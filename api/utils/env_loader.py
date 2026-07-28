"""Mantenido por compatibilidad hacia atrás. Usa api.config.Config internamente."""

from config import Config


def get_credentials():
    """Lee credenciales desde variables de entorno (vía Config)."""
    if not Config.DEEPSEEK_TOKEN or not Config.DEEPSEEK_COOKIES:
        raise ValueError(
            "Faltan variables de entorno: DEEPSEEK_TOKEN y DEEPSEEK_COOKIES. "
            "Asegúrate de tener un archivo .env o las variables definidas."
        )
    return Config.DEEPSEEK_TOKEN, Config.DEEPSEEK_COOKIES
