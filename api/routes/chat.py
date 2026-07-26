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
    """
    Endpoint compatible con OpenAI.
    
    Los modelos son FICTICIOS:
    - 'deepseek-chat' → thinking_enabled=False (sin razonamiento)
    - 'deepseek-reasoner' → thinking_enabled=True (con razonamiento)
    
    El parámetro search_enabled se controla con 'search_enabled': true
    """
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
    
    # ============================================================
    # MODELOS FICTICIOS - Solo controlan parámetros
    # ============================================================
    model = data.get('model', 'deepseek-chat')
    
    # Determinar si activar razonamiento según el modelo
    thinking_enabled = False
    if 'reasoner' in model.lower():
        thinking_enabled = True
    
    # Permitir override por parámetro
    if data.get('reasoning_enabled') is True:
        thinking_enabled = True
    
    search_enabled = data.get('search_enabled', False)
    
    logger.info(f"📥 Chat request:")
    logger.info(f"  Modelo solicitado: {model} (FICTICIO)")
    logger.info(f"  Thinking: {thinking_enabled}")
    logger.info(f"  Search: {search_enabled}")
    logger.info(f"  Prompt: {prompt[:100]}...")
    
    try:
        # Crear sesión automática
        session_id = service.create_session()
        
        # Recolectar respuesta
        respuesta = ""
        razonamiento = ""
        
        for event in service.send_message(
            session_id=session_id,
            prompt=prompt,
            thinking_enabled=thinking_enabled,
            search_enabled=search_enabled
        ):
            if event['type'] == 'think':
                razonamiento += event['data']
            elif event['type'] == 'response':
                chunk = event['data']
                if chunk != "FINISHED":
                    respuesta += chunk
            elif event['type'] == 'error':
                logger.error(f"Error del servicio: {event['data']}")
                return jsonify({"error": {"message": event['data']}}), 500
        
        logger.info(f"✅ Respuesta generada: {len(respuesta)} caracteres")
        
        # Si no hay respuesta, generar mensaje de error
        if not respuesta:
            respuesta = "Lo siento, no pude generar una respuesta. Por favor, intenta de nuevo."
        
        # Construir respuesta OpenAI
        response = {
            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,  # El modelo ficticio que el usuario eligió
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


@chat_bp.route('/v1/chat/completions', methods=['OPTIONS'])
def chat_completions_options():
    response = jsonify({})
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response


@chat_bp.route('/v1/models', methods=['GET'])
def list_models():
    """Lista de modelos FICTICIOS."""
    models = [
        {
            "id": "deepseek-chat",
            "object": "model",
            "created": 1700000000,
            "owned_by": "deepseek",
            "description": "Modelo base sin razonamiento (thinking_enabled=False)"
        },
        {
            "id": "deepseek-reasoner",
            "object": "model",
            "created": 1700000000,
            "owned_by": "deepseek",
            "description": "Modelo con razonamiento activado (thinking_enabled=True)"
        }
    ]
    return jsonify({
        "object": "list",
        "data": models
    }), 200