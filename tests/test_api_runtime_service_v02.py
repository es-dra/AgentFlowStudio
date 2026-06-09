from __future__ import annotations

import json

from fastapi.testclient import TestClient

from apps.api.openapi_export import export_openapi_schema
from apps.api.runtime_service import create_runtime_app


def test_runtime_service_v02_lists_imports_and_exports_projects_without_private_paths(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    assert client.get("/projects").json()["projects"] == []

    created = client.post(
        "/projects",
        json={
            "project_id": "proj_runtime_created",
            "project_type": "short_video_campaign",
            "goal": "Created through Runtime Service v0.2 list surface.",
        },
    ).json()
    imported_manifest = {
        "artifact_type": "agentflow_project_manifest",
        "schema_version": "0.1.0",
        "project_id": "proj_runtime_imported",
        "project_type": "short_video_campaign",
        "goal": "Imported through frontend JSON payload.",
        "source_assets": [],
        "runs": [],
        "packages": [],
        "feedback_refs": [],
        "profile_version_refs": [],
        "status": "ready_for_next_round",
        "does_not_store_secrets": True,
        "does_not_store_private_asset_bytes": True,
        "does_not_auto_sync": True,
    }
    imported = client.post("/projects/import", json={"manifest": imported_manifest}).json()

    project_list = client.get("/projects").json()
    exported = client.get("/projects/proj_runtime_imported/export").json()
    serialized = json.dumps({"list": project_list, "exported": exported, "imported": imported}, ensure_ascii=False).lower()

    assert created["artifact"]["artifact_id"]
    assert imported["project_id"] == "proj_runtime_imported"
    assert imported["manifest"]["status"] == "ready_for_next_round"
    assert [item["project_id"] for item in project_list["projects"]] == ["proj_runtime_created", "proj_runtime_imported"]
    assert project_list["projects"][0]["run_count"] == 0
    assert project_list["projects"][0]["artifact"]["role"] == "project_manifest"
    assert exported["download_filename"] == "proj_runtime_imported.project_manifest.json"
    assert exported["manifest"]["project_id"] == "proj_runtime_imported"
    assert exported["non_claims"] == ["not human acceptance", "not business validation", "not durable memory"]
    assert "path" not in serialized
    assert "d:\\" not in serialized
    assert "c:\\" not in serialized


def test_runtime_service_v02_reports_job_progress_and_exports_openapi(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    result = client.post(
        "/provider/validation-plan",
        json={
            "project_id": "proj_runtime_demo",
            "asset_profile_seed": "examples/agentflow/production_memory_asset_profile_seed.example.json",
            "generated_at": "2026-06-08T16:30:00+08:00",
        },
    ).json()
    job = client.get(f"/runs/{result['job']['job_id']}").json()["job"]

    assert job["progress"] == {"stage": "provider_validation_plan", "percent": 100, "terminal": True}

    output_path = tmp_path / "frontend" / "afs-runtime-service.openapi.json"
    exported_path = export_openapi_schema(output_path, runtime_root=tmp_path / "openapi_runtime")
    schema = json.loads(exported_path.read_text(encoding="utf-8"))

    assert schema["info"]["version"] == "0.2.0"
    assert "/projects" in schema["paths"]
    assert "/projects/import" in schema["paths"]
    assert "/projects/{project_id}/export" in schema["paths"]
    assert "/projects/{project_id}/source-assets" in schema["paths"]
    assert "/projects/{project_id}/content-cards" in schema["paths"]
    assert "/projects/{project_id}/canvas-draft" in schema["paths"]
    assert "/projects/{project_id}/scene-inspector" in schema["paths"]
    assert "/projects/{project_id}/review-decisions" in schema["paths"]
    assert "/projects/{project_id}/workbench-state" in schema["paths"]
    assert "/runs/{job_id}" in schema["paths"]
    assert "api_key" not in json.dumps(schema, ensure_ascii=False).lower()


def test_runtime_service_recovers_corrupt_artifact_index_when_listing_projects(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    client.post(
        "/projects",
        json={
            "project_id": "proj_recover_index",
            "project_type": "short_video_campaign",
            "goal": "Recover a local artifact index after an interrupted write.",
        },
    )
    (tmp_path / "artifact_index.json").write_text("", encoding="utf-8")

    project_list = client.get("/projects")
    index = json.loads((tmp_path / "artifact_index.json").read_text(encoding="utf-8"))

    assert project_list.status_code == 200
    assert project_list.json()["projects"][0]["project_id"] == "proj_recover_index"
    assert index["artifacts"]
