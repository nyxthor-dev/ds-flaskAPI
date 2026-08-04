"""
Configuración centralizada de la aplicación.
Todo se lee de variables de entorno para no acoplar código con secretos.
"""

import os


def _split_csv(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


class Config:
    # --- Credenciales DeepSeek (obligatorias) ---
    DEEPSEEK_TOKEN = os.getenv("DEEPSEEK_TOKEN")
    DEEPSEEK_COOKIES = os.getenv("DEEPSEEK_COOKIES")
    DEEPSEEK_LOGIN_DIR = os.getenv("DEEPSEEK_LOGIN_DIR", ".login_api")

    # --- Seguridad de la propia API ---
    # Lista de API keys propias (separadas por coma) que los clientes deben
    # enviar como "Authorization: Bearer <key>". Si está vacía, la API
    # queda abierta (NO recomendado en producción).
    API_KEYS = set(_split_csv(os.getenv("API_KEYS", "")))
    REQUIRE_API_KEY = os.getenv("REQUIRE_API_KEY", "true").lower() == "true"

    # --- CORS ---
    # "*" solo se recomienda en desarrollo. En producción, define
    # CORS_ORIGINS="https://tuapp.com,https://otra.com"
    CORS_ORIGINS = _split_csv(os.getenv("CORS_ORIGINS", "*"))

    # --- Logging ---
    LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper()
    # Nunca loguear el contenido de prompts/respuestas por defecto (privacidad)
    LOG_PROMPT_CONTENT = os.getenv("LOG_PROMPT_CONTENT", "false").lower() == "true"

    # --- Entorno ---
    ENV = os.getenv("FLASK_ENV", "production")
    DEBUG = ENV == "development"
    # Nunca devolver detalles internos de excepciones al cliente en producción
    EXPOSE_ERROR_DETAILS = os.getenv("EXPOSE_ERROR_DETAILS", "true").lower() == "true" or DEBUG

    # --- Rate limiting ---
    RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "60 per minute")
    RATE_LIMIT_STORAGE_URI = os.getenv("RATE_LIMIT_STORAGE_URI", "memory://")

    # --- Concurrencia hacia el backend de DeepSeek ---
    # Limita cuántas conversaciones simultáneas se envían al backend para
    # no saturar la sesión compartida.
    MAX_CONCURRENT_CHATS = int(os.getenv("MAX_CONCURRENT_CHATS", "4"))
    CHAT_TIMEOUT_SECONDS = int(os.getenv("CHAT_TIMEOUT_SECONDS", "120"))

    PORT = int(os.getenv("PORT", "5000"))

    @classmethod
    def validate(cls) -> list[str]:
        """Devuelve una lista de problemas de configuración (vacía si todo OK)."""
        problems = []
        if not cls.DEEPSEEK_TOKEN or not cls.DEEPSEEK_COOKIES:
            problems.append("Faltan DEEPSEEK_TOKEN y/o DEEPSEEK_COOKIES")
        if cls.REQUIRE_API_KEY and not cls.API_KEYS:
            problems.append(
                "REQUIRE_API_KEY=true pero no hay ninguna API_KEYS configurada. "
                "Define API_KEYS o pon REQUIRE_API_KEY=false explícitamente."
            )
        if cls.CORS_ORIGINS == ["*"] and cls.ENV == "production":
            problems.append(
                "CORS_ORIGINS='*' en producción no es recomendado; restringe a tus dominios."
            )
        return problems
