import logging
import os
import tempfile

from flask import Blueprint, jsonify, request

from config import Config
from extensions import limiter
from services.deepseek_service import DeepSeekService
from utils.auth import require_api_key
from utils.errors import openai_error
from utils.file_processor import is_archive, process_archive, is_text_file

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

# Extensiones que DeepSeek acepta de forma NATIVA (no requieren conversión).
# Todo lo demás que sea texto/código (.py, .js, .java, etc.) se reescribe
# a .txt antes de subirse, porque el backend de DeepSeek rechaza extensiones
# de código que no reconoce.
NATIVE_EXTENSIONS = {".txt", ".pdf", ".md", ".csv", ".json", ".png", ".jpg", ".jpeg"}


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
                # Calcular tamaño y fecha ANTES de subir/borrar el archivo,
                # ya que tanto upload_file como el unlink posterior pueden
                # dejarlo inaccesible.
                file_size = os.path.getsize(processed_file)
                file_ctime = int(os.path.getctime(processed_file))
                # Subir el archivo concatenado en lugar del comprimido,
                # conservando el nombre original + .txt para que se note
                # que es el contenido extraído del comprimido.
                display_name = os.path.splitext(file.filename)[0] + "_extracted.txt"
                file_id = service.upload_file_and_wait(processed_file, thinking, display_name=display_name)
                # Devolver el ID del archivo concatenado
                response = {
                    "id": file_id,
                    "object": "file",
                    "bytes": file_size,
                    "created_at": file_ctime,
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
        upload_path = tmp_path
        converted_tmp_path = None
        status_details = None

        if ext not in NATIVE_EXTENSIONS and is_text_file(file.filename):
            # DeepSeek no reconoce extensiones de código (.py, .js, .java, ...),
            # así que lo convertimos a .txt internamente antes de subirlo,
            # conservando el nombre original solo como referencia visible.
            logger.info("Convirtiendo archivo de código a .txt para compatibilidad: %s", file.filename)
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as conv_tmp:
                    converted_tmp_path = conv_tmp.name
                with open(tmp_path, "r", encoding="utf-8", errors="replace") as src:
                    content = src.read()
                header = f"--- Archivo: {file.filename} ---\n"
                with open(converted_tmp_path, "w", encoding="utf-8") as dst:
                    dst.write(header)
                    dst.write(content)
                upload_path = converted_tmp_path
                status_details = {"processed_as": "converted_to_text", "original_extension": ext}
            except Exception:
                logger.exception("Error al convertir archivo a texto, se sube tal cual")
                upload_path = tmp_path
                status_details = None

        display_name = None
        if converted_tmp_path:
            display_name = os.path.splitext(file.filename)[0] + ".txt"

        try:
            file_size = os.path.getsize(upload_path)
            file_ctime = int(os.path.getctime(upload_path))
            file_id = service.upload_file_and_wait(upload_path, thinking, display_name=display_name)
        finally:
            if converted_tmp_path and os.path.exists(converted_tmp_path):
                try:
                    os.unlink(converted_tmp_path)
                except OSError:
                    pass

        response = {
            "id": file_id,
            "object": "file",
            "bytes": file_size,
            "created_at": file_ctime,
            "filename": file.filename,
            "purpose": purpose,
            "status": "processed",
            "status_details": status_details,
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