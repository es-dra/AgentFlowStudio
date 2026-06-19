from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.runtime_service import create_runtime_app
from tools.afs_internal_beta_acceptance_client import HttpAcceptanceClient
from tools.afs_internal_beta_acceptance_config import AcceptanceConfig
from tools.afs_internal_beta_acceptance_contract import run_acceptance_contract
from tools.afs_internal_beta_preflight_three_end import collect_three_end_status, safe_three_end_status


class AcceptanceConfigurationError(ValueError):
    pass


def main() -> int:
    args = _parse_args()
    report_path = Path(args.report).resolve() if args.report else None
    try:
        if args.preflight_only:
            report = run_http_preflight(
                base_url=args.base_url,
                report_path=report_path,
                include_three_end_status=args.three_end_status,
                three_end_repo_root=Path(args.three_end_repo_root).resolve(),
                three_end_server=args.three_end_server,
            )
        elif args.base_url:
            report = run_http_acceptance(
                base_url=args.base_url,
                invite_code=args.invite_code or os.environ.get(args.invite_code_env, ""),
                beta_invite_code=args.beta_invite_code or os.environ.get(args.beta_invite_code_env, ""),
                report_path=report_path,
            )
        elif args.runtime_root:
            report = run_inprocess_acceptance(runtime_root=Path(args.runtime_root).resolve(), report_path=report_path)
        else:
            with tempfile.TemporaryDirectory(prefix="afs-beta-acceptance-") as temp_dir:
                report = run_inprocess_acceptance(runtime_root=Path(temp_dir), report_path=report_path)
    except AcceptanceConfigurationError as exc:
        print(json.dumps({"status": "configuration_error", "error": str(exc), "report": str(report_path) if report_path else ""}, ensure_ascii=False))
        return 2
    print(json.dumps({"status": report["status"], "report": str(report_path) if report_path else ""}, ensure_ascii=False))
    ok_statuses = {"contract_verified_pending_human_acceptance", "ready_for_http_acceptance"}
    return 0 if report["status"] in ok_statuses else 2


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a safe deterministic AFS internal beta acceptance contract.")
    parser.add_argument("--runtime-root", default="", help="Optional local runtime root for deterministic in-process mode.")
    parser.add_argument("--base-url", default="", help="Optional deployed Runtime base URL for HTTP acceptance mode.")
    parser.add_argument("--invite-code", default="", help="Disposable alpha invite code for HTTP mode. Prefer the env form.")
    parser.add_argument("--invite-code-env", default="AFS_INTERNAL_BETA_ACCEPTANCE_INVITE_CODE", help="Environment variable holding the alpha invite code.")
    parser.add_argument("--beta-invite-code", default="", help="Disposable beta invite code for HTTP mode.")
    parser.add_argument("--beta-invite-code-env", default="AFS_INTERNAL_BETA_ACCEPTANCE_INVITE_CODE_BETA", help="Environment variable holding the beta invite code.")
    parser.add_argument("--preflight-only", action="store_true", help="Only inspect deployed Runtime readiness; no invite codes or provider calls.")
    parser.add_argument("--three-end-status", action="store_true", help="Include safe local/GitHub/server drift status in preflight mode.")
    parser.add_argument("--three-end-repo-root", default=".", help="Local repository root for optional three-end preflight status.")
    parser.add_argument("--three-end-server", default="", help="Optional SSH alias for server-side three-end status.")
    parser.add_argument("--report", default="", help="Optional JSON report output path.")
    return parser.parse_args()


def run_inprocess_acceptance(*, runtime_root: Path, report_path: Path | None = None) -> dict[str, Any]:
    from fastapi.testclient import TestClient

    runtime_root = runtime_root.resolve()
    runtime_root.mkdir(parents=True, exist_ok=True)
    with _deterministic_runtime_env():
        client = TestClient(create_runtime_app(runtime_root=runtime_root))
        report = run_acceptance_contract(client)
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def run_http_acceptance(
    *,
    base_url: str,
    invite_code: str,
    beta_invite_code: str = "",
    report_path: Path | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    if not base_url.strip():
        raise AcceptanceConfigurationError("HTTP acceptance requires a Runtime base URL.")
    if not invite_code.strip():
        raise AcceptanceConfigurationError("HTTP acceptance requires an invite code via --invite-code or AFS_INTERNAL_BETA_ACCEPTANCE_INVITE_CODE.")
    if not beta_invite_code.strip():
        raise AcceptanceConfigurationError("HTTP acceptance requires a beta invite code via --beta-invite-code or AFS_INTERNAL_BETA_ACCEPTANCE_INVITE_CODE_BETA.")
    active_run_id = _safe_run_id(run_id or uuid.uuid4().hex[:10])
    client = HttpAcceptanceClient(base_url.strip())
    try:
        report = run_acceptance_contract(
            client,
            config=AcceptanceConfig.deployed_http(
                alpha_invite_code=invite_code.strip(),
                beta_invite_code=beta_invite_code.strip(),
                run_id=active_run_id,
            ),
            mode="deployed_http_runtime",
        )
    finally:
        close = getattr(client, "close", None)
        if callable(close):
            close()
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def run_http_preflight(
    *,
    base_url: str,
    report_path: Path | None = None,
    include_three_end_status: bool = False,
    three_end_repo_root: Path | None = None,
    three_end_server: str = "",
) -> dict[str, Any]:
    if not base_url.strip():
        raise AcceptanceConfigurationError("HTTP preflight requires a Runtime base URL.")
    client = HttpAcceptanceClient(base_url.strip())
    try:
        three_end_status = None
        if include_three_end_status:
            three_end_status = collect_three_end_status(
                repo_root=three_end_repo_root or Path("."),
                server=three_end_server,
            )
        report = _build_http_preflight_report(client, three_end_status=three_end_status)
    finally:
        close = getattr(client, "close", None)
        if callable(close):
            close()
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def _safe_run_id(value: str) -> str:
    safe = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
    return safe[:40] or uuid.uuid4().hex[:10]


def _build_http_preflight_report(client, *, three_end_status: dict[str, Any] | None = None) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    health_status = 0
    health: dict[str, Any] = {}
    auth_status = 0
    auth_payload: dict[str, Any] = {}
    try:
        health_response = client.get("/health")
        health_status = int(getattr(health_response, "status_code", 0))
        health = _safe_json_object(health_response)
    except Exception as exc:  # pragma: no cover - exercised by deployed smoke more than unit tests.
        _add_preflight_check(checks, "runtime_health", "failed", {"http_status": 0, "error_class": exc.__class__.__name__})
    else:
        _add_preflight_check(
            checks,
            "runtime_health",
            "passed" if health_status == 200 and health.get("status") == "ready" else "failed",
            {
                "http_status": health_status,
                "runtime_status": health.get("status"),
                "runtime_root_persisted": bool(health.get("runtime_root_persisted")),
            },
        )
    try:
        auth_response = client.get("/auth/status")
        auth_status = int(getattr(auth_response, "status_code", 0))
        auth_payload = _safe_json_object(auth_response)
    except Exception as exc:  # pragma: no cover - exercised by deployed smoke more than unit tests.
        _add_preflight_check(checks, "auth_surface", "failed", {"http_status": 0, "error_class": exc.__class__.__name__})
    else:
        _add_preflight_check(
            checks,
            "auth_surface",
            "passed" if auth_status == 200 and auth_payload.get("auth_required") is True else "failed",
            {
                "http_status": auth_status,
                "auth_required": auth_payload.get("auth_required"),
                "invite_registration_available": auth_payload.get("invite_registration_available"),
            },
        )
    studio_static = health.get("studio_static") if isinstance(health, dict) else {}
    _add_preflight_check(
        checks,
        "studio_static",
        "passed" if isinstance(studio_static, dict) and studio_static.get("status") == "ready" else "failed",
        _safe_studio_static(studio_static),
    )
    provider_gates = _safe_provider_gates(health.get("provider_gates") if isinstance(health, dict) else {})
    _add_preflight_check(
        checks,
        "provider_gate_projection",
        "passed" if "video" in provider_gates else "failed",
        {"provider_gates": provider_gates, "provider_calls_started": False},
    )
    safe_three_end = safe_three_end_status(three_end_status) if three_end_status is not None else None
    if safe_three_end is not None:
        summary = safe_three_end.get("summary", {})
        _add_preflight_check(
            checks,
            "three_end_status",
            "passed" if safe_three_end.get("status") == "aligned" else "failed",
            {
                "status": str(safe_three_end.get("status") or ""),
                "checked_end_count": int(summary.get("checked_end_count") or 0),
                "aligned_end_count": int(summary.get("aligned_end_count") or 0),
                "dirty_end_count": int(summary.get("dirty_end_count") or 0),
                "runtime_status": str(summary.get("runtime_status") or ""),
            },
        )
    failed_count = sum(1 for item in checks if item["status"] == "failed")
    passed_count = sum(1 for item in checks if item["status"] == "passed")
    report = {
        "artifact_type": "afs_internal_beta_acceptance_preflight_report",
        "schema_version": "0.1.0",
        "mode": "deployed_http_preflight",
        "status": "ready_for_http_acceptance" if failed_count == 0 else "needs_attention",
        "provider_calls_started": False,
        "requires_invite_codes": bool(auth_payload.get("invite_registration_available") or health.get("auth_required")),
        "human_acceptance_claim": "not_claimed",
        "business_validation_claim": "not_claimed",
        "writes_company_kb": False,
        "writes_long_term_memory": False,
        "summary": {"passed_check_count": passed_count, "failed_check_count": failed_count},
        "safe_health": _safe_health(health),
        "checks": checks,
    }
    if safe_three_end is not None:
        report["three_end_status"] = safe_three_end
    return report


def _add_preflight_check(checks: list[dict[str, Any]], check_id: str, status: str, evidence: dict[str, Any]) -> None:
    checks.append({"check_id": check_id, "status": status, "provider_calls_started": False, "evidence": evidence})


def _safe_json_object(response) -> dict[str, Any]:
    try:
        value = response.json()
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def _safe_health(health: dict[str, Any]) -> dict[str, Any]:
    return {
        "service": str(health.get("service") or ""),
        "status": str(health.get("status") or ""),
        "service_version": str(health.get("service_version") or ""),
        "schema_version": str(health.get("schema_version") or ""),
        "runtime_root_persisted": bool(health.get("runtime_root_persisted")),
        "auth_required": bool(health.get("auth_required")),
        "studio_static": _safe_studio_static(health.get("studio_static")),
        "provider_gates": _safe_provider_gates(health.get("provider_gates")),
    }


def _safe_studio_static(value: Any) -> dict[str, bool | str]:
    if not isinstance(value, dict):
        value = {}
    return {
        "mounted": bool(value.get("mounted")),
        "root_exists": bool(value.get("root_exists")),
        "index_exists": bool(value.get("index_exists")),
        "entry_js_exists": bool(value.get("entry_js_exists")),
        "status": str(value.get("status") or "missing"),
    }


def _safe_provider_gates(value: Any) -> dict[str, bool]:
    if not isinstance(value, dict):
        return {}
    allowed = {"llm", "image", "video", "vision", "asr", "external_download"}
    return {str(key): bool(val) for key, val in value.items() if str(key) in allowed}


@contextmanager
def _deterministic_runtime_env() -> Iterator[None]:
    env = {
        "AFS_AUTH_ENABLED": "true",
        "AFS_INVITE_CODES": "alpha-invite,beta-invite",
        "AFS_AUTH_SESSION_TTL_HOURS": "168",
        "AFS_ALLOW_REMOTE_LLM": "false",
        "AFS_ALLOW_REMOTE_IMAGE": "false",
        "AFS_ALLOW_REMOTE_VISION": "false",
        "AFS_ALLOW_REMOTE_VIDEO": "false",
        "AFS_ALLOW_REMOTE_ASR": "false",
        "AFS_ALLOW_EXTERNAL_DOWNLOAD": "false",
    }
    previous = {key: os.environ.get(key) for key in env}
    os.environ.update(env)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


if __name__ == "__main__":
    raise SystemExit(main())
