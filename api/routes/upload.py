import logging
import os
import tempfile

from flask import Blueprint, jsonify, request

from config import Config
from extensions import limiter
from services.deepseek_service import DeepSeekService
from utils.auth import require_api_key
from utils.errors import openai_error
from utils.file_processor import is_archive, process_archive

upload_bp = Blueprint("upload", __name__)
service = DeepSeekService()
logger = logging.getLogger(__name__)

# Extensiones ahora incluyen texto/código y comprimidos
ALLOWED_EXTENSIONS = {
    ".txt", ".pdf", ".md", ".csv", ".json", ".png", ".jpg", ".jpeg",
    ".py", ".js", ".html", ".css", ".xml", ".yaml", ".yml", ".sh",
    ".bat", ".ps1", ".rb", ".java", ".c", ".cpp", ".h", ".hpp",
    ".go", ".rs", ".swift", ".kt", ".log", ".conf", ".ini", ".properties",
    ".toml", ".sql", ".r", ".pl", ".pm", ".tcl", ".lua", ".vim",
    ".rst", ".tex", ".scss", ".less", ".sass", ".styl", ".vue",
    ".jsx", ".tsx", ".ts", ".coffee", ".dart", ".lisp", ".clj",
    ".cljs", ".edn", ".erl", ".hrl", ".ex", ".exs", ".fs", ".fsx",
    ".ml", ".mli", ".nim", ".cr", ".zig", ".v", ".vhd", ".vhdl",
    ".sv", ".svh", ".f", ".for", ".f90", ".f95", ".f03", ".f08",
    ".m", ".mm", ".p", ".p6", ".pm6", ".pl6", ".t", ".pod",
    ".make", ".cmake", ".gradle", ".sbt", ".pom", ".xsd", ".wsdl",
    ".wadl", ".raml", ".oas", ".swagger", ".proto", ".thrift",
    ".avsc", ".avro", ".env", ".example", ".sample", ".template",
    # Formatos comprimidos (se procesarán por separado)
    ".zip", ".tar", ".tgz", ".tar.gz", ".gz", ".rar",
}
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

        # --- Procesar archivos comprimidos ---
        if is_archive(file.filename):
            logger.info("Archivo comprimido detectado: %s", file.filename)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as output_tmp:
                output_txt_path = output_tmp.name
            try:
                processed_file = process_archive(tmp_path, output_txt_path)
                if processed_file is None:
                    return openai_error("El comprimido no contiene archivos de texto válidos.")
                # Subir el archivo concatenado en lugar del comprimido
                file_id = service.upload_file(processed_file, thinking)
                # Limpiar archivo temporal generado
                try:
                    os.unlink(output_txt_path)
                except OSError:
                    pass
                # Devolver el ID del archivo concatenado
                response = {
                    "id": file_id,
                    "object": "file",
                    "bytes": os.path.getsize(processed_file),
                    "created_at": int(os.path.getctime(processed_file)),
                    "filename": file.filename,  # Mantenemos el nombre original para referencia
                    "purpose": purpose,
                    "status": "processed",
                    "status_details": {"processed_as": "concatenated_text"},
                }
                return jsonify(response), 200
            except Exception as e:
                logger.exception("Error al procesar archivo comprimido")
                message = str(e) if Config.EXPOSE_ERROR_DETAILS else "Error al procesar el comprimido"
                return openai_error(message, status_code=502, error_type="server_error")
            finally:
                # Limpiar archivo temporal de salida si no se eliminó
                if os.path.exists(output_txt_path):
                    try:
                        os.unlink(output_txt_path)
                    except OSError:
                        pass

        # --- Archivo individual (incluye texto y otros permitidos) ---
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