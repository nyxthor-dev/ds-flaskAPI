"""Conteo de tokens aproximado con tiktoken.

DeepSeek no publica su propio tokenizador vía tiktoken, así que usamos el
encoding de OpenAI (cl100k_base) como aproximación razonable — mucho más
fiel que contar palabras con str.split(), y suficiente para reportar 'usage'
de forma compatible con clientes que esperan ese campo.
"""

import logging

logger = logging.getLogger(__name__)

try:
    import tiktoken

    _ENCODING = tiktoken.get_encoding("cl100k_base")
except Exception:  # pragma: no cover - tiktoken puede fallar al descargar datos
    logger.warning("tiktoken no disponible, se usará una aproximación por palabras")
    _ENCODING = None


def count_tokens(text: str, model: str | None = None) -> int:
    if not text:
        return 0
    if _ENCODING is not None:
        try:
            return len(_ENCODING.encode(text))
        except Exception:
            logger.debug("Fallo al tokenizar con tiktoken, usando fallback", exc_info=True)
    # Fallback muy aproximado
    return max(1, len(text.split()))
