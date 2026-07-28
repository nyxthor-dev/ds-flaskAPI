import logging
import os
import tempfile

from flask import Blueprint, jsonify, request

from config import Config
from extensions import limiter
from services.deepseek_service import DeepSeekService
from utils.auth import require_api_key
from utils.errors import openai_error

upload_bp = Blueprint("upload", __name__)
service = DeepSeekService()
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".txt", ".pdf", ".md", ".csv", ".json", ".png", ".jpg", ".jpeg"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


@upload_bp.route("/v1/files", methods=["POST"])
@require_api_key
@limiter.limit(Config.RATE_LIMIT_DEFAULT)
def upload_file_openai():
    """Endpoint compatible con la API de Files de OpenAI."""
    if "file" not in request.files:
        return openai_error("No se encontró el archivo")

    file = request.files["file"]
    if file.filename == "":
        return openai_error("Nombre de archivo vacío")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return openai_error(f"Extensión no permitida: {ext}")

    purpose = request.form.get("purpose", "assistants")
    thinking = request.form.get("thinking_enabled", "true").lower() == "true"

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name

        if os.path.getsize(tmp_path) > MAX_FILE_SIZE:
            return openai_error(f"El archivo excede el tamaño máximo de {MAX_FILE_SIZE // (1024*1024)} MB")

        file_id = service.upload_file(tmp_path, thinking)

        response = {
            "id": file_id,
            "object": "file",
            "bytes": os.path.getsize(tmp_path),
            "created_at": int(os.path.getctime(tmp_path)),
            "filename": file.filename,
            "purpose": purpose,
            "status": "processed",
            "status_details": None,
        }
        return jsonify(response), 200

    except Exception as e:
        logger.exception("Error al subir archivo")
        message = str(e) if Config.EXPOSE_ERROR_DETAILS else "Error al procesar el archivo"
        return openai_error(message, status_code=502, error_type="server_error")
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


@upload_bp.route("/v1/files", methods=["GET"])
@require_api_key
def list_files_openai():
    """Lista de archivos. NOTA: no hay persistencia real todavía (ver roadmap)."""
    return jsonify({"object": "list", "data": [], "first_id": None, "last_id": None, "has_more": False}), 200


@upload_bp.route("/v1/files/<file_id>", methods=["DELETE"])
@require_api_key
def delete_file_openai(file_id):
    return jsonify({"id": file_id, "object": "file", "deleted": True}), 200


@upload_bp.route("/v1/files", methods=["OPTIONS"])
def upload_file_options():
    return jsonify({}), 200


@upload_bp.route("/api/upload", methods=["POST"])
@require_api_key
def upload_file_legacy():
    """Endpoint legacy: delega en la implementación estándar."""
    return upload_file_openai()
