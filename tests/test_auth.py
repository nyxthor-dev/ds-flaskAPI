def test_chat_without_api_key_is_rejected(client):
    resp = client.post("/v1/chat/completions", json={"messages": [{"role": "user", "content": "hola"}]})
    assert resp.status_code == 401
    assert resp.get_json()["error"]["code"] == "missing_api_key"


def test_chat_with_wrong_api_key_is_rejected(client):
    resp = client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "hola"}]},
        headers={"Authorization": "Bearer key-incorrecta"},
    )
    assert resp.status_code == 401
    assert resp.get_json()["error"]["code"] == "invalid_api_key"


def test_chat_with_correct_api_key_is_accepted(client, auth_headers):
    resp = client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "hola"}]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
