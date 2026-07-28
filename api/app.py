#!/usr/bin/env python3
"""
API REST para DeepSeek, compatible con el formato de OpenAI.
Desplegable en Render/Railway/Docker.
"""

import logging
import sys
import time

from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

from config import Config  # noqa: E402  (después de load_dotenv)
from extensions import limiter  # noqa: E402

# ============================================================
# LOGGING
# ============================================================
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ============================================================
# VALIDAR CONFIGURACIÓN AL ARRANQUE
# ============================================================
config_problems = Config.validate()
for problem in config_problems:
    logger.warning("⚠️ Configuración: %s", problem)

if not Config.DEEPSEEK_TOKEN or not Config.DEEPSEEK_COOKIES:
    logger.error("❌ Faltan credenciales: DEEPSEEK_TOKEN y DEEPSEEK_COOKIES deben estar definidas")
    sys.exit(1)

logger.info("✅ Credenciales encontradas")
if Config.REQUIRE_API_KEY and Config.API_KEYS:
    logger.info("🔒 Autenticación por API key: ACTIVADA (%d key(s) configuradas)", len(Config.API_KEYS))
else:
    logger.warning("🔓 Autenticación por API key: DESACTIVADA — cualquiera con la URL puede usar la API")

# ============================================================
# APP
# ============================================================
app = Flask(__name__)
app.config["SECRET_KEY"] = Config.API_KEYS and next(iter(Config.API_KEYS)) or "dev-secret-key"
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB

CORS(
    app,
    resources={
        r"/*": {
            "origins": Config.CORS_ORIGINS,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "Accept"],
        }
    },
)

app.config["RATELIMIT_DEFAULT"] = Config.RATE_LIMIT_DEFAULT
app.config["RATELIMIT_STORAGE_URI"] = Config.RATE_LIMIT_STORAGE_URI
limiter.init_app(app)

# ============================================================
# RUTAS
# ============================================================
try:
    from routes.session import session_bp
    from routes.chat import chat_bp
    from routes.upload import upload_bp

    app.register_blueprint(session_bp, url_prefix="/api/session")  # legacy
    app.register_blueprint(chat_bp, url_prefix="")
    app.register_blueprint(upload_bp, url_prefix="")

    logger.info("✅ Rutas registradas correctamente")
except Exception:
    logger.exception("❌ Error al importar rutas")
    sys.exit(1)

# ============================================================
# ENDPOINTS BÁSICOS
# ============================================================


@app.route("/api/health")
def health():
    """Health check. No expone secretos, solo si están presentes."""
    return jsonify(
        {
            "status": "ok",
            "service": "deepseek-api",
            "timestamp": int(time.time()),
            "credentials_configured": bool(Config.DEEPSEEK_TOKEN and Config.DEEPSEEK_COOKIES),
            "auth_required": Config.REQUIRE_API_KEY,
        }
    )


@app.route("/")
def home():
    return jsonify(
        {
            "service": "DeepSeek API",
            "version": "2.1.0",
            "description": "API compatible con el formato de OpenAI (no oficial)",
            "endpoints": {
                "health": "/api/health",
                "openai": {
                    "chat": "/v1/chat/completions",
                    "models": "/v1/models",
                    "files": "/v1/files",
                },
            },
            "docs": "https://platform.openai.com/docs/api-reference",
            "supported_models": ["deepseek-chat", "deepseek-reasoner"],
        }
    )


# ============================================================
# MANEJADOR DE ERRORES GLOBAL
# ============================================================
@app.errorhandler(Exception)
def handle_error(e):
    logger.exception("Error no capturado")
    message = str(e) if Config.EXPOSE_ERROR_DETAILS else "Error interno del servidor"
    return (
        jsonify({"error": {"message": message, "type": "server_error", "code": "internal_error"}}),
        500,
    )


@app.errorhandler(429)
def handle_rate_limit(e):
    return (
        jsonify(
            {
                "error": {
                    "message": "Límite de peticiones excedido, intenta de nuevo más tarde.",
                    "type": "rate_limit_error",
                    "code": "rate_limit_exceeded",
                }
            }
        ),
        429,
    )


# ============================================================
# EJECUCIÓN
# ============================================================
if __name__ == "__main__":
    logger.info("🚀 Iniciando servidor en puerto %s", Config.PORT)
    app.run(host="0.0.0.0", port=Config.PORT, debug=Config.DEBUG)
