from __future__ import annotations

import base64
from typing import Any

from tools.afs_internal_beta_acceptance_config import AcceptanceConfig


PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def health_step(client, steps: list[dict[str, Any]]) -> dict[str, Any]:
    response = client.get("/health")
    payload = response.json()
    add_step(
        steps,
        "runtime_health",
        "passed" if response.status_code == 200 and payload.get("status") == "ready" else "failed",
        {
            "http_status": response.status_code,
            "runtime_status": payload.get("status"),
            "auth_required": payload.get("auth_required"),
            "runtime_root_persisted": payload.get("runtime_root_persisted"),
            "provider_gates": _safe_provider_gates(payload.get("provider_gates")),
        },
    )
    return payload


def auth_registration_step(client, steps: list[dict[str, Any]], config: AcceptanceConfig) -> tuple[dict[str, str], dict[str, str]]:
    status = client.get("/auth/status").json()
    alpha = _register(client, config.alpha_invite_code, config.alpha_email, config.password)
    beta = _register(client, config.beta_invite_code, config.beta_email, config.password)
    alpha_headers = auth_headers(alpha["session_token"])
    beta_headers = auth_headers(beta["session_token"])
    me = client.get("/auth/me", headers=alpha_headers)
    add_step(
        steps,
        "auth_registration",
        "passed" if status.get("auth_required") is True and me.status_code == 200 else "failed",
        {
            "auth_required": status.get("auth_required"),
            "invite_registration_available": status.get("invite_registration_available"),
            "registered_user_count": 2,
            "me_http_status": me.status_code,
        },
    )
    return alpha_headers, beta_headers


def project_isolation_step(
    client,
    steps: list[dict[str, Any]],
    alpha_headers: dict[str, str],
    beta_headers: dict[str, str],
    config: AcceptanceConfig,
) -> str:
    created = client.post(
        "/projects",
        json={"project_id": config.project_id, "goal": "Internal beta acceptance deterministic project"},
        headers=alpha_headers,
    )
    alpha_projects = client.get("/projects", headers=alpha_headers)
    beta_projects = client.get("/projects", headers=beta_headers)
    alpha_manifest = client.get(f"/projects/{config.project_id}/manifest", headers=alpha_headers)
    beta_manifest = client.get(f"/projects/{config.project_id}/manifest", headers=beta_headers)
    add_step(
        steps,
        "project_owner_isolation",
        "passed" if _project_isolation_ok(created, alpha_projects, beta_projects, alpha_manifest, beta_manifest) else "failed",
        {
            "create_http_status": created.status_code,
            "alpha_project_count": len(alpha_projects.json().get("projects") or []),
            "beta_project_count": len(beta_projects.json().get("projects") or []),
            "beta_manifest_http_status": beta_manifest.status_code,
        },
    )
    return str(created.json()["artifact"]["artifact_id"])


def studio_state_step(
    client,
    steps: list[dict[str, Any]],
    alpha_headers: dict[str, str],
    beta_headers: dict[str, str],
    config: AcceptanceConfig,
) -> None:
    state = {
        "meta": {"projectName": "Beta Acceptance Project", "canvasName": "Acceptance Board"},
        "nodes": {"image_1": {"type": "image", "title": "First frame"}},
        "order": ["image_1"],
    }
    write_response = client.put(f"/projects/{config.project_id}/studio-state", json={"state": state}, headers=alpha_headers)
    alpha_state = client.get(f"/projects/{config.project_id}/studio-state", headers=alpha_headers)
    beta_state = client.get(f"/projects/{config.project_id}/studio-state", headers=beta_headers)
    add_step(
        steps,
        "studio_state_isolation",
        "passed" if write_response.status_code == 200 and alpha_state.status_code == 200 and beta_state.status_code == 403 else "failed",
        {"write_http_status": write_response.status_code, "alpha_read_http_status": alpha_state.status_code, "beta_read_http_status": beta_state.status_code},
    )


def image_asset_step(
    client,
    steps: list[dict[str, Any]],
    alpha_headers: dict[str, str],
    beta_headers: dict[str, str],
    config: AcceptanceConfig,
) -> tuple[str, str]:
    upload = client.post(
        f"/projects/{config.project_id}/image-assets",
        json={
            "node_id": "image_1",
            "filename": "first-frame.png",
            "mime_type": "image/png",
            "data_base64": base64.b64encode(PNG_BYTES).decode("ascii"),
            "role": "reference_image",
            "generated_at": config.generated_at,
        },
        headers=alpha_headers,
    )
    payload = upload.json()
    asset_id = str(payload["asset"]["asset_id"])
    artifact_id = str(payload["artifact"]["artifact_id"])
    alpha_list = client.get(f"/projects/{config.project_id}/image-assets", headers=alpha_headers)
    beta_list = client.get(f"/projects/{config.project_id}/image-assets", headers=beta_headers)
    alpha_preview = client.get(f"/projects/{config.project_id}/image-assets/{asset_id}/preview", headers=alpha_headers)
    beta_preview = client.get(f"/projects/{config.project_id}/image-assets/{asset_id}/preview", headers=beta_headers)
    add_step(steps, "image_asset_isolation", "passed" if _image_asset_ok(upload, alpha_list, beta_list, alpha_preview, beta_preview, payload) else "failed", {
        "upload_http_status": upload.status_code,
        "alpha_asset_count": len(alpha_list.json().get("assets") or []),
        "beta_list_http_status": beta_list.status_code,
        "beta_preview_http_status": beta_preview.status_code,
        "media_bytes_returned": payload.get("media_bytes_returned"),
    })
    return asset_id, artifact_id


def artifact_scope_step(
    client,
    steps: list[dict[str, Any]],
    alpha_headers: dict[str, str],
    beta_headers: dict[str, str],
    artifact_ids: list[str],
) -> None:
    alpha_statuses = [client.get(f"/artifacts/{artifact_id}", headers=alpha_headers).status_code for artifact_id in artifact_ids]
    beta_statuses = [client.get(f"/artifacts/{artifact_id}", headers=beta_headers).status_code for artifact_id in artifact_ids]
    add_step(
        steps,
        "artifact_scope",
        "passed" if alpha_statuses == [200, 200, 200] and beta_statuses == [403, 403, 403] else "failed",
        {"alpha_statuses": alpha_statuses, "beta_statuses": beta_statuses, "artifact_count": len(artifact_ids)},
    )


def auth_headers(session_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {session_token}"}


def add_step(
    steps: list[dict[str, Any]],
    step_id: str,
    status: str,
    evidence: dict[str, Any],
    *,
    provider_calls_started: bool = False,
) -> None:
    steps.append({"step_id": step_id, "status": status, "provider_calls_started": provider_calls_started, "evidence": evidence})


def _register(client, invite_code: str, email: str, password: str) -> dict[str, Any]:
    response = client.post(
        "/auth/register",
        json={"email": email, "password": password, "display_name": email.split("@", 1)[0], "invite_code": invite_code},
    )
    if response.status_code != 200:
        raise RuntimeError("acceptance auth registration failed")
    return response.json()


def _safe_provider_gates(value: Any) -> dict[str, bool]:
    if not isinstance(value, dict):
        return {}
    return {str(key): bool(val) for key, val in value.items() if str(key) in {"llm", "image", "vision", "video", "asr", "external_download"}}


def _project_isolation_ok(created, alpha_projects, beta_projects, alpha_manifest, beta_manifest) -> bool:
    return all(response.status_code == 200 for response in (created, alpha_projects, beta_projects, alpha_manifest)) and beta_manifest.status_code == 403


def _image_asset_ok(upload, alpha_list, beta_list, alpha_preview, beta_preview, payload: dict[str, Any]) -> bool:
    return (
        upload.status_code == 200
        and alpha_list.status_code == 200
        and beta_list.status_code == 403
        and alpha_preview.status_code == 200
        and beta_preview.status_code == 403
        and payload.get("media_bytes_returned") is False
    )
