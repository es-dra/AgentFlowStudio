from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

PROTECTED_LOCAL_CONFIG = {"configs/models.yaml", "configs/providers.local.json"}
PROTECTED_ROOTS = ("data/models/", "data/raw/")
AUTO_DELETE_PARTS = {"__pycache__", ".pytest_cache"}
PYTEST_BASETEMP = "data/processed/pytest-basetemp/"
MEDIA_SUFFIXES = {".mp4", ".mov", ".wav", ".mp3", ".png", ".jpg", ".jpeg", ".webp"}
MODEL_SUFFIXES = {".bin", ".safetensors", ".onnx", ".pt", ".pth"}
GIT_WARNINGS: list[str] = []


def build_project_inventory(root: Path) -> dict[str, Any]:
    root = root.resolve()
    GIT_WARNINGS.clear()
    tracked = _git_lines(root, ["ls-files"])
    ignored = _git_lines(root, ["ls-files", "--others", "--ignored", "--exclude-standard"])
    untracked = _git_lines(root, ["ls-files", "--others", "--exclude-standard"])
    tracked_entries = [_tracked_entry(root, rel) for rel in tracked if (root / rel).is_file()]
    ignored_entries = [_ignored_entry(root, rel.strip('"')) for rel in ignored if (root / rel.strip('"')).is_file()]
    cleanup_plan = _cleanup_plan(root, ignored_entries)
    return {
        "schema_version": "afs_project_inventory_v0_1",
        "artifact_type": "afs_project_inventory_report",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "repo": root.name,
        "git": _git_state(root),
        "tracked": {
            "total_files": len(tracked),
            "total_bytes": sum(entry["bytes"] for entry in tracked_entries),
            "total_lines": sum(entry["lines"] for entry in tracked_entries),
            "by_extension": _group_counts(tracked_entries, "extension"),
            "by_module": _group_counts(tracked_entries, "module"),
            "oversized": [entry for entry in tracked_entries if entry["lines"] > 300],
            "top_by_lines": sorted(tracked_entries, key=lambda item: item["lines"], reverse=True)[:40],
        },
        "ignored": {
            "total_files": len(ignored),
            "total_bytes": sum(entry["bytes"] for entry in ignored_entries),
            "by_root": _group_counts(ignored_entries, "root"),
            "by_extension": _group_counts(ignored_entries, "extension"),
            "top_by_size": sorted(ignored_entries, key=lambda item: item["bytes"], reverse=True)[:50],
            "entries": ignored_entries,
        },
        "untracked_unignored": {"total_files": len(untracked), "paths": untracked[:200], "truncated": len(untracked) > 200},
        "warnings": sorted(set(GIT_WARNINGS)),
        "cleanup_plan": cleanup_plan,
        "recommendations": _recommendations(tracked_entries, ignored_entries, cleanup_plan),
        "non_claims": ["not human acceptance", "not business validation", "not durable memory"],
    }


def execute_cleanup_plan(root: Path, cleanup_plan: dict[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    manifest: dict[str, Any] = {
        "schema_version": "afs_project_cleanup_manifest_v0_1",
        "artifact_type": "afs_project_cleanup_manifest",
        "executed_at": datetime.now().isoformat(timespec="seconds"),
        "deleted": [],
        "skipped": [],
    }
    for target in cleanup_plan.get("auto_delete", []):
        path = _safe_path(root, target["path"])
        before_size = _size_on_disk(path)
        if not path.exists():
            manifest["skipped"].append({**target, "reason": "missing"})
            continue
        try:
            shutil.rmtree(path) if path.is_dir() else path.unlink()
            manifest["deleted"].append({**target, "bytes": before_size})
        except OSError as exc:
            manifest["skipped"].append({**target, "reason": str(exc)})
    _remove_empty_auto_dirs(root)
    manifest["summary"] = {
        "deleted_count": len(manifest["deleted"]),
        "skipped_count": len(manifest["skipped"]),
        "bytes_deleted": sum(item.get("bytes", 0) for item in manifest["deleted"]),
    }
    return manifest


def _tracked_entry(root: Path, rel: str) -> dict[str, Any]:
    path = root / rel
    lines = _read_text(path).splitlines()
    code, comments, blanks = _line_breakdown(lines, path.suffix.lower())
    return {
        "path": rel,
        "root": rel.split("/", 1)[0],
        "module": _module(rel),
        "extension": path.suffix.lower() or "<noext>",
        "bytes": path.stat().st_size,
        "lines": len(lines),
        "code_lines": code,
        "comment_lines": comments,
        "blank_lines": blanks,
    }


def _ignored_entry(root: Path, rel: str) -> dict[str, Any]:
    path = root / rel
    action, reason = _cleanup_classification(rel, path)
    return {
        "path": rel,
        "root": rel.split("/", 1)[0],
        "extension": path.suffix.lower() or "<noext>",
        "bytes": path.stat().st_size,
        "modified_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
        "cleanup_action": action,
        "cleanup_reason": reason,
    }


def _cleanup_classification(rel: str, path: Path) -> tuple[str, str]:
    parts = set(Path(rel).parts)
    suffix = path.suffix.lower()
    if rel.startswith(".venv/"):
        return "report_only", "local virtualenv environment"
    if rel in PROTECTED_LOCAL_CONFIG or rel.startswith("configs/") and ".local." in Path(rel).name:
        return "report_only", "protected local configuration"
    if rel.startswith(PROTECTED_ROOTS) or suffix in MODEL_SUFFIXES:
        return "report_only", "protected local model or original source"
    if rel.startswith(PYTEST_BASETEMP):
        return "auto_delete", "recreatable pytest basetemp cache"
    if parts & AUTO_DELETE_PARTS or suffix in {".pyc", ".pyo"}:
        return "auto_delete", "recreatable interpreter/test cache"
    if suffix in MEDIA_SUFFIXES:
        return "report_only", "media or evidence artifact requires human retention decision"
    return "report_only", "ignored artifact requires retention review"


def _cleanup_plan(root: Path, ignored_entries: list[dict[str, Any]]) -> dict[str, Any]:
    auto = [{"path": item["path"], "target_type": "file", "rule_id": item["cleanup_reason"]} for item in ignored_entries if item["cleanup_action"] == "auto_delete"]
    auto.extend(_known_auto_dirs(root))
    auto.extend(_empty_ignored_sop_dirs(root))
    report_only = [item for item in ignored_entries if item["cleanup_action"] == "report_only"]
    return {
        "auto_delete": auto,
        "report_only": [{"path": item["path"], "bytes": item["bytes"], "reason": item["cleanup_reason"]} for item in report_only[:500]],
        "report_only_truncated": len(report_only) > 500,
    }


def _known_auto_dirs(root: Path) -> list[dict[str, str]]:
    targets = []
    for rel in (".pytest_cache", "data/processed/pytest-basetemp"):
        if (root / rel).exists():
            targets.append({"path": rel, "target_type": "dir", "rule_id": "known recreatable cache directory"})
    return targets


def _empty_ignored_sop_dirs(root: Path) -> list[dict[str, str]]:
    studio = root / "agentflow_studio"
    if not studio.exists():
        return []
    return [
        {"path": path.relative_to(root).as_posix(), "target_type": "dir", "rule_id": "empty ignored SOP directory"}
        for path in studio.glob("*_sop")
        if path.is_dir() and not any(path.rglob("*"))
    ]


def _remove_empty_auto_dirs(root: Path) -> None:
    for directory in sorted(root.rglob("__pycache__"), key=lambda item: len(item.parts), reverse=True):
        if directory.is_dir() and not any(directory.iterdir()):
            directory.rmdir()
    for rel in (".pytest_cache", "data/processed/pytest-basetemp"):
        path = root / rel
        if path.exists() and path.is_dir():
            try:
                shutil.rmtree(path)
            except OSError:
                pass


def _recommendations(tracked: list[dict[str, Any]], ignored: list[dict[str, Any]], cleanup_plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "p0_before_provider_gateway": [
            "Review oversized Runtime/Studio files before expanding provider routes.",
            "Keep provider local config and model weights report-only.",
        ],
        "auto_cleanup_count": len(cleanup_plan["auto_delete"]),
        "ignored_report_only_bytes": sum(item["bytes"] for item in ignored if item["cleanup_action"] == "report_only"),
        "tracked_oversized_count": sum(1 for item in tracked if item["lines"] > 300),
    }


def _group_counts(entries: list[dict[str, Any]], key: str) -> dict[str, dict[str, int]]:
    grouped: dict[str, dict[str, int]] = {}
    for entry in entries:
        bucket = grouped.setdefault(entry[key], {"files": 0, "bytes": 0, "lines": 0})
        bucket["files"] += 1
        bucket["bytes"] += entry.get("bytes", 0)
        bucket["lines"] += entry.get("lines", 0)
    return dict(sorted(grouped.items(), key=lambda item: item[1]["bytes"], reverse=True))


def _git_state(root: Path) -> dict[str, str]:
    return {
        "branch": _git_text(root, ["branch", "--show-current"]),
        "head": _git_text_optional(root, ["rev-parse", "--short", "HEAD"], "<no-head>"),
        "status_short": _git_text(root, ["status", "--short", "--branch"]),
    }


def _git_lines(root: Path, args: list[str]) -> list[str]:
    return [line for line in _git_text(root, args).splitlines() if line]


def _git_text(root: Path, args: list[str]) -> str:
    result = subprocess.run(["git", *args], cwd=root, text=True, encoding="utf-8", errors="ignore", capture_output=True)
    if result.stderr.strip():
        GIT_WARNINGS.extend(line for line in result.stderr.splitlines() if line.strip())
    if result.returncode:
        raise subprocess.CalledProcessError(result.returncode, result.args, output=result.stdout, stderr=result.stderr)
    return result.stdout.strip()


def _git_text_optional(root: Path, args: list[str], fallback: str) -> str:
    try:
        return _git_text(root, args)
    except subprocess.CalledProcessError:
        return fallback


def _line_breakdown(lines: list[str], suffix: str) -> tuple[int, int, int]:
    blanks = comments = 0
    markers = ("#",) if suffix == ".py" else ("//", "/*", "*", "<!--")
    for line in lines:
        stripped = line.strip()
        if not stripped:
            blanks += 1
        elif stripped.startswith(markers):
            comments += 1
    return len(lines) - blanks - comments, comments, blanks


def _module(rel: str) -> str:
    parts = rel.split("/")
    if len(parts) >= 2 and parts[0] in {"apps", "agentflow", "agentflow_studio", "tests"}:
        return "/".join(parts[:2])
    return parts[0]


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _size_on_disk(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(child.stat().st_size for child in path.rglob("*") if child.is_file())


def _safe_path(root: Path, rel: str) -> Path:
    path = (root / rel).resolve()
    if path != root and root not in path.parents:
        raise ValueError(f"cleanup target escapes repository root: {rel}")
    return path


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
