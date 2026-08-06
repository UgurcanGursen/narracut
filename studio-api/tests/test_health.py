from __future__ import annotations

from fastapi.testclient import TestClient

from kurgu_studio_api.app import create_app
from kurgu_studio_api.infrastructure.runtime import build_runtime


def test_health_is_local_liveness_only(tmp_path):
    runtime = build_runtime(database_path=tmp_path / "studio.sqlite3")
    try:
        response = TestClient(create_app(runtime)).get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "scope": "local_beta"}
    finally:
        runtime.project_repository.close()
