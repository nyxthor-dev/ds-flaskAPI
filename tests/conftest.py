"""Configuración compartida de pytest.

Evita cualquier llamada real a la red (descarga de WASM, DeepSeekClient real)
inyectando un módulo 'deepseekcli' falso ANTES de que se importe la app, ya
que services/deepseek_service.py es un singleton que solo se inicializa una
vez por proceso.
"""

import os
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

API_DIR = Path(__file__).resolve().parent.parent / "api"
sys.path.insert(0, str(API_DIR))

os.environ.setdefault("DEEPSEEK_TOKEN", "test-token")
os.environ.setdefault("DEEPSEEK_COOKIES", "test-cookies")
os.environ.setdefault("API_KEYS", "test-api-key")
os.environ.setdefault("REQUIRE_API_KEY", "true")
os.environ.setdefault("LOG_LEVEL", "ERROR")

# --- Doble de prueba para DeepSeekClient, instalado antes de cualquier import ---
mock_client = MagicMock()
mock_client.create_chat_session.return_value = "session-123"


def _fake_chat(*args, on_think_chunk=None, on_response_chunk=None, **kwargs):
    if on_think_chunk:
        on_think_chunk("razonamiento de prueba")
    if on_response_chunk:
        on_response_chunk("respuesta de prueba")
    return "razonamiento de prueba", "respuesta de prueba", "msg-1"


mock_client.chat.side_effect = _fake_chat

fake_module = types.ModuleType("deepseekcli")
fake_module.DeepSeekClient = MagicMock(return_value=mock_client)
sys.modules.setdefault("deepseekcli", fake_module)


@pytest.fixture
def fake_client():
    """Resetea el estado del mock compartido entre tests."""
    mock_client.reset_mock()
    mock_client.create_chat_session.return_value = "session-123"
    mock_client.chat.side_effect = _fake_chat
    yield mock_client


@pytest.fixture
def app(fake_client):
    import app as app_module

    app_module.app.config.update(TESTING=True)
    return app_module.app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-api-key"}
