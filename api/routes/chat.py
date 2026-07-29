# routes/chat.py - Con streaming original restaurado
import json
import logging
import time
import uuid

from flask import Blueprint, Response, jsonify, request

from config import Config
from extensions import limiter
from services.deepseek_service import DeepSeekService
from utils.auth import require_api_key
from utils.errors import openai_error
from utils.tokens import count_tokens

# Importar lógica de herramientas
from routes.tool_handler import (
    extract_text_content,
    build_tool_calls_prompt,
    parse_tool_decision,
    build_tool_response
)

chat_bp = Blueprint("chat", __name__)
service = DeepSeekService()
logger = logging.getLogger(__name__)

_PARAM_RANGES = {
    "temperature": (0, 2),
    "top_p": (0, 1),
    "presence_penalty": (-2, 2),
    "frequency_penalty": (-2, 2),
}

def _validate_params(data: dict):
    for name, (lo, hi) in _PARAM_RANGES.items():
        if name in data and data[name] is not None:
            value = data[name]
            if not isinstance(value, (int, float)) or not (lo <= value <= hi):
                return f"'{name}' debe estar entre {lo} y {hi}"
    return None

def _extract_prompt(messages: list) -> str | None:
    """Extrae el prompt del último mensaje (user o tool)."""
    for msg in reversed(messages):
        role = msg.get("role")
        if role in ("user", "tool"):
            content = msg.get("content")
            if content:
                text = extract_text_content(content)
                if text:
                    return text
    return None

@chat_bp.route("/v1/chat/completions", methods=["POST"])
@require_api_key
@limiter.limit(Config.RATE_LIMIT_DEFAULT)
def chat_completions():
    data = request.get_json(silent=True)
    if not data:
        return openai_error("Se requiere un cuerpo JSON válido")

    messages = data.get("messages", [])
    if not messages:
        return openai_error("'messages' es obligatorio")

    model = data.get("model", "deepseek-chat")
    stream = bool(data.get("stream", False))

    # --- MANEJO DE TOOLS (usando DeepSeek para decidir) ---
    tools = data.get("tools")
    if tools:
        logger.info(f"🔧 Tools detectadas: {[t.get('function', {}).get('name') for t in tools]}")

        try:
            # 1. Construir prompt para DeepSeek
            tool_prompt = build_tool_calls_prompt(messages, tools)

            # 2. Enviar a DeepSeek (usando el servicio existente)
            session_id = service.create_session()

            # Recoger la respuesta de DeepSeek (solo para decisión de herramienta)
            response_text = ""
            for event in service.send_message(
                session_id=session_id,
                prompt=tool_prompt,
                thinking_enabled=False,
                search_enabled=False,
            ):
                if event["type"] == "response" and event["data"] != "FINISHED":
                    response_text += event["data"]
                elif event["type"] == "error":
                    logger.error(f"Error en decisión de herramienta: {event['data']}")
                    break

            # 3. Parsear la decisión
            tool_call = parse_tool_decision(response_text)
            if tool_call:
                logger.info(f"🔧 DeepSeek decidió usar herramienta: {tool_call['function']['name']}")
                return build_tool_response(tool_call, model)

            logger.info("🔧 DeepSeek decidió NO usar herramienta, continuando con texto")

        except Exception as e:
            logger.error(f"❌ Error en tool calling: {e}")
            # Si falla, continuar con flujo normal

        # Eliminar tools para no interferir con el flujo normal
        data.pop("tools", None)
        data.pop("tool_choice", None)

    # --- FLUJO NORMAL (texto) ---
    prompt = _extract_prompt(messages)
    if not prompt:
        return openai_error("No se encontró contenido en el mensaje")

    error = _validate_params(data)
    if error:
        return openai_error(error)

    thinking_enabled = "reasoner" in model.lower() or data.get("reasoning_enabled") is True
    search_enabled = bool(data.get("search_enabled", False))

    if Config.LOG_PROMPT_CONTENT:
        logger.info(f"📥 Chat request modelo={model} thinking={thinking_enabled} search={search_enabled} prompt={prompt[:100]}")
    else:
        logger.info(f"📥 Chat request modelo={model} thinking={thinking_enabled} search={search_enabled} len(prompt)={len(prompt)}")

    completion_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created = int(time.time())

    if stream:
        return _stream_response(completion_id, created, model, prompt, thinking_enabled, search_enabled)
    return _full_response(completion_id, created, model, prompt, thinking_enabled, search_enabled)

def _full_response(completion_id, created, model, prompt, thinking_enabled, search_enabled):
    try:
        session_id = service.create_session()
        respuesta, razonamiento = "", ""

        for event in service.send_message(
            session_id=session_id,
            prompt=prompt,
            thinking_enabled=thinking_enabled,
            search_enabled=search_enabled,
        ):
            if event["type"] == "think":
                razonamiento += event["data"]
            elif event["type"] == "response" and event["data"] != "FINISHED":
                respuesta += event["data"]
            elif event["type"] == "error":
                logger.error(f"Error del servicio: {event['data']}")
                return openai_error(event["data"], status_code=502, error_type="server_error")

        if not respuesta:
            respuesta = "Lo siento, no pude generar una respuesta. Por favor, intenta de nuevo."

        prompt_tokens = count_tokens(prompt, model)
        completion_tokens = count_tokens(respuesta, model)

        message = {"role": "assistant", "content": respuesta}
        if razonamiento:
            message["reasoning_content"] = razonamiento

        response = {
            "id": completion_id,
            "object": "chat.completion",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        }
        return jsonify(response), 200

    except Exception as e:
        logger.exception("❌ Error en chat completions")
        message = str(e) if Config.EXPOSE_ERROR_DETAILS else "Error al generar la respuesta"
        return openai_error(message, status_code=502, error_type="server_error")

def _stream_response(completion_id, created, model, prompt, thinking_enabled, search_enabled):
    """Streaming ORIGINAL restaurado: primero role, luego contenido, luego stop."""
    
    def sse_chunk(delta: dict, finish_reason=None):
        payload = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
        }
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    def generate():
        sent_content = False
        try:
            session_id = service.create_session()
            
            # 1. Enviar role primero (como funcionaba originalmente)
            yield sse_chunk({"role": "assistant"})

            # 2. Enviar contenido en chunks
            for event in service.send_message(
                session_id=session_id,
                prompt=prompt,
                thinking_enabled=thinking_enabled,
                search_enabled=search_enabled,
            ):
                if event["type"] == "think":
                    yield sse_chunk({"reasoning_content": event["data"]})
                elif event["type"] == "response" and event["data"] != "FINISHED":
                    yield sse_chunk({"content": event["data"]})
                    sent_content = True
                elif event["type"] == "error":
                    logger.error(f"Error del servicio (stream): {event['data']}")
                    yield sse_chunk({"content": "Lo siento, ocurrió un error."})
                    sent_content = True
                    break

            # 3. Si no se envió contenido, enviar fallback
            if not sent_content:
                yield sse_chunk({"content": "Lo siento, no pude generar una respuesta."})

            # 4. Enviar stop
            yield sse_chunk({}, finish_reason="stop")
            yield "data: [DONE]\n\n"
            
        except Exception:
            logger.exception("❌ Error en streaming de chat completions")
            yield sse_chunk({"content": "Error interno del servidor."})
            yield sse_chunk({}, finish_reason="stop")
            yield "data: [DONE]\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@chat_bp.route("/v1/chat/completions", methods=["OPTIONS"])
def chat_completions_options():
    return jsonify({}), 200

@chat_bp.route("/v1/models", methods=["GET"])
@require_api_key
def list_models():
    models = [
        {"id": "deepseek-chat", "object": "model", "created": 1700000000, "owned_by": "deepseek"},
        {"id": "deepseek-reasoner", "object": "model", "created": 1700000000, "owned_by": "deepseek"},
    ]
    return jsonify({"object": "list", "data": models}), 200