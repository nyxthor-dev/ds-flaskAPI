"""Conteo de tokens SIN dependencias compiladas (nada de tiktoken).

tiktoken requiere compilar una extensión en Rust, lo cual falla en varios
entornos de build gestionado (p. ej. Render) si no hay toolchain de Rust
disponible. En su lugar usamos una heurística estándar: para texto en
inglés/español, 1 token ronda ~4 caracteres, y casi nunca es menos que el
número de palabras. Tomamos el máximo de ambas estimaciones, que en la
práctica se acerca bastante al conteo real de BPE sin instalar nada.
"""

import re

_WORD_RE = re.compile(r"\S+")


def count_tokens(text: str, model: str | None = None) -> int:
    """Estimación de tokens sin librerías compiladas.

    No es un conteo exacto (para eso haría falta el tokenizador real de
    DeepSeek, que no es público), pero es estable, rápida, y suficiente
    para reportar el campo 'usage' de forma orientativa.
    """
    if not text:
        return 0

    words = len(_WORD_RE.findall(text))
    chars_estimate = len(text) / 4  # heurística habitual: ~4 caracteres por token

    return max(1, words, round(chars_estimate))
