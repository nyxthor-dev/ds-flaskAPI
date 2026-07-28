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

chat_bp = Blueprint("chat", __name__)
service = DeepSeekService()
logger = logging.getLogger(__name__)

# Rango válido de parámetros estilo OpenAI (se validan aunque el backend
# real de DeepSeek no los use todos).
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
    for msg in reversed(messages):
        if msg.get("role") == "user":
            return msg.get("content")
    return None


@chat_bp.route("/v1/chat/completions", methods=["POST"])
@require_api_key
@limiter.limit(Config.RATE_LIMIT_DEFAULT)
def chat_completions():
    """Endpoint compatible con el formato de chat completions de OpenAI.

    Los modelos 'deepseek-chat' / 'deepseek-reasoner' son FICTICIOS: solo
    controlan los parámetros thinking_enabled y search_enabled que se le
    pasan al backend real de DeepSeek.
    """
    data = request.get_json(silent=True)
    if not data:
        return openai_error("Se requiere un cuerpo JSON válido")

    messages = data.get("messages", [])
    if not messages:
        return openai_error("'messages' es obligatorio")

    prompt = _extract_prompt(messages)
    if not prompt:
        return openai_error("No se encontró ningún mensaje con role='user'")

    error = _validate_params(data)
    if error:
        return openai_error(error)

    model = data.get("model", "deepseek-chat")
    thinking_enabled = "reasoner" in model.lower() or data.get("reasoning_enabled") is True
    search_enabled = bool(data.get("search_enabled", False))
    stream = bool(data.get("stream", False))

    if Config.LOG_PROMPT_CONTENT:
        logger.info("📥 Chat request modelo=%s thinking=%s search=%s prompt=%r", model, thinking_enabled, search_enabled, prompt[:100])
    else:
        logger.info("📥 Chat request modelo=%s thinking=%s search=%s len(prompt)=%d", model, thinking_enabled, search_enabled, len(prompt))

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
            elif event["type"] == "response":
                if event["data"] != "FINISHED":
                    respuesta += event["data"]
            elif event["type"] == "error":
                logger.error("Error del servicio: %s", event["data"])
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
    """Streaming real en formato Server-Sent Events, como espera el SDK de OpenAI."""

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
                elif event["type"] == "error":
                    logger.error("Error del servicio (stream): %s", event["data"])
                    yield sse_chunk({}, finish_reason="stop")
                    yield "data: [DONE]\n\n"
                    return

            yield sse_chunk({}, finish_reason="stop")
            yield "data: [DONE]\n\n"
        except Exception:
            logger.exception("❌ Error en streaming de chat completions")
            yield sse_chunk({}, finish_reason="stop")
            yield "data: [DONE]\n\n"

    return Response(generate(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@chat_bp.route("/v1/chat/completions", methods=["OPTIONS"])
def chat_completions_options():
    return jsonify({}), 200


@chat_bp.route("/v1/models", methods=["GET"])
@require_api_key
def list_models():
    models = [
        {
            "id": "deepseek-chat",
            "object": "model",
            "created": 1700000000,
            "owned_by": "deepseek",
            "description": "Modelo base sin razonamiento (thinking_enabled=False)",
        },
        {
            "id": "deepseek-reasoner",
            "object": "model",
            "created": 1700000000,
            "owned_by": "deepseek",
            "description": "Modelo con razonamiento activado (thinking_enabled=True)",
        },
    ]
    return jsonify({"object": "list", "data": models}), 200
