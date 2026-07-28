import logging

from flask import Blueprint, jsonify

from config import Config
from services.deepseek_service import DeepSeekService
from utils.auth import require_api_key
from utils.errors import openai_error

session_bp = Blueprint("session", __name__)
service = DeepSeekService()
logger = logging.getLogger(__name__)


@session_bp.route("", methods=["POST"])
@require_api_key
def create_session():
    """Crea una nueva sesión de chat (endpoint legacy)."""
    try:
        session_id = service.create_session()
        return jsonify({"session_id": session_id}), 200
    except Exception as e:
        logger.exception("Error al crear sesión")
        message = str(e) if Config.EXPOSE_ERROR_DETAILS else "No se pudo crear la sesión"
        return openai_error(message, status_code=502, error_type="server_error")
