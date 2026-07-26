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
    Endpoint compatible con OpenAI Chat Completions API.
    Soporta streaming y no streaming.
    Documentación: https://platform.openai.com/docs/api-reference/chat
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": {"message": "JSON requerido", "type": "invalid_request_error"}}), 400
    
    # ============================================================
    # 1. PARSEAR PARÁMETROS OPENAI
    # ============================================================
    messages = data.get('messages', [])
    if not messages:
        return jsonify({"error": {"message": "messages es obligatorio", "type": "invalid_request_error"}}), 400
    
    # Extraer mensajes
    prompt = None
    system_prompt = None
    for msg in messages:
        role = msg.get('role')
        content = msg.get('content')
        if role == 'system':
            system_prompt = content
        elif role == 'user' and not prompt:
            prompt = content
    
    if not prompt:
        return jsonify({"error": {"message": "No se encontró mensaje de usuario", "type": "invalid_request_error"}}), 400
    
    # Parámetros OpenAI
    model = data.get('model', 'deepseek-chat')
    temperature = data.get('temperature', 0.7)
    max_tokens = data.get('max_tokens', 1000)
    stream = data.get('stream', False)
    seed = data.get('seed')
    user = data.get('user')
    
    # ============================================================
    # 2. GESTIÓN DE SESIÓN
    # ============================================================
    session_id = data.get('session_id')
    if not session_id:
        session_id = service.create_session()
        logger.info(f"Sesión creada automáticamente: {session_id}")
    
    # Combinar system prompt
    final_prompt = prompt
    if system_prompt:
        final_prompt = f"{system_prompt}\n\nUsuario: {prompt}"
    
    # ============================================================
    # 3. GENERAR RESPUESTA
    # ============================================================
    
    # 3.1 MODO STREAMING
    if stream:
        @stream_with_context
        def generate_openai_stream():
            """Generador de streaming estilo OpenAI."""
            completion_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
            created = int(time.time())
            
            try:
                # Evento inicial
                yield f"data: {json.dumps({'id': completion_id, 'object': 'chat.completion.chunk', 'created': created, 'model': model, 'choices': [{'index': 0, 'delta': {'role': 'assistant'}, 'finish_reason': None}]})}\n\n"
                
                # Enviar chunks
                for event in service.send_message(
                    session_id=session_id,
                    prompt=final_prompt,
                    thinking_enabled=data.get('thinking_enabled', True),
                    search_enabled=data.get('search_enabled', True)
                ):
                    if event['type'] == 'response':
                        chunk = event['data']
                        # Saltar FINISHED
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
    
    # 3.2 MODO NO-STREAMING
    try:
        respuesta_completa = ""
        thinking_completo = ""
        mensaje_id = None
        
        for event in service.send_message(
            session_id=session_id,
            prompt=final_prompt,
            thinking_enabled=data.get('thinking_enabled', True),
            search_enabled=data.get('search_enabled', True)
        ):
            if event['type'] == 'think':
                thinking_completo += event['data']
            elif event['type'] == 'response':
                chunk = event['data']
                if chunk != "FINISHED":
                    respuesta_completa += chunk
            elif event['type'] == 'done':
                mensaje_id = event['data']
        
        # Construir respuesta OpenAI
        response = {
            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": respuesta_completa
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": len(final_prompt.split()),
                "completion_tokens": len(respuesta_completa.split()),
                "total_tokens": len(final_prompt.split()) + len(respuesta_completa.split())
            },
            # Campos extras útiles (no estándar OpenAI pero compatibles)
            "session_id": session_id,
            "message_id": mensaje_id,
            "_thinking": thinking_completo  # Prefijo _ para no interferir con OpenAI
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.exception("Error en chat completions")
        return jsonify({"error": {"message": str(e), "type": "server_error"}}), 500


@chat_bp.route('/v1/chat/completions', methods=['OPTIONS'])
def chat_completions_options():
    """CORS preflight para OpenAI endpoint."""
    response = jsonify({})
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response


# ============================================================
# ENDPOINT ORIGINAL (para compatibilidad hacia atrás)
# ============================================================

@chat_bp.route('', methods=['POST'])
def send_message():
    """Endpoint original - Devuelve SSE streaming (legacy)."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Datos JSON requeridos"}), 400
    
    session_id = data.get('session_id')
    prompt = data.get('prompt')
    if not session_id or not prompt:
        return jsonify({"error": "session_id y prompt son obligatorios"}), 400
    
    parent_message_id = data.get('parent_message_id')
    ref_file_ids = data.get('ref_file_ids', [])
    thinking_enabled = data.get('thinking_enabled', True)
    search_enabled = data.get('search_enabled', True)
    model_type = data.get('model_type')
    
    @stream_with_context
    def generate():
        """Generador de eventos SSE."""
        yield "event: start\ndata: {}\n\n"
        try:
            for event in service.send_message(
                session_id=session_id,
                prompt=prompt,
                parent_message_id=parent_message_id,
                ref_file_ids=ref_file_ids,
                thinking_enabled=thinking_enabled,
                search_enabled=search_enabled,
                model_type=model_type
            ):
                if event['type'] == 'response' and event['data'] == "FINISHED":
                    continue
                yield f"event: {event['type']}\ndata: {json.dumps(event['data'], ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
    
    return Response(generate(), mimetype="text/event-stream")