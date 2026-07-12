from __future__ import annotations

import logging

from fastapi.testclient import TestClient

from agentflow.harness.json_io import write_json
from apps.api.runtime_file_logging import configure_runtime_file_logging
from apps.api.runtime_logging import log_business_event
from apps.api.runtime_service import create_runtime_app
from apps.api.runtime_store import RuntimeStore


def test_studio_client_event_logging_sanitizes_nested_sensitive_fragments(tmp_path, monkeypatch, caplog) -> None:
    monkeypatch.setenv("AFS_FILE_LOG_ENABLED", "true")
    monkeypatch.setenv("AFS_FILE_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("AFS_FILE_LOG_NAME", "client-event-hardening")
    caplog.set_level(logging.INFO, logger="afs.runtime.request")

    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    response = client.post(
        "/studio/client-events",
        json={
            "event_type": "client_event_probe",
            "severity": "warning",
            "message": r"preview failed for D:\private\story.png with Bearer leaked-token",
            "project_id": "log-hardening",
            "action": "client_event_probe",
            "details": {
                "safe_count": 3,
                "nested": {
                    "api_key": "sk-fixture-client-event",
                    "authorization": "Bearer nested-client-token",
                    "prompt": r"use C:\Users\chenzy\private\prompt.png",
                    "source_path": r"D:\private\clips\sample.mov",
                },
                "raw_payload": {
                    "provider_raw_response": {
                        "access_token": "raw-access-token",
                        "signed_url": "https://signed.example.test/private.png?token=abc",
                    }
                },
                "media_bytes": "AAAA",
            },
            "generated_at": "2026-07-02T12:00:00+08:00",
        },
    )

    assert response.status_code == 200
    combined = _combined_logs(caplog, tmp_path / "logs")
    assert "safe_count" in combined
    assert "sk-fixture-client-event" not in combined
    assert "nested-client-token" not in combined
    assert "raw-access-token" not in combined
    assert "leaked-token" not in combined
    assert "api_key" not in combined.lower()
    assert "access_token" not in combined.lower()
    assert "authorization" not in combined.lower()
    assert "raw_payload" not in combined.lower()
    assert "provider_raw_response" not in combined.lower()
    assert "media_bytes" not in combined.lower()
    assert "signed_url" not in combined.lower()
    assert "bearer " not in combined.lower()
    assert "d:\\" not in combined.lower()
    assert "c:\\" not in combined.lower()
    assert "sample.mov" not in combined.lower()
    assert "https://signed.example.test" not in combined.lower()
    assert "AAAA" not in combined


def test_process_file_logging_sanitizes_prompt_path_and_raw_payload_fields(tmp_path, caplog) -> None:
    configure_runtime_file_logging(
        {
            "AFS_FILE_LOG_ENABLED": "true",
            "AFS_FILE_LOG_DIR": str(tmp_path / "logs"),
            "AFS_FILE_LOG_NAME": "process-hardening",
        }
    )
    caplog.set_level(logging.INFO, logger="afs.runtime.request")

    log_business_event(
        "video_generation_probe",
        request_id="req_harden",
        project_id="log-hardening",
        provider_prompt=r"draw from D:\private\asset.png with api_key=sk-fixture-process",
        details={
            "raw_payload": {"client_secret": "client-secret-value"},
            "nested": {"refresh_token": "refresh-token-value", "safe_label": "kept"},
            "local_path": r"C:\Users\chenzy\private\asset.mov",
        },
        file_log_domain="video",
        file_log_event="provider_probe",
    )

    combined = _combined_logs(caplog, tmp_path / "logs")
    assert "safe_label" in combined
    assert "client-secret-value" not in combined
    assert "refresh-token-value" not in combined
    assert "sk-fixture-process" not in combined
    assert "api_key" not in combined.lower()
    assert "refresh_token" not in combined.lower()
    assert "client_secret" not in combined.lower()
    assert "raw_payload" not in combined.lower()
    assert "d:\\" not in combined.lower()
    assert "c:\\" not in combined.lower()
    assert "asset.mov" not in combined.lower()


def test_auth_enabled_artifact_read_uses_path_project_when_payload_has_no_project_id(tmp_path, monkeypatch) -> None:
    client = _auth_client(tmp_path, monkeypatch)
    alpha = _register(client, invite_code="alpha-invite", email="alpha@example.com")
    beta = _register(client, invite_code="beta-invite", email="beta@example.com")
    alpha_headers = _auth_headers(alpha["session_token"])
    beta_headers = _auth_headers(beta["session_token"])

    assert client.post(
        "/projects",
        json={"project_id": "alpha-project", "goal": "Alpha owned project"},
        headers=alpha_headers,
    ).status_code == 200

    artifact_path = tmp_path / "runs" / "alpha-project" / "manual-job" / "safe_manifest.json"
    write_json(
        artifact_path,
        {
            "artifact_type": "agentflow_safe_manifest",
            "schema_version": "0.1.0",
            "summary": "safe artifact without project_id in body",
        },
    )
    artifact = RuntimeStore(tmp_path).register_artifact(artifact_path, role="safe_manifest")

    alpha_read = client.get(f"/artifacts/{artifact['artifact_id']}", headers=alpha_headers)
    beta_read = client.get(f"/artifacts/{artifact['artifact_id']}", headers=beta_headers)

    assert alpha_read.status_code == 200
    assert alpha_read.json()["payload"]["summary"] == "safe artifact without project_id in body"
    assert beta_read.status_code == 403


def test_local_artifact_reads_still_work_without_auth_for_path_project_artifacts(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    artifact_path = tmp_path / "runs" / "local-project" / "manual-job" / "safe_manifest.json"
    write_json(
        artifact_path,
        {
            "artifact_type": "agentflow_safe_manifest",
            "schema_version": "0.1.0",
            "summary": "local safe artifact",
        },
    )
    artifact = RuntimeStore(tmp_path).register_artifact(artifact_path, role="safe_manifest")

    response = client.get(f"/artifacts/{artifact['artifact_id']}")

    assert response.status_code == 200
    assert response.json()["payload"]["summary"] == "local safe artifact"


def _combined_logs(caplog, log_dir) -> str:
    records = "\n".join(record.getMessage() for record in caplog.records)
    files = "\n".join(path.read_text(encoding="utf-8") for path in sorted(log_dir.glob("*.log")))
    return records + "\n" + files


def _auth_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AFS_INVITE_CODES", "alpha-invite,beta-invite")
    return TestClient(create_runtime_app(runtime_root=tmp_path))


def _register(client: TestClient, *, invite_code: str, email: str) -> dict:
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "strong-password-123",
            "display_name": email.split("@", 1)[0],
            "invite_code": invite_code,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _auth_headers(session_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {session_token}"}
