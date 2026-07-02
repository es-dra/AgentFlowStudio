from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from tools.afs_readiness_claims import safe_readiness_projection


DEFAULT_HOME_PATH = "/home/afs-ops/AgentFlowStudio"
DEFAULT_OPT_PATH = "/opt/afs/AgentFlowStudio"
DEFAULT_RUNTIME_HEALTH_URL = "http://127.0.0.1:8790/health"
SAFE_GATE_KEYS = {"llm", "image", "video", "vision", "asr", "external_download"}


@dataclass(frozen=True)
class RepoSnapshot:
    label: str
    branch_status: str
    head: str
    origin_head: str
    dirty: bool
    aligned_with_origin: bool


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    report_path = Path(args.report).resolve() if args.report else None
    report = run_three_end_status(
        repo_root=Path(args.repo_root).resolve(),
        server=args.server,
        home_path=args.home_path,
        opt_path=args.opt_path,
        runtime_health_url=args.runtime_health_url,
        fetch=not args.no_fetch,
    )
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "report": str(report_path) if report_path else ""}, ensure_ascii=False))
    return 0 if report["status"] == "aligned" else 2


def run_three_end_status(
    *,
    repo_root: Path,
    server: str = "",
    home_path: str = DEFAULT_HOME_PATH,
    opt_path: str = DEFAULT_OPT_PATH,
    runtime_health_url: str = DEFAULT_RUNTIME_HEALTH_URL,
    fetch: bool = True,
) -> dict[str, Any]:
    local = collect_local_repo_snapshot(repo_root, "local", fetch=fetch)
    server_home = None
    server_opt = None
    runtime_health: dict[str, Any] | None = None
    if server.strip():
        server_home = collect_remote_repo_snapshot(server, home_path, "server_home", fetch=fetch)
        server_opt = collect_remote_repo_snapshot(server, opt_path, "server_opt", fetch=fetch)
        try:
            runtime_health = collect_remote_runtime_health(server, runtime_health_url)
        except RuntimeError:
            runtime_health = {}
    return build_three_end_report(local=local, server_home=server_home, server_opt=server_opt, runtime_health=runtime_health)


def collect_local_repo_snapshot(repo_root: Path, label: str, *, fetch: bool = True) -> RepoSnapshot:
    if fetch:
        _run(["git", "fetch", "origin"], cwd=repo_root)
    return parse_repo_snapshot(
        label,
        _run(["git", "status", "--short", "--branch"], cwd=repo_root),
        _run(["git", "rev-parse", "--short", "HEAD"], cwd=repo_root).strip(),
        _run(["git", "rev-parse", "--short", "origin/master"], cwd=repo_root).strip(),
    )


def collect_remote_repo_snapshot(server: str, repo_path: str, label: str, *, fetch: bool = True) -> RepoSnapshot:
    fetch_cmd = "git fetch origin >/dev/null 2>&1;" if fetch else ""
    script = (
        f"set -e; cd {sh_quote(repo_path)}; {fetch_cmd} "
        "git status --short --branch; "
        "printf '__AFS_SPLIT__\\n'; git rev-parse --short HEAD; "
        "printf '__AFS_SPLIT__\\n'; git rev-parse --short origin/master"
    )
    output = _run(["ssh", server, script])
    parts = [part.strip() for part in output.split("__AFS_SPLIT__")]
    if len(parts) != 3:
        raise RuntimeError(f"could not parse remote git state for {label}")
    return parse_repo_snapshot(label, parts[0], parts[1], parts[2])


def collect_remote_runtime_health(server: str, runtime_health_url: str) -> dict[str, Any]:
    script = f"curl -fsS {sh_quote(runtime_health_url)}"
    output = _run(["ssh", server, script])
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def parse_repo_snapshot(label: str, status_text: str, head: str, origin_head: str) -> RepoSnapshot:
    lines = [line.rstrip() for line in status_text.splitlines() if line.strip()]
    branch_status = lines[0] if lines and lines[0].startswith("## ") else ""
    dirty_lines = [line for line in lines if not line.startswith("## ")]
    normalized_head = str(head or "").strip()
    normalized_origin = str(origin_head or "").strip()
    return RepoSnapshot(
        label=label,
        branch_status=branch_status,
        head=normalized_head,
        origin_head=normalized_origin,
        dirty=bool(dirty_lines),
        aligned_with_origin=bool(normalized_head and normalized_head == normalized_origin and not dirty_lines),
    )


def build_three_end_report(
    *,
    local: RepoSnapshot,
    server_home: RepoSnapshot | None = None,
    server_opt: RepoSnapshot | None = None,
    runtime_health: dict[str, Any] | None = None,
) -> dict[str, Any]:
    snapshots = [item for item in (local, server_home, server_opt) if item is not None]
    aligned_count = sum(1 for item in snapshots if item.aligned_with_origin)
    dirty_count = sum(1 for item in snapshots if item.dirty)
    safe_health = safe_runtime_health(runtime_health or {})
    health_ready = runtime_health is None or safe_health.get("status") == "ready"
    all_aligned = aligned_count == len(snapshots) and health_ready
    runtime_freshness_verified = all_aligned and runtime_health is not None
    return {
        "artifact_type": "afs_three_end_status_report",
        "schema_version": "0.1.0",
        "status": "aligned" if all_aligned else "needs_attention",
        "provider_calls_started": False,
        "writes_company_kb": False,
        "writes_long_term_memory": False,
        "summary": {
            "checked_end_count": len(snapshots),
            "aligned_end_count": aligned_count,
            "dirty_end_count": dirty_count,
            "runtime_status": safe_health.get("status", ""),
        },
        "ends": {item.label: asdict(item) for item in snapshots},
        "runtime_health": safe_health,
        "readiness_claims": {
            "repo_ends_aligned": aligned_count == len(snapshots),
            "runtime_service_ready": health_ready,
            "runtime_freshness_verified": runtime_freshness_verified,
            "acceptance_ready": False,
            "human_creative_acceptance": False,
            "product_readiness": False,
        },
        "non_claims": [
            "three-end alignment only",
            "not provider smoke",
            "not generated-media QA",
            "not human creative acceptance",
            "not product or business readiness",
            "not public or legal readiness",
            "not CompanyOS promotion",
        ],
    }


def safe_runtime_health(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "service": str(payload.get("service") or ""),
        "status": str(payload.get("status") or ""),
        "service_version": str(payload.get("service_version") or ""),
        "schema_version": str(payload.get("schema_version") or ""),
        "runtime_root_persisted": bool(payload.get("runtime_root_persisted")),
        "auth_required": bool(payload.get("auth_required")),
        "studio_static": _safe_studio_static(payload.get("studio_static")),
        "provider_gates": _safe_provider_gates(payload.get("provider_gates")),
        "readiness": safe_readiness_projection(payload.get("readiness")),
    }


def sh_quote(value: str) -> str:
    return "'" + str(value).replace("'", "'\"'\"'") + "'"


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
    return {str(key): bool(val) for key, val in value.items() if str(key) in SAFE_GATE_KEYS}
def _run(args: list[str], *, cwd: Path | None = None) -> str:
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"command failed: {args[0]}")
    return result.stdout


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Report safe AFS local/GitHub/server three-end alignment.")
    parser.add_argument("--repo-root", type=Path, default=Path("."), help="Local repository root.")
    parser.add_argument("--server", default="", help="Optional SSH alias for server checks, for example afs-bwg-ops.")
    parser.add_argument("--home-path", default=DEFAULT_HOME_PATH, help="Server /home checkout path.")
    parser.add_argument("--opt-path", default=DEFAULT_OPT_PATH, help="Server /opt deployment checkout path.")
    parser.add_argument("--runtime-health-url", default=DEFAULT_RUNTIME_HEALTH_URL, help="Runtime health URL checked from the server.")
    parser.add_argument("--no-fetch", action="store_true", help="Skip git fetch before comparing origin/master.")
    parser.add_argument("--report", default="", help="Optional JSON report output path.")
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
