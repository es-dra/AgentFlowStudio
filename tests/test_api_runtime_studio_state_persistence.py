from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app


def test_studio_state_prunes_runtime_bundle_details_before_safety_scan(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "studio-state-runtime-result"
    client.post("/projects", json={"project_id": project_id, "goal": "Studio failed result persistence"})

    state = {
        "nodes": {
            "image_1": {
                "type": "image",
                "title": "generated candidate",
                "prompt": "A character walks through a desert.",
                "result": "Gate blocked\nReason: image provider gate is closed.",
                "params": {
                    "model": "minimax-image-01",
                    "temporaryLockOverrides": [{"asset_id": "va_1", "lock_text": "keep black hair"}],
                    "lastContextBundle": {
                        "trace_summary": "not persisted in studio state",
                        "included_assets": [{"asset_id": "va_1"}],
                    },
                    "visualAssets": [{"asset_id": "va_fixed_1", "label": "Zhou Tong"}],
                },
            }
        },
        "order": ["image_1"],
    }

    response = client.put(f"/projects/{project_id}/studio-state", json={"state": state})

    assert response.status_code == 200
    params = response.json()["state"]["nodes"]["image_1"]["params"]
    assert "lastContextBundle" not in params
    assert "temporaryLockOverrides" not in params
    assert params["visualAssets"][0]["asset_id"] == "va_fixed_1"
