def test_health_returns_ok(client):
    """Render のヘルスチェックがここを叩くので、DB なしで 200 が返ること。"""
    res = client.get("/api/health/")

    assert res.status_code == 200
    assert res.json()["status"] == "ok"
