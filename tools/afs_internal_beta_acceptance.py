from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app
from tools.afs_internal_beta_acceptance_contract import run_acceptance_contract


def main() -> int:
    args = _parse_args()
    report_path = Path(args.report).resolve() if args.report else None
    if args.runtime_root:
        report = run_inprocess_acceptance(runtime_root=Path(args.runtime_root).resolve(), report_path=report_path)
    else:
        with tempfile.TemporaryDirectory(prefix="afs-beta-acceptance-") as temp_dir:
            report = run_inprocess_acceptance(runtime_root=Path(temp_dir), report_path=report_path)
    print(json.dumps({"status": report["status"], "report": str(report_path) if report_path else ""}, ensure_ascii=False))
    return 0 if report["status"] == "contract_verified_pending_human_acceptance" else 2


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a safe deterministic AFS internal beta acceptance contract.")
    parser.add_argument("--runtime-root", default="", help="Optional local runtime root for deterministic in-process mode.")
    parser.add_argument("--report", default="", help="Optional JSON report output path.")
    return parser.parse_args()


def run_inprocess_acceptance(*, runtime_root: Path, report_path: Path | None = None) -> dict[str, Any]:
    runtime_root = runtime_root.resolve()
    runtime_root.mkdir(parents=True, exist_ok=True)
    with _deterministic_runtime_env():
        client = TestClient(create_runtime_app(runtime_root=runtime_root))
        report = run_acceptance_contract(client)
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


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
