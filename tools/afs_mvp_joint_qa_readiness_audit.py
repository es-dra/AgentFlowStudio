from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def main() -> int:
    args = parse_args()
    evidence_root = Path(args.evidence_root).resolve()
    report_path = Path(args.report).resolve() if args.report else evidence_root / "afs_mvp_joint_qa_readiness_audit.json"
    audit = build_readiness_audit(evidence_root)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": audit["status"], "report": str(report_path)}, ensure_ascii=False))
    return 0 if audit["status"] == "recommended" else 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a safe no-cost AFS MVP joint QA readiness audit.")
    parser.add_argument("--evidence-root", required=True)
    parser.add_argument("--report", default="")
    return parser.parse_args()


def build_readiness_audit(evidence_root: Path) -> dict[str, Any]:
    evidence_root = evidence_root.resolve()
    image_blocker = _image_provider_blocker(evidence_root)
    kling_blocker = _kling_provider_blocker(evidence_root)
    provider_blockers = [item for item in (kling_blocker, image_blocker) if item is not None]
    role_checks = _role_checks(evidence_root, provider_blockers)
    status = "needs_fixes" if provider_blockers else "recommended"
    return {
        "artifact_type": "afs_mvp_joint_qa_readiness_audit",
        "schema_version": "0.1.0",
        "status": status,
        "human_acceptance_claim": "not_claimed",
        "provider_blockers": provider_blockers,
        "role_checks": role_checks,
        "summary": {
            "provider_blocker_count": len(provider_blockers),
            "role_count": len(role_checks),
            "passed_role_count": sum(1 for item in role_checks if item["status"] == "passed"),
            "blocked_role_count": sum(1 for item in role_checks if item["status"] == "blocked"),
        },
        "next_actions": _next_actions(provider_blockers),
        "non_claims": [
            "no-cost evidence audit only",
            "not live provider smoke",
            "not human acceptance",
            "not business validation",
            "not durable memory",
        ],
    }


def _image_provider_blocker(evidence_root: Path) -> dict[str, Any] | None:
    manifests = sorted(evidence_root.glob("live_minimax_image_runtime/**/B/keyframe_generation_safe_manifest.json"))
    if not manifests:
        return _missing_evidence_blocker(
            "P1-IMAGE-B-PROVIDER-READINESS",
            "live_minimax_image_runtime/**/B/keyframe_generation_safe_manifest.json",
        )
    manifest_path = manifests[-1]
    manifest = _read_json(manifest_path)
    blocks = _safe_blocks(manifest.get("blocks"))
    if str(manifest.get("status")) != "blocked":
        return None
    return {
        "blocker_id": "P1-IMAGE-B-PROVIDER-READINESS",
        "status": "blocked",
        "root_cause_block_id": _first_block_id(blocks, "remote_image_provider_not_ready"),
        "provider_calls_started": manifest.get("provider_calls_started") is True,
        "retry_count": int(manifest.get("retry_count") or 0),
        "evidence_refs": [_relative_ref(evidence_root, manifest_path)],
    }


def _kling_provider_blocker(evidence_root: Path) -> dict[str, Any] | None:
    preflight_path = evidence_root / "kling_provider_preflight_after_blocker_hardening.json"
    video_manifest_paths = sorted(evidence_root.glob("live_kling_i2v_runtime/**/video_generation_safe_manifest.json"))
    if not preflight_path.is_file() and not video_manifest_paths:
        return _missing_evidence_blocker(
            "P1-KLING-CONFIG-MISSING",
            "kling_provider_preflight_after_blocker_hardening.json or live_kling_i2v_runtime/**/video_generation_safe_manifest.json",
        )
    preflight = _read_json(preflight_path) if preflight_path.is_file() else {}
    video_manifest = _read_json(video_manifest_paths[-1]) if video_manifest_paths else {}
    root_block = str(_nested(preflight, "checks", "block_id") or _first_block_id(_safe_blocks(video_manifest.get("blocks")), "remote_video_provider_not_ready"))
    if root_block in {"", "none"} and str(video_manifest.get("status")) != "blocked":
        return None
    refs = []
    if preflight_path.is_file():
        refs.append(_relative_ref(evidence_root, preflight_path))
    if video_manifest_paths:
        refs.append(_relative_ref(evidence_root, video_manifest_paths[-1]))
    return {
        "blocker_id": "P1-KLING-CONFIG-MISSING",
        "status": "blocked",
        "root_cause_block_id": root_block or "missing_kling_evidence",
        "provider_calls_started": video_manifest.get("provider_calls_started") is True,
        "retry_count": int(video_manifest.get("retry_count") or 0),
        "evidence_refs": refs or ["missing:kling_preflight_or_video_manifest"],
    }


def _role_checks(evidence_root: Path, provider_blockers: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        _file_check("ordinary_internal_tester", evidence_root, "gate_closed_8790_ui_smoke_corrected_report.json"),
        _file_check("creative_director", evidence_root, "live_minimax_image_comparison_report.json"),
        _file_check("asset_manager", evidence_root, "live_minimax_image_comparison_report.json"),
        {
            "role_id": "video_qa",
            "status": "blocked" if any(item["blocker_id"] == "P1-KLING-CONFIG-MISSING" for item in provider_blockers) else "passed",
            "evidence_ref": "live_kling_i2v_report.json",
        },
        _file_check("safety_release_qa", evidence_root, "ai_role_pre_acceptance_summary.json"),
        _file_check("runbook_paths_1_6", evidence_root, "ai_role_pre_acceptance_summary.json"),
        _file_check("frontend_ui_reviewer", evidence_root, "frontend_ui_reviewer_after_fix2_report.json"),
    ]


def _file_check(role_id: str, evidence_root: Path, relative_path: str) -> dict[str, str]:
    path = evidence_root / relative_path
    return {
        "role_id": role_id,
        "status": "passed" if path.is_file() else "missing_evidence",
        "evidence_ref": relative_path,
    }


def _next_actions(provider_blockers: list[dict[str, Any]]) -> list[str]:
    actions = []
    for blocker in provider_blockers:
        if blocker["blocker_id"] == "P1-KLING-CONFIG-MISSING":
            actions.append("Add an ignored local provider config containing kling_i2v plus valid Kling credential env vars before the next live video smoke.")
        if blocker["blocker_id"] == "P1-IMAGE-B-PROVIDER-READINESS":
            actions.append("After explicit image retry approval, rerun MiniMax comparison and inspect arm-level block_ids/retry_count.")
    return actions


def _read_json(path: Path) -> dict[str, Any]:
    payload: Any = None
    for encoding in ("utf-8", "utf-8-sig", "utf-16"):
        try:
            payload = json.loads(path.read_text(encoding=encoding))
            break
        except UnicodeDecodeError:
            continue
        except (OSError, json.JSONDecodeError):
            return {}
    return payload if isinstance(payload, dict) else {}


def _safe_blocks(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _first_block_id(blocks: list[dict[str, Any]], fallback: str) -> str:
    for block in blocks:
        block_id = block.get("block_id")
        if block_id:
            return str(block_id)
    return fallback


def _missing_evidence_blocker(blocker_id: str, evidence_pattern: str) -> dict[str, Any]:
    return {
        "blocker_id": blocker_id,
        "status": "missing_evidence",
        "root_cause_block_id": "missing_evidence",
        "provider_calls_started": False,
        "retry_count": 0,
        "evidence_refs": [f"missing:{evidence_pattern}"],
    }


def _nested(payload: dict[str, Any], *keys: str) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _relative_ref(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
