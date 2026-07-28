import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))

from utils.tokens import count_tokens


def test_count_tokens_empty():
    assert count_tokens("") == 0


def test_count_tokens_basic_text():
    assert count_tokens("Hola, ¿cómo estás?") > 0


def test_count_tokens_is_stable():
    text = "Este es un texto de prueba para contar tokens."
    assert count_tokens(text) == count_tokens(text)
