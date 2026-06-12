from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from tools.project_inventory_core import build_project_inventory, execute_cleanup_plan, write_json
except ModuleNotFoundError:
    from project_inventory_core import build_project_inventory, execute_cleanup_plan, write_json  # type: ignore[no-redef]

__all__ = ["build_project_inventory", "execute_cleanup_plan"]


def write_inventory_outputs(report: dict[str, Any], output_dir: Path, report_doc: Path | None) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "inventory.json", report)
    write_json(output_dir / "cleanup_plan.json", report["cleanup_plan"])
    if report_doc is not None:
        report_doc.parent.mkdir(parents=True, exist_ok=True)
        report_doc.write_text(_markdown_report(report, None), encoding="utf-8")


def write_cleanup_manifest(output_dir: Path, manifest: dict[str, Any], report: dict[str, Any], report_doc: Path | None) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "cleanup_manifest.json", manifest)
    if report_doc is not None:
        report_doc.write_text(_markdown_report(report, manifest), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build AFS project inventory and optionally clean low-risk residue.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--report-doc", default=None)
    parser.add_argument("--execute-cleanup", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_dir = Path(args.output_dir) if args.output_dir else root / "data" / "reports" / "project_inventory" / stamp
    report_doc = Path(args.report_doc) if args.report_doc else None
    report = build_project_inventory(root)
    write_inventory_outputs(report, output_dir, report_doc)
    manifest = None
    if args.execute_cleanup:
        manifest = execute_cleanup_plan(root, report["cleanup_plan"])
        write_cleanup_manifest(output_dir, manifest, report, report_doc)
    print(json.dumps({"status": "ok", "output_dir": str(output_dir), "cleanup_executed": bool(manifest)}, ensure_ascii=False))
    return 0


def _markdown_report(report: dict[str, Any], manifest: dict[str, Any] | None) -> str:
    tracked = report["tracked"]
    ignored = report["ignored"]
    cleanup = report["cleanup_plan"]
    lines = [
        "# AFS Project Inventory",
        "",
        f"- Generated at: `{report['generated_at']}`",
        f"- Git branch: `{report['git']['branch']}`",
        f"- Tracked files: `{tracked['total_files']}`",
        f"- Tracked lines: `{tracked['total_lines']}`",
        f"- Ignored files: `{ignored['total_files']}`",
        f"- Ignored bytes: `{ignored['total_bytes']}`",
        f"- Auto-delete candidates: `{len(cleanup['auto_delete'])}`",
        f"- Oversized tracked files: `{len(tracked['oversized'])}`",
        "",
        "## Cleanup Result",
    ]
    if manifest:
        lines.extend([
            f"- Deleted targets: `{manifest['summary']['deleted_count']}`",
            f"- Skipped targets: `{manifest['summary']['skipped_count']}`",
            f"- Bytes deleted: `{manifest['summary']['bytes_deleted']}`",
        ])
    else:
        lines.append("- Cleanup not executed in this report.")
    lines.extend(["", "## Warnings"])
    lines.extend(f"- `{warning}`" for warning in report.get("warnings", [])[:30])
    lines.extend(["", "## Top Ignored Files"])
    lines.extend(f"- `{item['path']}`: {item['bytes']} bytes; {item['cleanup_reason']}" for item in ignored["top_by_size"][:20])
    lines.extend(["", "## Oversized Tracked Files"])
    lines.extend(f"- `{item['path']}`: {item['lines']} lines" for item in tracked["oversized"][:30])
    lines.extend(["", "## Non-Claims", "- Not human acceptance.", "- Not business validation.", "- Not durable memory."])
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
