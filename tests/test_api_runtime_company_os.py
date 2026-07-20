from __future__ import annotations

import json

from fastapi.testclient import TestClient

from apps.api.runtime_company_os import company_os_gfr_projection_payload
from apps.api.runtime_errors import response_contains_unsafe_marker
from apps.api.runtime_service import create_runtime_app


def test_company_os_gfr_projection_payload_is_safe_and_explicit() -> None:
    payload = company_os_gfr_projection_payload()
    serialized = json.dumps(payload, ensure_ascii=False).lower()

    assert payload["projection_id"] == "afs-company-os-gfr-projection-v0"
    assert payload["status"] == "candidate_runtime_projection"
    assert "identity" in payload["gfr_packet_fields"]
    assert "evidence_standard" in payload["gfr_packet_fields"]
    assert "feedback_route" in payload["gfr_packet_fields"]
    assert {gate["id"]: gate["default"] for gate in payload["provider_gates"]} == {
        "llm": "closed",
        "image": "closed",
        "video": "closed",
        "audio": "closed",
        "vision": "closed",
        "asr": "closed",
        "external_download": "closed",
    }
    assert "automatic rule promotion" in payload["runtime_recording"]["not_supported_yet"]
    assert response_contains_unsafe_marker(serialized) is False
    assert "d:\\" not in serialized
    assert "c:\\" not in serialized
    assert "provider_config" not in serialized
    assert "api_key" not in serialized
    assert "signed_url" not in serialized


def test_runtime_serves_company_os_gfr_projection_without_private_material(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    response = client.get("/company-os/gfr-projection")
    payload = response.json()
    serialized = json.dumps(payload, ensure_ascii=False).lower()

    assert response.status_code == 200
    assert payload["source_boundary"]["afs_repo_role"] == "execution_projection_only"
    assert "runtime_verification" in [
        state["id"] for state in payload["evidence_states"]
    ]
    assert "company_os_gfr_projection" in client.get("/capabilities").json()["actions"]
    assert response_contains_unsafe_marker(serialized) is False
    assert "10-startup" in serialized
    assert "d:\\" not in serialized
    assert "c:\\" not in serialized
    assert "raw provider" not in serialized
    assert "real customer names" not in serialized
