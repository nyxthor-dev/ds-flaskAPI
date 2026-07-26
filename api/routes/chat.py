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
    Endpoint compatible con DeepSeek (y parcialmente OpenAI).
    Si model = 'deepseek-reasoner' o se envía 'reasoning_enabled': true,
    se incluye 'reasoning_content' en la respuesta.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": {"message": "JSON requerido", "type": "invalid_request_error"}}), 400

    messages = data.get('messages', [])
    if not messages:
        return jsonify({"error": {"message": "messages es obligatorio", "type": "invalid_request_error"}}), 400

    # --- Parámetros ---
    model = data.get('model', 'deepseek-chat')
    temperature = data.get('temperature', 0.7)
    max_tokens = data.get('max_tokens', 1000)
    stream = data.get('stream', False)
    
    # Detectar si debemos incluir razonamiento
    # Si el modelo es 'deepseek-reasoner' o se pasa 'reasoning_enabled': true
    reasoning_enabled = data.get('reasoning_enabled', False)
    if 'reasoner' in model.lower():
        reasoning_enabled = True

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

    # --- Crear sesión interna (sin exponer) ---
    session_id = service.create_session()

    # --- Streaming (modo simplificado) ---
    if stream:
        @stream_with_context
        def generate_openai_stream():
            completion_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
            created = int(time.time())

            try:
                # Evento inicial
                yield f"data: {json.dumps({'id': completion_id, 'object': 'chat.completion.chunk', 'created': created, 'model': model, 'choices': [{'index': 0, 'delta': {'role': 'assistant'}, 'finish_reason': None}]})}\n\n"

                # Acumular pensamiento y respuesta para streaming (opcional)
                thinking_chunks = []
                for event in service.send_message(
                    session_id=session_id,
                    prompt=prompt,
                    thinking_enabled=reasoning_enabled,
                    search_enabled=True
                ):
                    if event['type'] == 'think' and reasoning_enabled:
                        chunk = event['data']
                        thinking_chunks.append(chunk)
                        # Enviar como reasoning_content en el delta (formato DeepSeek)
                        yield f"data: {json.dumps({'id': completion_id, 'object': 'chat.completion.chunk', 'created': created, 'model': model, 'choices': [{'index': 0, 'delta': {'reasoning_content': chunk}, 'finish_reason': None}]})}\n\n"
                    elif event['type'] == 'response':
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
        razonamiento = ""

        for event in service.send_message(
            session_id=session_id,
            prompt=prompt,
            thinking_enabled=reasoning_enabled,
            search_enabled=True
        ):
            if event['type'] == 'think' and reasoning_enabled:
                razonamiento += event['data']
            elif event['type'] == 'response':
                chunk = event['data']
                if chunk != "FINISHED":
                    respuesta += chunk

        # Construir la respuesta según el formato deseado
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

        # Si hay razonamiento, lo incluimos dentro de message
        if razonamiento:
            response["choices"][0]["message"]["reasoning_content"] = razonamiento

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