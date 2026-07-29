# routes/chat.py - Compatibilidad total con RooCode (OpenAI format)
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

# Importar lógica de herramientas mejorada
from routes.tool_handler import (
    normalize_messages,
    build_full_prompt,
    build_tool_decision_prompt,
    parse_tool_decision,
    build_tool_response,
    has_tool_in_history,
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

    # 🔥 NORMALIZAR MENSAJES: convertir formatos Anthropic/RooCode a OpenAI
    messages = normalize_messages(messages)
    
    # Log para depuración
    logger.info(f"📨 Mensajes normalizados: {len(messages)} mensajes")
    if Config.LOG_PROMPT_CONTENT:
        logger.debug(f"📨 Contenido: {json.dumps(messages, ensure_ascii=False, indent=2)}")

    model = data.get("model", "deepseek-chat")
    stream = bool(data.get("stream", False))

    error = _validate_params(data)
    if error:
        return openai_error(error)

    # --- LÓGICA DE HERRAMIENTAS (tool calling) ---
    tools = data.get("tools")
    tool_choice = data.get("tool_choice", "auto")

    # Evitar bucles
    has_tool_result = has_tool_in_history(messages)
    should_decide_tool = (
        tools
        and tool_choice != "none"
        and not has_tool_result
    )

    if should_decide_tool:
        logger.info(f"🔧 Tools disponibles: {[t.get('function', {}).get('name') for t in tools]}")
        try:
            decision_prompt = build_tool_decision_prompt(messages, tools)
            
            if Config.LOG_PROMPT_CONTENT:
                logger.debug(f"🔧 Prompt decisión: {decision_prompt[:500]}...")

            session_id = service.create_session()
            decision_response = ""
            for event in service.send_message(
                session_id=session_id,
                prompt=decision_prompt,
                thinking_enabled=False,
                search_enabled=False,
            ):
                if event["type"] == "response" and event["data"] != "FINISHED":
                    decision_response += event["data"]
                elif event["type"] == "error":
                    logger.error(f"Error en decisión de herramienta: {event['data']}")
                    break

            tool_call = parse_tool_decision(decision_response)
            if tool_call:
                logger.info(f"🔧 DeepSeek decidió usar herramienta: {tool_call['function']['name']}")
                return build_tool_response(tool_call, model)

            logger.info("🔧 DeepSeek decidió NO usar herramienta")

        except Exception as e:
            logger.error(f"❌ Error en tool calling: {e}")
            # Si falla, seguimos con texto

    # --- FLUJO NORMAL: respuesta de texto ---
    full_prompt = build_full_prompt(messages)
    if not full_prompt.strip():
        return openai_error("No se encontró contenido en los mensajes")

    thinking_enabled = "reasoner" in model.lower() or data.get("reasoning_enabled") is True
    search_enabled = bool(data.get("search_enabled", False))

    if Config.LOG_PROMPT_CONTENT:
        logger.info(f"📥 Prompt completo: {full_prompt[:200]}...")
    else:
        logger.info(f"📥 Prompt length: {len(full_prompt)} caracteres")

    completion_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created = int(time.time())

    if stream:
        return _stream_response(completion_id, created, model, full_prompt, thinking_enabled, search_enabled)
    else:
        return _full_response(completion_id, created, model, full_prompt, thinking_enabled, search_enabled)

# ---------- Funciones auxiliares (sin cambios) ----------

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
    """Streaming con formato OpenAI estándar."""
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

            yield sse_chunk({"role": "assistant"})

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

            if not sent_content:
                yield sse_chunk({"content": "Lo siento, no pude generar una respuesta."})

            yield sse_chunk({}, finish_reason="stop")
            yield "data: [DONE]\n\n"

        except Exception:
            logger.exception("❌ Error en streaming")
            yield sse_chunk({"content": "Error interno del servidor."})
            yield sse_chunk({}, finish_reason="stop")
            yield "data: [DONE]\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

# ---------- Endpoint /v1/models ----------
@chat_bp.route("/v1/models", methods=["GET"])
@require_api_key
def list_models():
    models = [
        {"id": "deepseek-chat", "object": "model", "created": 1700000000, "owned_by": "deepseek"},
        {"id": "deepseek-reasoner", "object": "model", "created": 1700000000, "owned_by": "deepseek"},
    ]
    return jsonify({"object": "list", "data": models}), 200

@chat_bp.route("/v1/chat/completions", methods=["OPTIONS"])
def chat_completions_options():
    return jsonify({}), 200
