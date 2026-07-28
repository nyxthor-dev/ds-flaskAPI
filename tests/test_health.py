def test_health_ok(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["credentials_configured"] is True


def test_root_info(client):
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "deepseek-chat" in data["supported_models"]
