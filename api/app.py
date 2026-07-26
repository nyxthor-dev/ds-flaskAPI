#!/usr/bin/env python3
"""
API REST para DeepSeek con streaming en tiempo real.
100% compatible con OpenAI y DeepSeek.
Desplegable en Render.
"""

import os
import sys
import logging
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
import time

# Configurar logging detallado
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

# Verificar credenciales al inicio
logger.info("=== INICIANDO API DEEPSEEK ===")
logger.info(f"Directorio actual: {os.getcwd()}")
logger.info(f"Archivos en directorio: {os.listdir('.')}")

token = os.getenv('DEEPSEEK_TOKEN')
cookies = os.getenv('DEEPSEEK_COOKIES')

if not token or not cookies:
    logger.error("❌ Faltan credenciales: DEEPSEEK_TOKEN y DEEPSEEK_COOKIES deben estar definidas")
    logger.error("   Revisa las variables de entorno en Render")
    sys.exit(1)

logger.info("✅ Credenciales encontradas (token y cookies)")

# Inicializar app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB

# ============================================================
# CORS - Configuración completa para OpenAI
# ============================================================
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Accept"]
    }
})

# ============================================================
# MIDDLEWARE: Autorización (Acepta cualquier token)
# ============================================================
@app.before_request
def handle_authorization():
    """
    Acepta la cabecera Authorization sin validarla.
    Esto evita que los clientes estándar (OpenAI SDK) fallen.
    """
    # Ignoramos OPTIONS (preflight CORS)
    if request.method == 'OPTIONS':
        return
    
    auth = request.headers.get('Authorization')
    if auth and auth.startswith('Bearer '):
        # Aceptamos el token pero no lo validamos
        # Podríamos extraer el usuario si quisiéramos
        logger.debug(f"Authorization header recibido: {auth[:20]}...")
    
    # Continuar con la petición
    return None

# ============================================================
# IMPORTAR RUTAS
# ============================================================
try:
    logger.info("Importando rutas...")
    from routes.session import session_bp
    from routes.chat import chat_bp
    from routes.upload import upload_bp
    
    # Registrar blueprints con URL prefixes correctos
    app.register_blueprint(session_bp, url_prefix='/api/session')  # Legacy
    app.register_blueprint(chat_bp, url_prefix='')  # Para /v1/chat/completions y /api/chat
    app.register_blueprint(upload_bp, url_prefix='')  # Para /v1/files y /api/upload
    
    logger.info("✅ Rutas registradas correctamente")
    
    # Log de rutas disponibles
    logger.info("📋 Rutas disponibles:")
    logger.info("   ✅ GET  /api/health")
    logger.info("   ✅ POST /api/session (legacy)")
    logger.info("   ✅ POST /v1/chat/completions (OpenAI)")
    logger.info("   ✅ GET  /v1/models (OpenAI)")
    logger.info("   ✅ POST /api/chat (legacy)")
    logger.info("   ✅ POST /v1/files (OpenAI)")
    logger.info("   ✅ POST /api/upload (legacy)")
    logger.info("   ✅ GET  / (info)")
    
except Exception as e:
    logger.exception("❌ Error al importar rutas")
    sys.exit(1)

# ============================================================
# ENDPOINTS
# ============================================================

@app.route('/api/health')
def health():
    """Health check estándar."""
    return jsonify({
        "status": "ok",
        "service": "deepseek-api",
        "timestamp": int(time.time())
    })

@app.route('/')
def home():
    """Información de la API."""
    return jsonify({
        "service": "DeepSeek API",
        "version": "2.0.0",
        "description": "API 100% compatible con OpenAI y DeepSeek",
        "endpoints": {
            "health": "/api/health",
            "openai": {
                "chat": "/v1/chat/completions",
                "models": "/v1/models",
                "files": "/v1/files"
            },
            "legacy": {
                "chat": "/api/chat",
                "upload": "/api/upload",
                "session": "/api/session"
            }
        },
        "docs": "https://platform.openai.com/docs/api-reference",
        "supported_models": [
            "deepseek-chat",
            "deepseek-reasoner"
        ]
    })

# ============================================================
# MANEJADOR DE ERRORES GLOBAL
# ============================================================
@app.errorhandler(Exception)
def handle_error(e):
    """Manejo de errores en formato OpenAI."""
    logger.exception("Error no capturado")
    return jsonify({
        "error": {
            "message": str(e),
            "type": "server_error",
            "code": "internal_error"
        }
    }), 500

# ============================================================
# EJECUCIÓN
# ============================================================
if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    logger.info(f"🚀 Iniciando servidor en puerto {port}")
    logger.info(f"   Health check: http://0.0.0.0:{port}/api/health")
    logger.info(f"   OpenAI Chat:  http://0.0.0.0:{port}/v1/chat/completions")
    logger.info(f"   OpenAI Models: http://0.0.0.0:{port}/v1/models")
    logger.info(f"   OpenAI Files:  http://0.0.0.0:{port}/v1/files")
    
    app.run(host='0.0.0.0', port=port, debug=False)