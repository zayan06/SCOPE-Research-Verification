from fastapi.testclient import TestClient

from api.main import app


def test_health_endpoint_is_live_and_marks_development_mode() -> None:
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": "0.1.0",
        "mode": "local_development",
    }
