#!/usr/bin/env python3
"""
API REST para DeepSeek con streaming en tiempo real.
Desplegable en Render.
"""

import os
import sys
import logging
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

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

# CORS - Configuración completa para OpenAI
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Accept"]
    }
})

# Importar rutas
try:
    logger.info("Importando rutas...")
    from routes.session import session_bp
    from routes.chat import chat_bp
    from routes.upload import upload_bp
    
    app.register_blueprint(session_bp, url_prefix='/api/session')
    app.register_blueprint(chat_bp, url_prefix='')  # Para /v1/chat/completions
    app.register_blueprint(upload_bp, url_prefix='')  # Para /v1/files
    logger.info("✅ Rutas registradas correctamente")
    
    # Log de rutas disponibles
    logger.info("📋 Rutas disponibles:")
    logger.info("   - GET  /api/health")
    logger.info("   - POST /api/session (legacy)")
    logger.info("   - POST /v1/chat/completions (OpenAI)")
    logger.info("   - POST /api/chat (legacy)")
    logger.info("   - POST /v1/files (OpenAI)")
    logger.info("   - POST /api/upload (legacy)")
except Exception as e:
    logger.exception("❌ Error al importar rutas")
    sys.exit(1)

# Health check
@app.route('/api/health')
def health():
    return jsonify({"status": "ok", "service": "deepseek-api"})

# Ruta raíz con información
@app.route('/')
def home():
    return jsonify({
        "service": "DeepSeek API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/api/health",
            "openai_chat": "/v1/chat/completions",
            "openai_files": "/v1/files",
            "legacy_chat": "/api/chat",
            "legacy_upload": "/api/upload",
            "legacy_session": "/api/session"
        },
        "docs": "https://platform.openai.com/docs/api-reference"
    })

# Manejador de errores global
@app.errorhandler(Exception)
def handle_error(e):
    logger.exception("Error no capturado")
    return jsonify({"error": {"message": str(e), "type": "server_error"}}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    logger.info(f"🚀 Iniciando servidor en puerto {port}")
    logger.info(f"   Health check: http://0.0.0.0:{port}/api/health")
    logger.info(f"   OpenAI Chat:  http://0.0.0.0:{port}/v1/chat/completions")
    logger.info(f"   OpenAI Files: http://0.0.0.0:{port}/v1/files")
    
    app.run(host='0.0.0.0', port=port, debug=False)