from flask import Blueprint, request, jsonify
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
    """Endpoint compatible con OpenAI."""
    
    data = request.get_json()
    if not data:
        return jsonify({"error": {"message": "JSON requerido"}}), 400
    
    messages = data.get('messages', [])
    if not messages:
        return jsonify({"error": {"message": "messages es obligatorio"}}), 400
    
    # Extraer el mensaje del usuario
    prompt = None
    for msg in messages:
        if msg.get('role') == 'user':
            prompt = msg.get('content')
            break
    
    if not prompt:
        return jsonify({"error": {"message": "No se encontró mensaje de usuario"}}), 400
    
    # Parámetros
    model = data.get('model', 'deepseek-chat')
    reasoning_enabled = data.get('reasoning_enabled', False)
    search_enabled = data.get('search_enabled', False)
    
    # Si el modelo es reasoner, forzar reasoning
    if 'reasoner' in model.lower():
        reasoning_enabled = True
    
    logger.info(f"📥 Chat request: model={model}, reasoning={reasoning_enabled}, search={search_enabled}")
    logger.info(f"📝 Prompt: {prompt[:100]}...")
    
    try:
        # Crear sesión automática
        session_id = service.create_session()
        logger.info(f"🔑 Sesión creada: {session_id}")
        
        # Recolectar respuesta
        respuesta = ""
        razonamiento = ""
        
        for event in service.send_message(
            session_id=session_id,
            prompt=prompt,
            thinking_enabled=reasoning_enabled,
            search_enabled=search_enabled
        ):
            if event['type'] == 'think':
                razonamiento += event['data']
            elif event['type'] == 'response':
                chunk = event['data']
                if chunk != "FINISHED":
                    respuesta += chunk
        
        logger.info(f"✅ Respuesta generada: {len(respuesta)} caracteres")
        logger.info(f"🧠 Razonamiento: {len(razonamiento)} caracteres")
        
        # Si no hay respuesta, generar un mensaje de error
        if not respuesta:
            respuesta = "Lo siento, no pude generar una respuesta. Por favor, intenta de nuevo."
        
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
        
        # Incluir razonamiento si existe
        if razonamiento:
            response["choices"][0]["message"]["reasoning_content"] = razonamiento
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.exception("❌ Error en chat completions")
        return jsonify({"error": {"message": str(e)}}), 500