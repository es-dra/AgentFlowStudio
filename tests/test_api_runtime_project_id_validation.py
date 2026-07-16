from __future__ import annotations

import json

from fastapi.testclient import TestClient

from apps.api.runtime_models import PROJECT_ID_MAX_LENGTH
from apps.api.runtime_service import create_runtime_app


def test_project_create_rejects_overlong_project_ids_without_runtime_path_leak(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    for project_id in ("p" * 300, "项目" * 300, "🙂" * 300):
        response = client.post("/projects", json={"project_id": project_id, "goal": "Long id"})
        body = response.json()
        serialized = json.dumps(body, ensure_ascii=False)

        assert response.status_code == 422
        assert body["detail"]["error"] == "request_validation_failed"
        assert "body.project_id" in serialized
        assert str(tmp_path) not in serialized

    assert not list((tmp_path / "projects").iterdir())


def test_project_create_openapi_exposes_project_id_max_length(tmp_path) -> None:
    schema = create_runtime_app(runtime_root=tmp_path).openapi()

    assert (
        schema["components"]["schemas"]["ProjectCreateRequest"]["properties"]["project_id"]["maxLength"]
        == PROJECT_ID_MAX_LENGTH
    )
