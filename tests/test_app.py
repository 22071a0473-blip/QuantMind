from fastapi.testclient import TestClient

import quantmind.app as app_module


class _Memory:
    configured = False


class _Engine:
    memory = _Memory()


class _Store:
    def close(self) -> None:
        return None


def test_health_reports_dependency_states(monkeypatch) -> None:
    monkeypatch.setattr(app_module, "build_engine", lambda: _Engine())
    monkeypatch.setattr(app_module, "build_store", lambda: _Store())
    monkeypatch.setenv("GROQ_API_KEY", "")

    response = TestClient(app_module.app).get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["database"] == "ok"
    assert body["memory"] == "not_configured"
    assert body["llm"] == "not_configured"
    assert body["universe_size"] > 0
