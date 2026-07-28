"""Autenticación por API key propia para proteger la API."""

import hmac
from functools import wraps

from flask import request

from config import Config
from utils.errors import openai_error


def _valid_key(provided: str) -> bool:
    # Comparación en tiempo constante para evitar timing attacks
    return any(hmac.compare_digest(provided, key) for key in Config.API_KEYS)


def require_api_key(view_func):
    """Exige 'Authorization: Bearer <API_KEY>' si REQUIRE_API_KEY está activo."""

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not Config.REQUIRE_API_KEY:
            return view_func(*args, **kwargs)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return openai_error(
                "Falta la cabecera Authorization: Bearer <API_KEY>",
                status_code=401,
                error_type="authentication_error",
                code="missing_api_key",
            )

        provided = auth_header.removeprefix("Bearer ").strip()
        if not provided or not _valid_key(provided):
            return openai_error(
                "API key inválida",
                status_code=401,
                error_type="authentication_error",
                code="invalid_api_key",
            )

        return view_func(*args, **kwargs)

    return wrapper
