from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class StackEntry:
    label: str
    base_ref: str
    head_ref: str
    expected_base_sha: str = ""
    expected_head_sha: str = ""


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    entries = _load_entries(args)
    report = collect_pr_stack_drift_guard(
        repo_root=Path(args.repo_root).resolve(),
        entries=entries,
        fetch=not args.no_fetch,
    )
    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "blocker_count": len(report["blockers"])}, ensure_ascii=False))
    return 0 if report["status"] == "stack_ready_for_review" else 2


def collect_pr_stack_drift_guard(
    *,
    repo_root: Path,
    entries: list[StackEntry],
    fetch: bool = True,
) -> dict[str, Any]:
    fetch_error = ""
    if fetch:
        fetch_error = _git_optional(repo_root, ["fetch", "origin", "--prune"], include_stderr=True).strip()

    resolved: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        item = _resolve_entry(repo_root, entry)
        if index > 0 and item["head_sha"]:
            item["previous_head_is_ancestor_of_head"] = _is_ancestor(repo_root, entries[index - 1].head_ref, entry.head_ref)
        resolved.append(item)
    blockers = build_stack_drift_blockers(resolved, fetch_error=fetch_error)
    return {
        "artifact_type": "afs_pr_stack_drift_guard",
        "schema_version": "0.1.0",
        "status": "stack_ready_for_review" if not blockers else "needs_attention",
        "entry_count": len(entries),
        "entries": resolved,
        "blockers": blockers,
        "recommended_next_action": _next_action(blockers),
        "provider_calls_started": False,
        "server_sync_performed": False,
        "deploy_performed": False,
        "secrets_printed": False,
        "non_claims": [
            "not a merge",
            "not deploy verification",
            "not runtime freshness verification",
            "not provider smoke",
            "not human acceptance",
            "not business validation",
        ],
    }


def build_stack_drift_blockers(entries: list[dict[str, Any]], *, fetch_error: str = "") -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    if fetch_error:
        blockers.append({"block_id": "fetch_failed", "stderr": fetch_error})

    previous: dict[str, Any] | None = None
    for entry in entries:
        label = entry["label"]
        base_sha = entry["base_sha"]
        head_sha = entry["head_sha"]
        if not base_sha:
            blockers.append({"block_id": "base_ref_unresolved", "label": label, "base_ref": entry["base_ref"]})
        if not head_sha:
            blockers.append({"block_id": "head_ref_unresolved", "label": label, "head_ref": entry["head_ref"]})
        if base_sha and head_sha and not entry["base_is_ancestor_of_head"]:
            blockers.append(
                {
                    "block_id": "base_not_ancestor_of_head",
                    "label": label,
                    "base_ref": entry["base_ref"],
                    "head_ref": entry["head_ref"],
                    "base_sha": _short(base_sha),
                    "head_sha": _short(head_sha),
                }
            )
        if entry["expected_base_sha"] and base_sha and not _same_sha(entry["expected_base_sha"], base_sha):
            blockers.append(
                {
                    "block_id": "base_ref_drifted",
                    "label": label,
                    "base_ref": entry["base_ref"],
                    "expected": _short(entry["expected_base_sha"]),
                    "actual": _short(base_sha),
                }
            )
        if entry["expected_head_sha"] and head_sha and not _same_sha(entry["expected_head_sha"], head_sha):
            blockers.append(
                {
                    "block_id": "head_ref_drifted",
                    "label": label,
                    "head_ref": entry["head_ref"],
                    "expected": _short(entry["expected_head_sha"]),
                    "actual": _short(head_sha),
                }
            )
        if previous is not None:
            if entry["base_ref"] != previous["head_ref"]:
                blockers.append(
                    {
                        "block_id": "stack_base_ref_not_previous_head_ref",
                        "label": label,
                        "base_ref": entry["base_ref"],
                        "previous_label": previous["label"],
                        "previous_head_ref": previous["head_ref"],
                    }
                )
            if previous["head_sha"] and head_sha and not entry["previous_head_is_ancestor_of_head"]:
                blockers.append(
                    {
                        "block_id": "previous_head_not_ancestor_of_head",
                        "label": label,
                        "previous_label": previous["label"],
                        "previous_head_sha": _short(previous["head_sha"]),
                        "head_sha": _short(head_sha),
                    }
                )
        previous = entry
    return blockers


def _resolve_entry(repo_root: Path, entry: StackEntry) -> dict[str, Any]:
    base_sha = _rev_parse(repo_root, entry.base_ref)
    head_sha = _rev_parse(repo_root, entry.head_ref)
    return {
        "label": entry.label,
        "base_ref": entry.base_ref,
        "head_ref": entry.head_ref,
        "base_sha": base_sha,
        "head_sha": head_sha,
        "expected_base_sha": entry.expected_base_sha,
        "expected_head_sha": entry.expected_head_sha,
        "base_is_ancestor_of_head": _is_ancestor(repo_root, entry.base_ref, entry.head_ref) if base_sha and head_sha else False,
        "previous_head_is_ancestor_of_head": False,
        "commit_count_since_base": _commit_count(repo_root, entry.base_ref, entry.head_ref) if base_sha and head_sha else 0,
    }


def _commit_count(repo_root: Path, base_ref: str, head_ref: str) -> int:
    output = _git_optional(repo_root, ["rev-list", "--count", f"{base_ref}..{head_ref}"]).strip()
    try:
        return int(output)
    except ValueError:
        return 0


def _rev_parse(repo_root: Path, ref: str) -> str:
    return _git_optional(repo_root, ["rev-parse", ref]).strip()


def _is_ancestor(repo_root: Path, ancestor: str, descendant: str) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _git_optional(repo_root: Path, args: list[str], *, include_stderr: bool = False) -> str:
    result = subprocess.run(["git", *args], cwd=repo_root, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return result.stderr if include_stderr else ""
    return result.stdout


def _load_entries(args: argparse.Namespace) -> list[StackEntry]:
    entries: list[StackEntry] = []
    if args.spec:
        payload = json.loads(Path(args.spec).read_text(encoding="utf-8"))
        for item in payload.get("entries", []):
            entries.append(_entry_from_mapping(item))
    for value in args.entry:
        entries.append(_entry_from_cli(value))
    if not entries:
        raise SystemExit("Provide at least one --entry or --spec.")
    return entries


def _entry_from_mapping(item: dict[str, Any]) -> StackEntry:
    return StackEntry(
        label=str(item.get("label") or item.get("pr") or item.get("head_ref") or "").strip(),
        base_ref=str(item.get("base_ref") or "").strip(),
        head_ref=str(item.get("head_ref") or "").strip(),
        expected_base_sha=str(item.get("expected_base_sha") or "").strip(),
        expected_head_sha=str(item.get("expected_head_sha") or "").strip(),
    )


def _entry_from_cli(value: str) -> StackEntry:
    parts = [part.strip() for part in value.split(",")]
    if len(parts) < 3:
        raise SystemExit("--entry must be label,base_ref,head_ref[,expected_base_sha[,expected_head_sha]]")
    return StackEntry(
        label=parts[0],
        base_ref=parts[1],
        head_ref=parts[2],
        expected_base_sha=parts[3] if len(parts) >= 4 else "",
        expected_head_sha=parts[4] if len(parts) >= 5 else "",
    )


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Detect drift in a declared AFS PR branch stack.")
    parser.add_argument("--repo-root", type=Path, default=Path("."), help="Local repository root.")
    parser.add_argument("--entry", action="append", default=[], help="label,base_ref,head_ref[,expected_base_sha[,expected_head_sha]]")
    parser.add_argument("--spec", default="", help="Optional JSON stack spec with an entries list.")
    parser.add_argument("--no-fetch", action="store_true", help="Skip git fetch before resolving refs.")
    parser.add_argument("--report", default="", help="Optional JSON report path.")
    return parser.parse_args(argv)


def _next_action(blockers: list[dict[str, Any]]) -> str:
    if not blockers:
        return "Stack ancestry and pinned refs are aligned; continue PR review, CI, or merge sequencing."
    if any(block["block_id"] in {"base_ref_drifted", "base_not_ancestor_of_head"} for block in blockers):
        return "Rebase or retarget the affected stack entry before claiming integration readiness."
    if any(block["block_id"] == "fetch_failed" for block in blockers):
        return "Repeat with fresh network access or run with --no-fetch only for local evidence."
    return "Resolve the listed stack blockers before merge, deploy, or release claims."


def _same_sha(expected: str, actual: str) -> bool:
    return actual.startswith(expected) or expected.startswith(actual)


def _short(value: str) -> str:
    return value[:12] if value else ""


if __name__ == "__main__":
    sys.exit(main())
