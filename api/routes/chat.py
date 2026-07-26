from flask import Blueprint, request, Response, jsonify
import json
import time
import uuid
from services.deepseek_service import DeepSeekService

chat_bp = Blueprint('chat', __name__)
service = DeepSeekService()

@chat_bp.route('', methods=['POST'])
def send_message():
    """Endpoint original - Devuelve SSE streaming."""
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
                yield f"event: {event['type']}\ndata: {json.dumps(event['data'], ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
    
    return Response(generate(), mimetype="text/event-stream")


@chat_bp.route('/openai', methods=['POST'])
def send_message_openai():
    """
    Endpoint compatible con OpenAI - Devuelve JSON.
    Soporta streaming y no streaming.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Datos JSON requeridos"}), 400
    
    # Parsear formato OpenAI
    messages = data.get('messages', [])
    if not messages:
        return jsonify({"error": "messages es obligatorio"}), 400
    
    # Extraer el último mensaje del usuario
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
        return jsonify({"error": "No se encontró mensaje de usuario"}), 400
    
    # Parámetros de OpenAI
    model = data.get('model', 'deepseek-chat')
    temperature = data.get('temperature', 0.7)
    max_tokens = data.get('max_tokens', 1000)
    stream = data.get('stream', False)
    
    # Extraer session_id (opcional, se puede crear automáticamente)
    session_id = data.get('session_id')
    if not session_id:
        # Crear sesión automáticamente si no se proporciona
        session_id = service.create_session()
    
    # Combinar system prompt con el mensaje del usuario si existe
    final_prompt = prompt
    if system_prompt:
        final_prompt = f"{system_prompt}\n\nUsuario: {prompt}"
    
    # Si stream=True, devolver streaming estilo OpenAI
    if stream:
        def generate_openai_stream():
            """Generador de streaming estilo OpenAI."""
            # ID único para la conversación
            completion_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
            created = int(time.time())
            
            try:
                # Enviar evento inicial con el rol
                yield f"data: {json.dumps({'id': completion_id, 'object': 'chat.completion.chunk', 'created': created, 'model': model, 'choices': [{'index': 0, 'delta': {'role': 'assistant'}, 'finish_reason': None}]})}\n\n"
                
                # Enviar chunks de la respuesta
                for event in service.send_message(
                    session_id=session_id,
                    prompt=final_prompt,
                    thinking_enabled=True,
                    search_enabled=True
                ):
                    if event['type'] == 'response':
                        chunk = event['data']
                        # Enviar chunk en formato OpenAI
                        yield f"data: {json.dumps({'id': completion_id, 'object': 'chat.completion.chunk', 'created': created, 'model': model, 'choices': [{'index': 0, 'delta': {'content': chunk}, 'finish_reason': None}]})}\n\n"
                
                # Enviar evento final
                yield f"data: {json.dumps({'id': completion_id, 'object': 'chat.completion.chunk', 'created': created, 'model': model, 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}]})}\n\n"
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        return Response(generate_openai_stream(), mimetype="text/event-stream")
    
    # Si stream=False, devolver JSON completo
    try:
        # Recolectar respuesta completa
        respuesta_completa = ""
        thinking_completo = ""
        mensaje_id = None
        
        for event in service.send_message(
            session_id=session_id,
            prompt=final_prompt,
            thinking_enabled=True,
            search_enabled=True
        ):
            if event['type'] == 'think':
                thinking_completo += event['data']
            elif event['type'] == 'response':
                respuesta_completa += event['data']
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
                "prompt_tokens": len(final_prompt.split()),  # Aproximación
                "completion_tokens": len(respuesta_completa.split()),
                "total_tokens": len(final_prompt.split()) + len(respuesta_completa.split())
            },
            "session_id": session_id,
            "message_id": mensaje_id,
            "thinking": thinking_completo  # Extra: pensamiento del modelo
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500