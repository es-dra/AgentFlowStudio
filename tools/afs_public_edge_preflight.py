from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.afs_three_end_status import DEFAULT_RUNTIME_HEALTH_URL, collect_remote_runtime_health, sh_quote
from tools.afs_readiness_claims import safe_readiness_projection


DEFAULT_PUBLIC_URL = "https://afstudio.art/studio/"


@dataclass(frozen=True)
class EdgeResponse:
    status_code: int
    headers: dict[str, str]
    error_class: str = ""


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    report = run_public_edge_preflight(
        public_url=args.public_url,
        server=args.server,
        runtime_health_url=args.runtime_health_url,
        check_runtime_health=args.check_runtime_health,
    )
    if args.report:
        path = Path(args.report).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "report": args.report or ""}, ensure_ascii=False))
    return 0 if report["status"] == "ready_for_public_auth" else 2


def run_public_edge_preflight(
    *,
    public_url: str = DEFAULT_PUBLIC_URL,
    server: str = "",
    runtime_health_url: str = DEFAULT_RUNTIME_HEALTH_URL,
    check_runtime_health: bool = False,
    head_fetcher: Callable[[str], EdgeResponse] | None = None,
    runtime_health_fetcher: Callable[[str, str], dict[str, Any]] | None = None,
    local_runtime_health_fetcher: Callable[[str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    fetch_head = head_fetcher or fetch_public_head
    fetch_runtime_health = runtime_health_fetcher or collect_remote_runtime_health
    fetch_local_runtime_health = local_runtime_health_fetcher or fetch_json_url
    edge = fetch_head(public_url)
    runtime_health = {}
    if server.strip():
        try:
            runtime_health = fetch_runtime_health(server, runtime_health_url)
        except RuntimeError:
            runtime_health = {}
    elif check_runtime_health:
        runtime_health = fetch_local_runtime_health(runtime_health_url)
    checks: list[dict[str, Any]] = []
    edge_blocked = _is_basic_auth_block(edge)
    edge_ready = 200 <= edge.status_code < 400 and not edge_blocked
    _add_check(
        checks,
        "public_edge_auth",
        "failed" if edge_blocked else ("passed" if edge_ready else "failed"),
        {
            "public_url": _safe_public_url(public_url),
            "http_status": edge.status_code,
            "edge_basic_auth": edge_blocked,
            "www_authenticate": _safe_www_authenticate(edge.headers.get("www-authenticate", "")),
            "error_class": edge.error_class,
        },
    )
    safe_health = _safe_runtime_health(runtime_health)
    runtime_checked = bool(server.strip() or check_runtime_health)
    runtime_ready = not runtime_checked or safe_health.get("status") == "ready"
    runtime_auth_ready = runtime_checked and safe_health.get("auth_required") is True
    _add_check(
        checks,
        "runtime_health",
        "passed" if runtime_ready else "failed",
        {
            "runtime_checked": runtime_checked,
            "runtime_status": safe_health.get("status", ""),
            "studio_static_status": safe_health.get("studio_static", {}).get("status", ""),
            "auth_required": safe_health.get("auth_required", False),
            "runtime_freshness_verified": bool(safe_health.get("readiness", {}).get("runtime_freshness_verified")),
            "acceptance_ready": bool(safe_health.get("readiness", {}).get("acceptance_ready")),
        },
    )
    _add_check(
        checks,
        "runtime_auth_boundary",
        "passed" if runtime_auth_ready else "failed",
        {
            "runtime_checked": runtime_checked,
            "auth_required": safe_health.get("auth_required", False),
            "public_edge_verified_by_health": bool(safe_health.get("readiness", {}).get("public_edge_verified")),
            "acceptance_ready": bool(safe_health.get("readiness", {}).get("acceptance_ready")),
        },
    )
    if edge_blocked:
        status = "blocked_by_edge_basic_auth"
    elif edge_ready and runtime_ready and runtime_auth_ready:
        status = "ready_for_public_auth"
    elif edge_ready and runtime_ready:
        status = "public_edge_auth_not_ready"
    else:
        status = "needs_attention"
    return {
        "artifact_type": "afs_public_edge_preflight_report",
        "schema_version": "0.1.0",
        "status": status,
        "provider_calls_started": False,
        "writes_company_kb": False,
        "writes_long_term_memory": False,
        "summary": {
            "public_edge_http_status": edge.status_code,
            "edge_basic_auth": edge_blocked,
            "runtime_status": safe_health.get("status", ""),
            "auth_required": safe_health.get("auth_required", False),
            "acceptance_ready": False,
        },
        "checks": checks,
        "runtime_health": safe_health,
        "readiness_boundary": {
            "public_edge_auth_ready": status == "ready_for_public_auth",
            "runtime_freshness_verified": False,
            "acceptance_ready": False,
            "human_acceptance_claim": "not_claimed",
            "product_readiness_claim": "not_claimed",
        },
        "non_claims": [
            "public edge auth preflight only",
            "not runtime loaded-code freshness",
            "not provider smoke",
            "not generated-media QA",
            "not human creative acceptance",
            "not product or business readiness",
            "not public or legal readiness",
        ],
        "recommended_action": _recommended_action(status),
    }


def fetch_public_head(public_url: str) -> EdgeResponse:
    request = urllib.request.Request(public_url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return EdgeResponse(status_code=response.status, headers=_lower_headers(response.headers))
    except urllib.error.HTTPError as exc:
        return EdgeResponse(status_code=exc.code, headers=_lower_headers(exc.headers), error_class=exc.__class__.__name__)
    except urllib.error.URLError as exc:
        return EdgeResponse(status_code=0, headers={}, error_class=exc.__class__.__name__)


def fetch_json_url(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            value = json.loads(response.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return {}
    return value if isinstance(value, dict) else {}


def nginx_basic_auth_disable_commands() -> list[str]:
    return [
        "sudo ./.venv/bin/python -m tools.afs_public_edge_nginx_fix --apply --config /etc/nginx/sites-available/afs-runtime",
        "sudo nginx -t",
        "sudo systemctl reload nginx",
    ]


def sh_public_preflight_command(public_url: str = DEFAULT_PUBLIC_URL) -> str:
    return "curl -I " + sh_quote(public_url)


def _add_check(checks: list[dict[str, Any]], check_id: str, status: str, evidence: dict[str, Any]) -> None:
    checks.append({"check_id": check_id, "status": status, "provider_calls_started": False, "evidence": evidence})


def _is_basic_auth_block(edge: EdgeResponse) -> bool:
    return edge.status_code == 401 and "basic" in str(edge.headers.get("www-authenticate", "")).lower()


def _lower_headers(headers: Any) -> dict[str, str]:
    return {str(key).lower(): str(value) for key, value in dict(headers or {}).items()}


def _safe_www_authenticate(value: str) -> str:
    text = str(value or "")
    return "Basic" if text.lower().startswith("basic") else text[:40]


def _safe_public_url(value: str) -> str:
    text = str(value or "")
    return text.split("?", 1)[0]


def _safe_runtime_health(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        payload = {}
    return {
        "service": str(payload.get("service") or ""),
        "status": str(payload.get("status") or ""),
        "runtime_root_persisted": bool(payload.get("runtime_root_persisted")),
        "auth_required": bool(payload.get("auth_required")),
        "studio_static": _safe_studio_static(payload.get("studio_static")),
        "provider_gates": _safe_provider_gates(payload.get("provider_gates")),
        "readiness": safe_readiness_projection(payload.get("readiness")),
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
def _recommended_action(status: str) -> dict[str, Any]:
    if status != "blocked_by_edge_basic_auth":
        return {"action": "none" if status == "ready_for_public_auth" else "inspect_public_edge", "commands": []}
    return {
        "action": "remove_nginx_basic_auth_or_intentionally_keep_it",
        "commands": nginx_basic_auth_disable_commands(),
        "post_check": sh_public_preflight_command(),
    }


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check whether the public AFS edge is blocked before Runtime auth.")
    parser.add_argument("--public-url", default=DEFAULT_PUBLIC_URL, help="Public Studio URL to check without credentials.")
    parser.add_argument("--server", default="", help="Optional SSH alias for server-side Runtime health.")
    parser.add_argument("--runtime-health-url", default=DEFAULT_RUNTIME_HEALTH_URL, help="Runtime health URL checked from the server.")
    parser.add_argument("--check-runtime-health", action="store_true", help="Check runtime-health-url directly from this machine instead of through SSH.")
    parser.add_argument("--report", default="", help="Optional JSON report output path.")
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
