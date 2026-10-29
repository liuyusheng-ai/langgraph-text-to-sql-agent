import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'api.db'}")
    import app as app_module
    importlib.reload(app_module)
    return TestClient(app_module.app)


def test_health_and_query_and_history(client) -> None:
    assert client.get("/healthz").json() == {"status": "ok"}
    body = client.post("/api/query", json={"question": "统计各地区销售额"}).json()
    assert body["status"] == "completed" and len(body["rows"]) == 3
    assert body["sql"].endswith("LIMIT 200")
    items = client.get("/api/history", params={"limit": 500}).json()["items"]
    assert items[0]["status"] == "completed"


def test_blank_and_write_questions_are_refused(client) -> None:
    assert client.post("/api/query", json={"question": "   "}).json()["status"] == "rejected"
    assert client.post("/api/query", json={"question": "清空销售表"}).json()["status"] == "rejected"
    assert client.post("/api/query", json={"question": ""}).status_code == 422
