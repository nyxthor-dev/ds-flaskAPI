def test_missing_messages_returns_400(client, auth_headers):
    resp = client.post("/v1/chat/completions", json={}, headers=auth_headers)
    assert resp.status_code == 400


def test_invalid_temperature_returns_400(client, auth_headers):
    resp = client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "hola"}], "temperature": 5},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_chat_completion_happy_path(client, auth_headers, fake_client):
    resp = client.post(
        "/v1/chat/completions",
        json={"model": "deepseek-reasoner", "messages": [{"role": "user", "content": "hola"}]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["object"] == "chat.completion"
    assert data["choices"][0]["message"]["content"] == "respuesta de prueba"
    assert data["choices"][0]["message"]["reasoning_content"] == "razonamiento de prueba"
    assert data["usage"]["total_tokens"] > 0
    fake_client.chat.assert_called_once()
    assert fake_client.chat.call_args.kwargs["thinking_enabled"] is True


def test_models_endpoint(client, auth_headers):
    resp = client.get("/v1/models", headers=auth_headers)
    assert resp.status_code == 200
    ids = [m["id"] for m in resp.get_json()["data"]]
    assert "deepseek-chat" in ids and "deepseek-reasoner" in ids


def test_streaming_returns_sse(client, auth_headers):
    resp = client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "hola"}], "stream": True},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.mimetype == "text/event-stream"
    body = resp.get_data(as_text=True)
    assert "data: [DONE]" in body
