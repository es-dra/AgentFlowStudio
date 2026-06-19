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


class AcceptanceConfigurationError(ValueError):
    pass


def main() -> int:
    args = _parse_args()
    report_path = Path(args.report).resolve() if args.report else None
    try:
        if args.base_url:
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
    return 0 if report["status"] == "contract_verified_pending_human_acceptance" else 2


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a safe deterministic AFS internal beta acceptance contract.")
    parser.add_argument("--runtime-root", default="", help="Optional local runtime root for deterministic in-process mode.")
    parser.add_argument("--base-url", default="", help="Optional deployed Runtime base URL for HTTP acceptance mode.")
    parser.add_argument("--invite-code", default="", help="Disposable alpha invite code for HTTP mode. Prefer the env form.")
    parser.add_argument("--invite-code-env", default="AFS_INTERNAL_BETA_ACCEPTANCE_INVITE_CODE", help="Environment variable holding the alpha invite code.")
    parser.add_argument("--beta-invite-code", default="", help="Disposable beta invite code for HTTP mode.")
    parser.add_argument("--beta-invite-code-env", default="AFS_INTERNAL_BETA_ACCEPTANCE_INVITE_CODE_BETA", help="Environment variable holding the beta invite code.")
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


def _safe_run_id(value: str) -> str:
    safe = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
    return safe[:40] or uuid.uuid4().hex[:10]


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
