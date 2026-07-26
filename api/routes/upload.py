from flask import Blueprint, request, jsonify
import tempfile
import os
import uuid
import logging
from services.deepseek_service import DeepSeekService

upload_bp = Blueprint('upload', __name__)
service = DeepSeekService()
logger = logging.getLogger(__name__)


@upload_bp.route('/v1/files', methods=['POST'])
def upload_file_openai():
    """
    Endpoint compatible con OpenAI Files API.
    Documentación: https://platform.openai.com/docs/api-reference/files
    """
    if 'file' not in request.files:
        return jsonify({"error": {"message": "No se encontró el archivo", "type": "invalid_request_error"}}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": {"message": "Nombre de archivo vacío", "type": "invalid_request_error"}}), 400
    
    # Parámetros OpenAI
    purpose = request.form.get('purpose', 'assistants')
    thinking = request.form.get('thinking_enabled', 'true').lower() == 'true'
    
    # Guardar temporalmente
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name
    
    try:
        file_id = service.upload_file(tmp_path, thinking)
        
        # Construir respuesta estilo OpenAI
        response = {
            "id": file_id,
            "object": "file",
            "bytes": os.path.getsize(tmp_path),
            "created_at": int(os.path.getctime(tmp_path)),
            "filename": file.filename,
            "purpose": purpose,
            "status": "processed",
            "status_details": None
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.exception("Error al subir archivo")
        return jsonify({"error": {"message": str(e), "type": "server_error"}}), 500
    finally:
        # Limpiar archivo temporal
        try:
            os.unlink(tmp_path)
        except:
            pass


@upload_bp.route('/v1/files/<file_id>', methods=['DELETE'])
def delete_file_openai(file_id):
    """
    Endpoint compatible con OpenAI para eliminar archivos.
    """
    try:
        # Aquí deberías implementar la lógica para eliminar el archivo
        # Por ahora, solo devolvemos éxito
        response = {
            "id": file_id,
            "object": "file",
            "deleted": True
        }
        return jsonify(response), 200
        
    except Exception as e:
        logger.exception("Error al eliminar archivo")
        return jsonify({"error": {"message": str(e), "type": "server_error"}}), 500


@upload_bp.route('/v1/files', methods=['GET'])
def list_files_openai():
    """
    Endpoint compatible con OpenAI para listar archivos.
    """
    try:
        # Aquí deberías implementar la lógica para listar archivos
        # Por ahora, devolvemos lista vacía
        response = {
            "object": "list",
            "data": [],
            "first_id": None,
            "last_id": None,
            "has_more": False
        }
        return jsonify(response), 200
        
    except Exception as e:
        logger.exception("Error al listar archivos")
        return jsonify({"error": {"message": str(e), "type": "server_error"}}), 500


@upload_bp.route('/v1/files', methods=['OPTIONS'])
def upload_file_options():
    """CORS preflight para OpenAI endpoint."""
    response = jsonify({})
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, GET, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response


# ============================================================
# ENDPOINT ORIGINAL (para compatibilidad hacia atrás)
# ============================================================

@upload_bp.route('', methods=['POST'])
def upload_file():
    """Sube un archivo y devuelve file_id (legacy)."""
    if 'file' not in request.files:
        return jsonify({"error": "No se encontró el archivo"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Nombre de archivo vacío"}), 400

    thinking = request.form.get('thinking_enabled', 'true').lower() == 'true'

    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name

    try:
        file_id = service.upload_file(tmp_path, thinking)
        return jsonify({"file_id": file_id, "filename": file.filename}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            os.unlink(tmp_path)
        except:
            pass