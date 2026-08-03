# routes/chat.py - Compatibilidad total con RooCode (OpenAI format)
import json
import logging
import time
import uuid
from typing import Optional

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
    build_tool_response_stream_chunks,
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

    max_tokens = data.get("max_tokens", data.get("max_completion_tokens"))
    if max_tokens is not None:
        if not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or max_tokens <= 0:
            return "'max_tokens' debe ser un entero positivo"

    stop = data.get("stop")
    if stop is not None:
        if isinstance(stop, str):
            pass
        elif isinstance(stop, list):
            if len(stop) > 4 or not all(isinstance(s, str) for s in stop):
                return "'stop' debe ser un string o una lista de hasta 4 strings"
        else:
            return "'stop' debe ser un string o una lista de strings"

    return None

def _get_stop_sequences(data: dict) -> list:
    stop = data.get("stop")
    if stop is None:
        return []
    if isinstance(stop, str):
        return [stop]
    return list(stop)

def _apply_stop_and_truncate(text: str, stop_sequences: list, max_tokens: Optional[int], model: str):
    """Aplica stop sequences (corta el texto en la primera que aparezca) y
    trunca por max_tokens (aproximado, vía count_tokens). Devuelve
    (texto_final, finish_reason) donde finish_reason es 'stop', 'length' o None
    (None = terminó naturalmente, se debe usar 'stop' igualmente aguas arriba).
    """
    finish_reason = None

    earliest_idx = None
    for seq in stop_sequences:
        if not seq:
            continue
        idx = text.find(seq)
        if idx != -1 and (earliest_idx is None or idx < earliest_idx):
            earliest_idx = idx
    if earliest_idx is not None:
        text = text[:earliest_idx]
        finish_reason = "stop"

    if max_tokens is not None:
        approx_chars_per_token = 4
        max_chars = max_tokens * approx_chars_per_token
        if len(text) > max_chars or count_tokens(text, model) > max_tokens:
            words = text.split(" ")
            truncated = []
            for w in words:
                candidate = " ".join(truncated + [w])
                if count_tokens(candidate, model) > max_tokens:
                    break
                truncated.append(w)
            text = " ".join(truncated)
            finish_reason = "length"

    return text, finish_reason

# ============================================================
# /v1/chat/completions (OpenAI compatible)
# ============================================================

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

    messages = normalize_messages(messages)

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
                prompt_tokens = count_tokens(decision_prompt, model)
                completion_tokens = count_tokens(decision_response, model)
                if stream:
                    completion_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
                    created = int(time.time())
                    chunks = build_tool_response_stream_chunks(tool_call, model, completion_id, created)
                    return Response(
                        (c for c in chunks),
                        mimetype="text/event-stream",
                        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
                    )
                return build_tool_response(
                    tool_call, model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                )

            logger.info("🔧 DeepSeek decidió NO usar herramienta")

        except Exception as e:
            logger.error(f"❌ Error en tool calling: {e}")

    # --- FLUJO NORMAL: respuesta de texto ---
    full_prompt = build_full_prompt(messages)
    if not full_prompt.strip():
        return openai_error("No se encontró contenido en los mensajes")

    thinking_enabled = "reasoner" in model.lower() or data.get("reasoning_enabled") is True
    search_enabled = bool(data.get("search_enabled", False))

    max_tokens = data.get("max_tokens", data.get("max_completion_tokens"))
    stop_sequences = _get_stop_sequences(data)
    stream_options = data.get("stream_options") or {}
    include_usage = bool(stream_options.get("include_usage", False))

    in_session_id = data.get("session_id")
    in_parent_message_id = data.get("parent_message_id")
    if in_parent_message_id is not None:
        try:
            in_parent_message_id = int(in_parent_message_id)
        except (TypeError, ValueError):
            return openai_error("'parent_message_id' debe ser un entero")

    if Config.LOG_PROMPT_CONTENT:
        logger.info(f"📥 Prompt completo: {full_prompt[:200]}...")
    else:
        logger.info(f"📥 Prompt length: {len(full_prompt)} caracteres")

    completion_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created = int(time.time())

    if stream:
        return _stream_response(
            completion_id, created, model, full_prompt, thinking_enabled, search_enabled,
            stop_sequences=stop_sequences, max_tokens=max_tokens, include_usage=include_usage,
            session_id=in_session_id, parent_message_id=in_parent_message_id,
        )
    else:
        return _full_response(
            completion_id, created, model, full_prompt, thinking_enabled, search_enabled,
            stop_sequences=stop_sequences, max_tokens=max_tokens,
            session_id=in_session_id, parent_message_id=in_parent_message_id,
        )

# ============================================================
# /api/chat/regenerate
# ============================================================

@chat_bp.route("/api/chat/regenerate", methods=["POST"])
@require_api_key
@limiter.limit(Config.RATE_LIMIT_DEFAULT)
def api_regenerate():
    """Regenera una respuesta existente."""
    data = request.get_json(silent=True) or {}

    session_id = data.get("session_id")
    child_message_id = data.get("child_message_id")
    stream = bool(data.get("stream", False))
    thinking_enabled = bool(data.get("thinking_enabled", True))
    search_enabled = bool(data.get("search_enabled", True))
    user_options = data.get("user_options")

    if not session_id:
        return openai_error("'session_id' es obligatorio")
    if child_message_id is None:
        return openai_error("'child_message_id' es obligatorio")
    try:
        child_message_id = int(child_message_id)
    except (TypeError, ValueError):
        return openai_error("'child_message_id' debe ser un entero")

    completion_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created = int(time.time())
    model = data.get("model", "deepseek-chat")

    if stream:
        return _stream_events(
            completion_id, created, model,
            service.regenerate_message(
                session_id=session_id,
                child_message_id=child_message_id,
                thinking_enabled=thinking_enabled,
                search_enabled=search_enabled,
                user_options=user_options,
            ),
            stop_sequences=[],
            max_tokens=None,
            include_usage=False,
            session_id=session_id,
        )
    else:
        return _full_events(
            completion_id, created, model,
            service.regenerate_message(
                session_id=session_id,
                child_message_id=child_message_id,
                thinking_enabled=thinking_enabled,
                search_enabled=search_enabled,
                user_options=user_options,
            ),
            stop_sequences=[],
            max_tokens=None,
            session_id=session_id,
        )

# ============================================================
# /api/chat/stop
# ============================================================

@chat_bp.route("/api/chat/stop", methods=["POST"])
@require_api_key
@limiter.limit(Config.RATE_LIMIT_DEFAULT)
def api_stop():
    """Detiene la generación en curso de un mensaje."""
    data = request.get_json(silent=True) or {}

    session_id = data.get("session_id")
    message_id = data.get("message_id")

    if not session_id:
        return openai_error("'session_id' es obligatorio")
    if message_id is None:
        return openai_error("'message_id' es obligatorio")
    try:
        message_id = int(message_id)
    except (TypeError, ValueError):
        return openai_error("'message_id' debe ser un entero")

    result = service.stop_message_stream(session_id=session_id, message_id=message_id)
    if result.get("success"):
        return jsonify({"success": True, "message": "Stream detenido", "data": result.get("data")}), 200
    return openai_error(result.get("error", "Error al detener el stream"), status_code=502)

# ============================================================
# /api/chat/continue
# ============================================================

@chat_bp.route("/api/chat/continue", methods=["POST"])
@require_api_key
@limiter.limit(Config.RATE_LIMIT_DEFAULT)
def api_continue():
    """Continúa una respuesta que quedó INCOMPLETE."""
    data = request.get_json(silent=True) or {}

    session_id = data.get("session_id")
    message_id = data.get("message_id")
    fallback_to_resume = bool(data.get("fallback_to_resume", True))
    stream = bool(data.get("stream", False))

    if not session_id:
        return openai_error("'session_id' es obligatorio")
    if message_id is None:
        return openai_error("'message_id' es obligatorio")
    try:
        message_id = int(message_id)
    except (TypeError, ValueError):
        return openai_error("'message_id' debe ser un entero")

    completion_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created = int(time.time())
    model = data.get("model", "deepseek-chat")

    if stream:
        return _stream_events(
            completion_id, created, model,
            service.continue_message(
                session_id=session_id,
                message_id=message_id,
                fallback_to_resume=fallback_to_resume,
            ),
            stop_sequences=[],
            max_tokens=None,
            include_usage=False,
            session_id=session_id,
        )
    else:
        return _full_events(
            completion_id, created, model,
            service.continue_message(
                session_id=session_id,
                message_id=message_id,
                fallback_to_resume=fallback_to_resume,
            ),
            stop_sequences=[],
            max_tokens=None,
            session_id=session_id,
        )

# ============================================================
# FUNCIONES AUXILIARES GENÉRICAS
# ============================================================

def _full_events(
    completion_id, created, model, event_generator,
    stop_sequences=None, max_tokens=None, session_id=None,
):
    """Procesa un generador de eventos y devuelve respuesta JSON completa."""
    stop_sequences = stop_sequences or []
    try:
        respuesta, razonamiento = "", ""
        response_message_id = None
        is_incomplete = False

        for event in event_generator:
            if event["type"] == "think":
                razonamiento += event["data"]
            elif event["type"] == "response" and event["data"] != "FINISHED":
                respuesta += event["data"]
            elif event["type"] == "done":
                done_data = event["data"]
                if isinstance(done_data, dict):
                    response_message_id = done_data.get("msg_id")
                    is_incomplete = done_data.get("is_incomplete", False)
                else:
                    response_message_id = done_data
            elif event["type"] == "error":
                logger.error(f"Error del servicio: {event['data']}")
                return openai_error(event["data"], status_code=502, error_type="server_error")

        if not respuesta:
            respuesta = "Lo siento, no pude generar una respuesta. Por favor, intenta de nuevo."

        respuesta, truncation_reason = _apply_stop_and_truncate(respuesta, stop_sequences, max_tokens, model)
        finish_reason = truncation_reason or "stop"

        prompt_tokens = 0  # No tenemos el prompt original aquí en regenerate/continue
        completion_tokens = count_tokens(respuesta, model)

        message = {"role": "assistant", "content": respuesta}
        if razonamiento:
            message["reasoning_content"] = razonamiento

        response = {
            "id": completion_id,
            "object": "chat.completion",
            "created": created,
            "model": model,
            "choices": [{
                "index": 0,
                "message": message,
                "finish_reason": finish_reason,
                "logprobs": None,
            }],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
            "session_id": session_id,
            "parent_message_id": response_message_id,
            "is_incomplete": is_incomplete,
        }
        return jsonify(response), 200

    except Exception as e:
        logger.exception("❌ Error en chat completions")
        message = str(e) if Config.EXPOSE_ERROR_DETAILS else "Error al generar la respuesta"
        return openai_error(message, status_code=502, error_type="server_error")

def _stream_events(
    completion_id, created, model, event_generator,
    stop_sequences=None, max_tokens=None, include_usage=False,
    session_id=None,
):
    """Streaming con formato OpenAI estándar desde cualquier generador de eventos."""
    stop_sequences = stop_sequences or []

    def sse_chunk(delta: dict, finish_reason=None, logprobs=None):
        payload = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason, "logprobs": logprobs}],
        }
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    def sse_usage_chunk(prompt_tokens: int, completion_tokens: int):
        payload = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        }
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    def sse_meta_chunk(session_id_out, parent_message_id_out, is_incomplete_out):
        payload = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [],
            "session_id": session_id_out,
            "parent_message_id": parent_message_id_out,
            "is_incomplete": is_incomplete_out,
        }
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    def generate():
        sent_content = False
        full_text = ""
        finish_reason = "stop"
        response_message_id = None
        is_incomplete = False
        try:
            yield sse_chunk({"role": "assistant"})

            for event in event_generator:
                if event["type"] == "think":
                    yield sse_chunk({"reasoning_content": event["data"]})
                elif event["type"] == "done":
                    done_data = event["data"]
                    if isinstance(done_data, dict):
                        response_message_id = done_data.get("msg_id")
                        is_incomplete = done_data.get("is_incomplete", False)
                    else:
                        response_message_id = done_data
                elif event["type"] == "response" and event["data"] != "FINISHED":
                    chunk_text = event["data"]

                    combined = full_text + chunk_text
                    cut_at = None
                    for seq in stop_sequences:
                        if not seq:
                            continue
                        idx = combined.find(seq)
                        if idx != -1 and (cut_at is None or idx < cut_at):
                            cut_at = idx

                    if cut_at is not None:
                        remaining_to_emit = combined[len(full_text):cut_at]
                        if remaining_to_emit:
                            yield sse_chunk({"content": remaining_to_emit})
                            sent_content = True
                        full_text = combined[:cut_at]
                        finish_reason = "stop"
                        break

                    full_text = combined
                    if max_tokens is not None and count_tokens(full_text, model) >= max_tokens:
                        yield sse_chunk({"content": chunk_text})
                        sent_content = True
                        finish_reason = "length"
                        break

                    yield sse_chunk({"content": chunk_text})
                    sent_content = True
                elif event["type"] == "error":
                    logger.error(f"Error del servicio (stream): {event['data']}")
                    yield sse_chunk({"content": "Lo siento, ocurrió un error."})
                    sent_content = True
                    break

            if not sent_content:
                yield sse_chunk({"content": "Lo siento, no pude generar una respuesta."})

            yield sse_chunk({}, finish_reason=finish_reason)

            if include_usage:
                prompt_tokens = 0
                completion_tokens = count_tokens(full_text, model)
                yield sse_usage_chunk(prompt_tokens, completion_tokens)

            yield sse_meta_chunk(session_id, response_message_id, is_incomplete)
            yield "data: [DONE]\n\n"

        except Exception:
            logger.exception("❌ Error en streaming")
            yield sse_chunk({"content": "Error interno del servidor."})
            yield sse_chunk({}, finish_reason="stop")
            yield "data: [DONE]\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

# ============================================================
# /v1/models
# ============================================================

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
