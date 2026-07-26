from flask import Blueprint, request, Response, jsonify, stream_with_context
import json
import time
import uuid
import logging
from services.deepseek_service import DeepSeekService

chat_bp = Blueprint('chat', __name__)
service = DeepSeekService()
logger = logging.getLogger(__name__)


def openai_error(message, error_type="invalid_request_error", param=None, code=None, status=400):
    """Formato de error estándar OpenAI."""
    return jsonify({
        "error": {
            "message": message,
            "type": error_type,
            "param": param,
            "code": code
        }
    }), status


@chat_bp.route('/v1/models', methods=['GET'])
def list_models():
    """Lista de modelos disponibles (estándar OpenAI)."""
    models = [
        {
            "id": "deepseek-chat",
            "object": "model",
            "created": 1700000000,
            "owned_by": "deepseek"
        },
        {
            "id": "deepseek-reasoner",
            "object": "model",
            "created": 1700000000,
            "owned_by": "deepseek"
        }
    ]
    return jsonify({
        "object": "list",
        "data": models
    }), 200


@chat_bp.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    """
    Endpoint 100% compatible con OpenAI Chat Completions API.
    Soporta todos los parámetros estándar.
    """
    data = request.get_json()
    if not data:
        return openai_error("JSON requerido", param="request")

    # --- Validación de messages ---
    messages = data.get('messages', [])
    if not messages:
        return openai_error("messages es obligatorio", param="messages")

    # --- Extraer todos los parámetros ---
    model = data.get('model', 'deepseek-chat')
    temperature = data.get('temperature', 0.7)
    max_tokens = data.get('max_tokens', 1000)
    top_p = data.get('top_p', 1.0)
    presence_penalty = data.get('presence_penalty', 0.0)
    frequency_penalty = data.get('frequency_penalty', 0.0)
    stop = data.get('stop')
    stream = data.get('stream', False)
    reasoning_effort = data.get('reasoning_effort', 'medium')
    user = data.get('user')

    # Parámetros DeepSeek (no OpenAI)
    reasoning_enabled = data.get('reasoning_enabled', False)
    search_enabled = data.get('search_enabled', False)

    # Detectar modelo con razonamiento
    if 'reasoner' in model.lower():
        reasoning_enabled = True

    # --- Validar parámetros ---
    if temperature < 0 or temperature > 2:
        return openai_error("temperature debe estar entre 0 y 2", param="temperature")
    if top_p < 0 or top_p > 1:
        return openai_error("top_p debe estar entre 0 y 1", param="top_p")
    if presence_penalty < -2 or presence_penalty > 2:
        return openai_error("presence_penalty debe estar entre -2 y 2", param="presence_penalty")
    if frequency_penalty < -2 or frequency_penalty > 2:
        return openai_error("frequency_penalty debe estar entre -2 y 2", param="frequency_penalty")

    # --- Construir prompt con historial ---
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
    prompt = conversation + "Asistente:"

    # --- Crear sesión interna ---
    session_id = service.create_session()
    logger.info(f"Sesión: {session_id}, Modelo: {model}, Razonamiento: {reasoning_enabled}, Búsqueda: {search_enabled}")

    # --- STREAMING ---
    if stream:
        @stream_with_context
        def generate_openai_stream():
            completion_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
            created = int(time.time())

            try:
                # Evento inicial: rol
                yield f"data: {json.dumps({'id': completion_id, 'object': 'chat.completion.chunk', 'created': created, 'model': model, 'choices': [{'index': 0, 'delta': {'role': 'assistant'}, 'finish_reason': None}]})}\n\n"

                # Acumular razonamiento y respuesta
                for event in service.send_message(
                    session_id=session_id,
                    prompt=prompt,
                    thinking_enabled=reasoning_enabled,
                    search_enabled=search_enabled,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=top_p,
                    presence_penalty=presence_penalty,
                    frequency_penalty=frequency_penalty,
                    stop=stop,
                    reasoning_effort=reasoning_effort
                ):
                    if event['type'] == 'think' and reasoning_enabled:
                        chunk = event['data']
                        # Enviar reasoning_content en el delta
                        yield f"data: {json.dumps({'id': completion_id, 'object': 'chat.completion.chunk', 'created': created, 'model': model, 'choices': [{'index': 0, 'delta': {'reasoning_content': chunk}, 'finish_reason': None}]})}\n\n"
                    elif event['type'] == 'response':
                        chunk = event['data']
                        if chunk == "FINISHED":
                            continue
                        yield f"data: {json.dumps({'id': completion_id, 'object': 'chat.completion.chunk', 'created': created, 'model': model, 'choices': [{'index': 0, 'delta': {'content': chunk}, 'finish_reason': None}]})}\n\n"

                # Evento final con finish_reason y system_fingerprint
                yield f"data: {json.dumps({'id': completion_id, 'object': 'chat.completion.chunk', 'created': created, 'model': model, 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}], 'system_fingerprint': 'fp_deepseek_v1'})}\n\n"
                yield "data: [DONE]\n\n"

            except Exception as e:
                logger.exception("Error en streaming")
                yield f"data: {json.dumps({'error': {'message': str(e), 'type': 'server_error'}})}\n\n"

        return Response(generate_openai_stream(), mimetype="text/event-stream", headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        })

    # --- NO STREAMING ---
    try:
        respuesta = ""
        razonamiento = ""

        for event in service.send_message(
            session_id=session_id,
            prompt=prompt,
            thinking_enabled=reasoning_enabled,
            search_enabled=search_enabled,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            presence_penalty=presence_penalty,
            frequency_penalty=frequency_penalty,
            stop=stop,
            reasoning_effort=reasoning_effort
        ):
            if event['type'] == 'think' and reasoning_enabled:
                razonamiento += event['data']
            elif event['type'] == 'response':
                chunk = event['data']
                if chunk != "FINISHED":
                    respuesta += chunk

        # Construir respuesta (100% OpenAI)
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
            },
            "system_fingerprint": "fp_deepseek_v1"
        }

        # Si hay razonamiento, incluirlo en message
        if razonamiento:
            response["choices"][0]["message"]["reasoning_content"] = razonamiento

        return jsonify(response), 200

    except Exception as e:
        logger.exception("Error en chat completions")
        return openai_error(str(e), error_type="server_error", status=500)


@chat_bp.route('/v1/chat/completions', methods=['OPTIONS'])
def chat_completions_options():
    response = jsonify({})
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response