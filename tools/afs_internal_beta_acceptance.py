from __future__ import annotations

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
from tools.afs_internal_beta_acceptance_args import parse_acceptance_args
from tools.afs_internal_beta_acceptance_client import HttpAcceptanceClient
from tools.afs_internal_beta_acceptance_config import AcceptanceConfig
from tools.afs_internal_beta_acceptance_contract import run_acceptance_contract
from tools.afs_internal_beta_acceptance_edge_gate import collect_public_edge_acceptance_gate
from tools.afs_internal_beta_acceptance_errors import AcceptanceConfigurationError
from tools.afs_internal_beta_acceptance_preflight import run_http_preflight as _run_http_preflight
from tools.afs_internal_beta_acceptance_review import render_human_review_markdown
from tools.afs_three_end_status import run_three_end_status


def main() -> int:
    args = parse_acceptance_args()
    report_path = Path(args.report).resolve() if args.report else None
    human_review_path = Path(args.human_review_md).resolve() if args.human_review_md else None
    try:
        if args.preflight_only:
            report = run_http_preflight(
                base_url=args.base_url,
                report_path=report_path,
                include_three_end_status=args.three_end_status,
                three_end_repo_root=Path(args.three_end_repo_root).resolve(),
                three_end_server=args.three_end_server,
                include_public_edge_status=args.public_edge_status,
                public_edge_url=args.public_edge_url,
                public_edge_server=args.public_edge_server or args.three_end_server,
                public_edge_check_runtime_health=args.public_edge_check_runtime_health,
            )
        elif args.three_end_status:
            report = run_three_end_status(repo_root=Path(args.three_end_repo_root).resolve(), server=args.three_end_server)
            _write_json_report(report, report_path)
        elif args.base_url:
            report = run_http_acceptance(
                base_url=args.base_url,
                invite_code=args.invite_code or os.environ.get(args.invite_code_env, ""),
                beta_invite_code=args.beta_invite_code or os.environ.get(args.beta_invite_code_env, ""),
                report_path=report_path,
                human_review_path=human_review_path,
                include_public_edge_status=args.public_edge_status,
                public_edge_url=args.public_edge_url,
                public_edge_server=args.public_edge_server or args.three_end_server,
                public_edge_check_runtime_health=args.public_edge_check_runtime_health,
            )
        elif args.runtime_root:
            report = run_inprocess_acceptance(runtime_root=Path(args.runtime_root).resolve(), report_path=report_path, human_review_path=human_review_path)
        else:
            with tempfile.TemporaryDirectory(prefix="afs-beta-acceptance-") as temp_dir:
                report = run_inprocess_acceptance(runtime_root=Path(temp_dir), report_path=report_path, human_review_path=human_review_path)
    except AcceptanceConfigurationError as exc:
        print(json.dumps({"status": "configuration_error", "error": str(exc), "report": str(report_path) if report_path else ""}, ensure_ascii=False))
        return 2
    print(json.dumps({"status": report["status"], "report": str(report_path) if report_path else ""}, ensure_ascii=False))
    ok_statuses = {"contract_verified_pending_human_acceptance", "ready_for_http_acceptance", "aligned"}
    return 0 if report["status"] in ok_statuses else 2

def run_inprocess_acceptance(*, runtime_root: Path, report_path: Path | None = None, human_review_path: Path | None = None) -> dict[str, Any]:
    from fastapi.testclient import TestClient

    runtime_root = runtime_root.resolve()
    runtime_root.mkdir(parents=True, exist_ok=True)
    with _deterministic_runtime_env():
        client = TestClient(create_runtime_app(runtime_root=runtime_root))
        report = run_acceptance_contract(client)
    _write_json_report(report, report_path)
    _write_human_review_markdown(report, human_review_path)
    return report


def run_http_acceptance(
    *,
    base_url: str,
    invite_code: str,
    beta_invite_code: str = "",
    report_path: Path | None = None,
    human_review_path: Path | None = None,
    run_id: str | None = None,
    include_public_edge_status: bool = False,
    public_edge_url: str = "",
    public_edge_server: str = "",
    public_edge_check_runtime_health: bool = False,
) -> dict[str, Any]:
    if not base_url.strip():
        raise AcceptanceConfigurationError("HTTP acceptance requires a Runtime base URL.")
    public_edge, edge_gate_report = collect_public_edge_acceptance_gate(
        enabled=include_public_edge_status,
        base_url=base_url,
        public_url=public_edge_url,
        server=public_edge_server,
        check_runtime_health=public_edge_check_runtime_health,
    )
    if edge_gate_report is not None:
        _write_json_report(edge_gate_report, report_path)
        return edge_gate_report
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
    if public_edge is not None:
        report["public_edge_status"] = public_edge
    _write_json_report(report, report_path)
    _write_human_review_markdown(report, human_review_path)
    return report


def run_http_preflight(
    *,
    base_url: str,
    report_path: Path | None = None,
    include_three_end_status: bool = False,
    three_end_repo_root: Path | None = None,
    three_end_server: str = "",
    include_public_edge_status: bool = False,
    public_edge_url: str = "",
    public_edge_server: str = "",
    public_edge_check_runtime_health: bool = False,
) -> dict[str, Any]:
    return _run_http_preflight(
        base_url=base_url,
        report_path=report_path,
        include_three_end_status=include_three_end_status,
        three_end_repo_root=three_end_repo_root,
        three_end_server=three_end_server,
        include_public_edge_status=include_public_edge_status,
        public_edge_url=public_edge_url,
        public_edge_server=public_edge_server,
        public_edge_check_runtime_health=public_edge_check_runtime_health,
        http_client_factory=HttpAcceptanceClient,
    )


def _safe_run_id(value: str) -> str:
    safe = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
    return safe[:40] or uuid.uuid4().hex[:10]


def _write_human_review_markdown(report: dict[str, Any], human_review_path: Path | None) -> None:
    if human_review_path is None:
        return
    human_review_path.parent.mkdir(parents=True, exist_ok=True)
    human_review_path.write_text(render_human_review_markdown(report), encoding="utf-8")


def _write_json_report(report: dict[str, Any], report_path: Path | None) -> None:
    if report_path is None:
        return
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


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
