from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.runtime_errors import response_contains_unsafe_marker
from apps.api.runtime_service import create_runtime_app
from apps.api.runtime_store import RuntimeStore


def test_runtime_service_reports_health_and_capabilities_without_secrets(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    health = client.get("/health").json()
    capabilities = client.get("/capabilities").json()
    serialized = json.dumps({"health": health, "capabilities": capabilities}, ensure_ascii=False).lower()

    assert health["service"] == "agentflow_runtime_service"
    assert health["status"] == "ready"
    assert health["runtime_root_persisted"] is False
    assert capabilities["actions"] == [
        "create_project",
        "list_projects",
        "read_project_manifest",
        "read_artifact",
        "read_job",
        "record_feedback",
        "prompt_optimization",
        "script_draft_plan",
        "image_asset_upload",
        "visual_asset_register",
        "keyframe_generation",
        "video_generation",
        "generation_comparison",
        "studio_state",
        "export_openapi_schema",
    ]
    assert capabilities["studio_flow"]["target_status"] == "ready_for_next_round"
    assert capabilities["studio_flow"]["actions"] == [
        "add_reference",
        "draft_canvas",
        "start_first_generation_check",
        "record_review_note",
        "start_next_round",
        "request_gated_generation",
    ]
    assert "asset_test_run" not in capabilities["actions"]
    assert "two_round_validate" not in capabilities["actions"]
    assert "provider_validation_plan" not in capabilities["actions"]
    assert "api_key" not in serialized
    assert "token" not in serialized
    assert "d:\\" not in serialized


def test_runtime_service_allows_local_studio_cors(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    localhost_response = client.options(
        "/health",
        headers={
            "Origin": "http://127.0.0.1:8789",
            "Access-Control-Request-Method": "GET",
        },
    )
    file_response = client.options(
        "/health",
        headers={
            "Origin": "null",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert localhost_response.status_code == 200
    assert localhost_response.headers["access-control-allow-origin"] == "http://127.0.0.1:8789"
    assert file_response.status_code == 200
    assert file_response.headers["access-control-allow-origin"] == "null"


def test_runtime_service_serves_studio_static_entry_without_private_paths(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    redirect = client.get("/studio", follow_redirects=False)
    index = client.get("/studio/")
    app_js = client.get("/studio/src/main.js")
    serialized = (index.text + app_js.text).lower()

    assert redirect.status_code in {307, 308}
    assert redirect.headers["location"] == "/studio/"
    assert index.status_code == 200
    assert '<div id="app">' in index.text
    assert '<script type="module" src="./src/main.js"></script>' in index.text
    assert app_js.status_code == 200
    assert index.headers["cache-control"] == "no-store"
    assert app_js.headers["cache-control"] == "no-store"
    assert "createStore" in app_js.text
    assert "d:\\" not in serialized
    assert "c:\\" not in serialized
    assert "api_key" not in serialized
    assert "signed_url" not in serialized


def test_runtime_service_does_not_serve_retired_workbench_static_entry(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    assert client.get("/workbench", follow_redirects=False).status_code == 404
    assert client.get("/workbench/").status_code == 404
    assert client.get("/workbench/src/app.js").status_code == 404


def test_runtime_service_creates_project_manifest_and_reads_safe_artifact(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    created = client.post(
        "/projects",
        json={
            "project_id": "proj_runtime_demo",
            "project_type": "short_video_campaign",
            "goal": "Validate local AFS runtime service contract.",
            "status": "in_progress",
        },
    ).json()

    assert created["project_id"] == "proj_runtime_demo"
    assert created["manifest"]["artifact_type"] == "agentflow_project_manifest"
    assert created["artifact"]["artifact_id"]
    assert "path" not in created["artifact"]

    fetched = client.get("/projects/proj_runtime_demo/manifest").json()
    artifact = client.get(f"/artifacts/{created['artifact']['artifact_id']}").json()

    assert fetched["manifest"]["project_id"] == "proj_runtime_demo"
    assert artifact["artifact_type"] == "agentflow_project_manifest"
    assert artifact["payload"]["does_not_store_secrets"] is True
    assert "path" not in json.dumps(artifact, ensure_ascii=False).lower()


def test_runtime_service_removed_production_memory_http_routes_return_404(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    for path in ("/runs/asset-test", "/runs/two-round-validate", "/provider/validation-plan"):
        response = client.post(path, json={"project_id": "proj_runtime_demo"})
        assert response.status_code == 404, path


def test_runtime_service_current_error_projection_does_not_leak_unsafe_exception_text(tmp_path, monkeypatch) -> None:
    def raise_unsafe_error(self: RuntimeStore, project_id: str) -> dict:
        raise ValueError(r"D:\private\providers.local.json api_key token signed_url provider raw response")

    monkeypatch.setattr(RuntimeStore, "ensure_project_manifest", raise_unsafe_error)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    response = client.get("/projects/proj_runtime_demo/manifest")

    assert response.status_code == 422
    assert response.json()["detail"] == {
        "error": "invalid_project_manifest",
        "detail_code": "invalid_request",
    }
    assert response_contains_unsafe_marker(response.json()) is False


def test_frontend_runtime_service_request_examples_match_current_api_contract(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_LLM", raising=False)
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VIDEO", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    fixture_dir = Path("examples/frontend_runtime_service")

    project_request = _load_fixture(fixture_dir / "create_project.request.example.json")
    project = client.post("/projects", json=project_request).json()
    assert project["manifest"]["project_id"] == project_request["project_id"]

    feedback_request = _load_fixture(fixture_dir / "feedback_record.request.example.json")
    feedback = client.post("/feedback", json=feedback_request).json()
    assert feedback["feedback_event"]["feedback_is_memory"] is False

    prompt_fixture = _load_fixture(fixture_dir / "prompt_optimizer_nodes" / "text_node.zh.json")
    prompt = client.post(
        f"/projects/{project_request['project_id']}/prompt-optimizations",
        json=prompt_fixture["request"],
    ).json()
    assert prompt["job"]["action"] == "prompt_optimization"
    assert prompt["provider_calls_started"] is False

    keyframe = client.post(
        f"/projects/{project_request['project_id']}/keyframe-generations",
        json={
            "node_id": "image-node-fixture-001",
            "prompt_text": "A quiet cinematic street scene.",
            "target_platform": "short_video",
            "style": "cinematic",
            "candidate_count": 1,
            "generated_at": "2026-06-13T12:00:00+08:00",
        },
    ).json()
    assert keyframe["job"]["action"] == "keyframe_generation"
    assert keyframe["job"]["status"] == "blocked"
    assert keyframe["provider_calls_started"] is False

    script = client.post(
        "/provider/script-draft-plan",
        json={
            "project_id": project_request["project_id"],
            "goal": "Draft a short scene script from the current canvas.",
            "target_platform": "short_video",
            "style": "clear_demo",
            "generated_at": "2026-06-13T12:10:00+08:00",
        },
    ).json()
    assert script["job"]["action"] == "llm_script_draft_plan"
    assert script["provider_calls_started"] is False


def _load_fixture(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    serialized = json.dumps(payload, ensure_ascii=False).lower()
    assert "api_key" not in serialized
    assert "token" not in serialized
    assert "d:\\" not in serialized
    assert "c:\\" not in serialized
    return payload
