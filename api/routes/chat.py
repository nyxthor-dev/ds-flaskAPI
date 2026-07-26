from flask import Blueprint, request, Response, jsonify, stream_with_context
import json
import time
import uuid
import logging
from services.deepseek_service import DeepSeekService

chat_bp = Blueprint('chat', __name__)
service = DeepSeekService()
logger = logging.getLogger(__name__)


@chat_bp.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    """
    Endpoint 100% compatible con OpenAI Chat Completions API.
    https://platform.openai.com/docs/api-reference/chat
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": {"message": "JSON requerido", "type": "invalid_request_error"}}), 400

    # --- Parámetros OpenAI ---
    messages = data.get('messages', [])
    if not messages:
        return jsonify({"error": {"message": "messages es obligatorio", "type": "invalid_request_error"}}), 400

    model = data.get('model', 'deepseek-chat')
    temperature = data.get('temperature', 0.7)
    max_tokens = data.get('max_tokens', 1000)
    stream = data.get('stream', False)
    # Otros parámetros opcionales (ignoramos los que no usamos)
    # seed, user, etc.

    # --- Construir el prompt a partir del historial ---
    # Reconstruimos todo el diálogo en un solo texto
    conversation = ""
    for msg in messages:
        role = msg.get('role')
        content = msg.get('content')
        if role == 'system':
            conversation += f"Sistema: {content}\n"
        elif role == 'user':
            conversation += f"Usuario: {content}\n"
        elif role == 'assistant':
            conversation += f"Asistente: {content}\n"
    # El prompt final es toda la conversación, más la instrucción de responder como asistente
    prompt = conversation + "Asistente:"

    # --- Gestión de sesión (totalmente interna) ---
    # Creamos una sesión nueva para cada solicitud (o podríamos cachear por usuario)
    # Esto asegura que no haya contaminación entre peticiones.
    session_id = service.create_session()

    # --- Streaming ---
    if stream:
        @stream_with_context
        def generate_openai_stream():
            completion_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
            created = int(time.time())

            try:
                # Primer evento (rol)
                yield f"data: {json.dumps({'id': completion_id, 'object': 'chat.completion.chunk', 'created': created, 'model': model, 'choices': [{'index': 0, 'delta': {'role': 'assistant'}, 'finish_reason': None}]})}\n\n"

                for event in service.send_message(
                    session_id=session_id,
                    prompt=prompt,
                    thinking_enabled=False,  # No exponemos el pensamiento
                    search_enabled=True
                ):
                    if event['type'] == 'response':
                        chunk = event['data']
                        if chunk == "FINISHED":
                            continue
                        yield f"data: {json.dumps({'id': completion_id, 'object': 'chat.completion.chunk', 'created': created, 'model': model, 'choices': [{'index': 0, 'delta': {'content': chunk}, 'finish_reason': None}]})}\n\n"

                # Evento final
                yield f"data: {json.dumps({'id': completion_id, 'object': 'chat.completion.chunk', 'created': created, 'model': model, 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}]})}\n\n"
                yield "data: [DONE]\n\n"

            except Exception as e:
                logger.exception("Error en streaming")
                yield f"data: {json.dumps({'error': {'message': str(e), 'type': 'server_error'}})}\n\n"

        return Response(generate_openai_stream(), mimetype="text/event-stream", headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        })

    # --- No streaming ---
    try:
        respuesta = ""
        for event in service.send_message(
            session_id=session_id,
            prompt=prompt,
            thinking_enabled=False,
            search_enabled=True
        ):
            if event['type'] == 'response':
                chunk = event['data']
                if chunk != "FINISHED":
                    respuesta += chunk

        # Respuesta OpenAI estándar (sin campos extras)
        response = {
            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": respuesta
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": len(respuesta.split()),
                "total_tokens": len(prompt.split()) + len(respuesta.split())
            }
        }

        return jsonify(response), 200

    except Exception as e:
        logger.exception("Error en chat completions")
        return jsonify({"error": {"message": str(e), "type": "server_error"}}), 500


@chat_bp.route('/v1/chat/completions', methods=['OPTIONS'])
def chat_completions_options():
    response = jsonify({})
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response


# ============================================================
# Endpoint legacy (compatibilidad hacia atrás)
# ============================================================
@chat_bp.route('/api/chat', methods=['POST'])
def send_message_legacy():
    """Endpoint legacy (se mantiene para no romper integraciones viejas)."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Datos JSON requeridos"}), 400
    session_id = data.get('session_id')
    prompt = data.get('prompt')
    if not session_id or not prompt:
        return jsonify({"error": "session_id y prompt son obligatorios"}), 400
    # ... (código legacy, sin cambios)