"""Helpers para respuestas de error consistentes con el formato de OpenAI."""

from flask import jsonify


def openai_error(message: str, status_code: int = 400, error_type: str = "invalid_request_error", code: str | None = None):
    """Construye una respuesta (json, status_code) con el formato de error de OpenAI."""
    body = {
        "error": {
            "message": message,
            "type": error_type,
            "code": code,
        }
    }
    return jsonify(body), status_code
