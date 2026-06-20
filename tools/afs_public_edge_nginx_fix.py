from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_NGINX_SITE = Path("/etc/nginx/sites-available/afs-runtime")
TARGET_AUTH_LINES = {
    'auth_basic "AFS Studio Internal Test";',
    "auth_basic_user_file /etc/nginx/.htpasswd_afs;",
}


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    report = build_nginx_basic_auth_fix_report(
        config_path=Path(args.config),
        apply=args.apply,
        backup_path=Path(args.backup) if args.backup else None,
    )
    if args.report:
        report_path = Path(args.report).resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "report": args.report or ""}, ensure_ascii=False))
    return 0 if report["status"] in {"already_ready", "applied"} else 2


def build_nginx_basic_auth_fix_report(
    *,
    config_path: Path = DEFAULT_NGINX_SITE,
    apply: bool = False,
    backup_path: Path | None = None,
) -> dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        return _report("config_missing", path, target_line_count=0, changed=False, backup_path=None)

    original = path.read_text(encoding="utf-8")
    updated, removed = _remove_target_basic_auth_lines(original)
    if not removed:
        return _report("already_ready", path, target_line_count=0, changed=False, backup_path=None)
    if not apply:
        return _report("ready_to_apply", path, target_line_count=len(removed), changed=False, backup_path=None)

    resolved_backup_path = backup_path or path.with_name(path.name + ".bak-" + _timestamp())
    resolved_backup_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_backup_path.write_text(original, encoding="utf-8")
    path.write_text(updated, encoding="utf-8")
    return _report("applied", path, target_line_count=len(removed), changed=True, backup_path=resolved_backup_path)


def _remove_target_basic_auth_lines(text: str) -> tuple[str, list[str]]:
    kept_lines: list[str] = []
    removed: list[str] = []
    for line in text.splitlines(keepends=True):
        if line.strip() in TARGET_AUTH_LINES:
            removed.append(line.strip())
            continue
        kept_lines.append(line)
    return "".join(kept_lines), removed


def _report(
    status: str,
    config_path: Path,
    *,
    target_line_count: int,
    changed: bool,
    backup_path: Path | None,
) -> dict[str, Any]:
    return {
        "artifact_type": "afs_public_edge_nginx_basic_auth_fix_report",
        "schema_version": "0.1.0",
        "status": status,
        "provider_calls_started": False,
        "writes_company_kb": False,
        "writes_long_term_memory": False,
        "summary": {
            "config_path": str(config_path),
            "target_line_count": target_line_count,
            "changed": changed,
            "backup_path": str(backup_path) if backup_path else "",
        },
        "non_claims": [
            "not runtime auth acceptance",
            "not invite-login verification",
            "not provider verification",
            "not human acceptance",
            "not business validation",
        ],
    }


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Safely remove the old AFS public-edge Nginx Basic Auth lines.")
    parser.add_argument("--config", default=str(DEFAULT_NGINX_SITE), help="Nginx site config to inspect or update.")
    parser.add_argument("--apply", action="store_true", help="Write a backup and remove only the known AFS Basic Auth lines.")
    parser.add_argument("--backup", default="", help="Optional explicit backup path.")
    parser.add_argument("--report", default="", help="Optional JSON report output path.")
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
