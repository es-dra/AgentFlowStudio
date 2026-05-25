from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from narratocut.harness.quality_profiles import POSTERFLOW_MEMORY_DEMO_PROFILE
from narratostudio.posterflow import (
    ContextAssemblyTrace,
    ContextBundle,
    NextRoundPrompt,
    PosterBrief,
    PosterCandidatesManifest,
    PosterFeedbackSignalLog,
    PosterMemoryCandidates,
    PosterPreferenceProfile,
    PosterPromptPack,
)
from narratostudio.posterflow.schemas import (
    PosterMemoryDecisions,
    PosterModelInvocations,
    PosterPlan,
    PosterRawFeedbackEvent,
    PosterMemoryCandidate,
    PosterMemoryReviewEvent,
)


REQUIRED_ARTIFACTS = [
    "poster_brief.json",
    "poster_plan.json",
    "poster_prompt_pack.json",
    "poster_model_invocations.json",
    "poster_candidates_manifest.json",
    "poster_feedback.jsonl",
    "poster_feedback_signal_log.json",
    "poster_memory_candidates.jsonl",
    "poster_memory_candidates.json",
    "poster_memory_decisions.json",
    "poster_memory_review.jsonl",
    "poster_preference_profile.json",
    "project_prefix.md",
    "context_bundle.json",
    "context_assembly_trace.json",
    "next_round_prompt.json",
    "poster_report.md",
    "poster_preview.html",
    "trace.json",
    "manifest.json",
    "run_manifest.json",
]

SCHEMA_MODELS = {
    "poster_brief.json": PosterBrief,
    "poster_plan.json": PosterPlan,
    "poster_prompt_pack.json": PosterPromptPack,
    "poster_model_invocations.json": PosterModelInvocations,
    "poster_candidates_manifest.json": PosterCandidatesManifest,
    "poster_feedback_signal_log.json": PosterFeedbackSignalLog,
    "poster_memory_candidates.json": PosterMemoryCandidates,
    "poster_memory_decisions.json": PosterMemoryDecisions,
    "poster_preference_profile.json": PosterPreferenceProfile,
    "context_bundle.json": ContextBundle,
    "context_assembly_trace.json": ContextAssemblyTrace,
    "next_round_prompt.json": NextRoundPrompt,
}


def posterflow_artifacts_to_inspect() -> list[str]:
    return list(REQUIRED_ARTIFACTS) + ["image_candidates/"]


def build_posterflow_quality_report(root: str | Path) -> dict[str, Any]:
    run_dir = Path(root)
    checks: list[dict[str, Any]] = []
    artifacts = {name: _read_json_object(run_dir / name) for name in REQUIRED_ARTIFACTS if name.endswith(".json")}
    jsonl_artifacts = {name: _read_jsonl(run_dir / name) for name in REQUIRED_ARTIFACTS if name.endswith(".jsonl")}

    for artifact in REQUIRED_ARTIFACTS:
        _add_file_check(run_dir / artifact, f"posterflow_{_check_name(artifact)}_exists", checks)
    _add_check(checks, "posterflow_image_candidates_dir_exists", "pass" if (run_dir / "image_candidates").is_dir() else "fail")

    _add_json_parse_checks(run_dir, checks)
    _add_schema_checks(artifacts, checks)
    _add_jsonl_schema_checks(jsonl_artifacts, checks)
    _add_reference_checks(run_dir, artifacts, jsonl_artifacts, checks)
    _add_report_checks(run_dir, checks)

    failed = [check for check in checks if check["status"] == "fail"]
    return {
        "status": "fail" if failed else "pass",
        "checks": checks,
        "warnings": [],
        "errors": [_check_error(check) for check in failed],
        "summary": {
            "quality_profile": POSTERFLOW_MEMORY_DEMO_PROFILE,
            "candidate_count": _candidate_count(artifacts.get("poster_candidates_manifest.json")),
            "memory_candidate_count": _candidate_count(artifacts.get("poster_memory_candidates.json")),
        },
    }


def build_posterflow_review_section(root: str | Path) -> dict[str, Any]:
    report = build_posterflow_quality_report(root)
    checks = [_review_check(check) for check in report["checks"]]
    return {
        "name": "posterflow_artifacts",
        "status": _review_status(checks),
        "checks": checks,
    }


def _add_json_parse_checks(run_dir: Path, checks: list[dict[str, Any]]) -> None:
    for artifact in REQUIRED_ARTIFACTS:
        if not artifact.endswith(".json") and not artifact.endswith(".jsonl"):
            continue
        path = run_dir / artifact
        if not path.is_file():
            continue
        if artifact.endswith(".jsonl"):
            _add_check(
                checks,
                f"posterflow_{_check_name(artifact)}_jsonl_valid",
                "pass" if _read_jsonl(path) is not None else "fail",
            )
            continue
        _add_check(
            checks,
            f"posterflow_{_check_name(artifact)}_json_valid",
            "pass" if _read_json_object(path) is not None else "fail",
        )


def _add_schema_checks(artifacts: dict[str, dict[str, Any] | None], checks: list[dict[str, Any]]) -> None:
    for name, payload in artifacts.items():
        if payload is None or name in {"manifest.json", "run_manifest.json", "trace.json"}:
            continue
        model = SCHEMA_MODELS.get(name)
        if model is None:
            continue
        try:
            model.model_validate(payload)
        except ValidationError as exc:
            _add_check(checks, f"posterflow_{_check_name(name)}_schema_valid", "fail", {"error_count": len(exc.errors())})
            continue
        _add_check(checks, f"posterflow_{_check_name(name)}_schema_valid", "pass")
        _add_check(
            checks,
            f"posterflow_{_check_name(name)}_schema_version",
            "pass" if payload.get("schema_version") == "0.1.0" else "fail",
            {"schema_version": payload.get("schema_version")},
        )


def _add_jsonl_schema_checks(
    jsonl_artifacts: dict[str, list[dict[str, Any]] | None],
    checks: list[dict[str, Any]],
) -> None:
    models = {
        "poster_feedback.jsonl": PosterRawFeedbackEvent,
        "poster_memory_candidates.jsonl": PosterMemoryCandidate,
        "poster_memory_review.jsonl": PosterMemoryReviewEvent,
    }
    for name, rows in jsonl_artifacts.items():
        model = models.get(name)
        if rows is None or model is None:
            continue
        failed = 0
        for row in rows:
            try:
                model.model_validate(row)
            except ValidationError:
                failed += 1
        _add_check(
            checks,
            f"posterflow_{_check_name(name)}_schema_valid",
            "pass" if failed == 0 and bool(rows) else "fail",
            {"row_count": len(rows), "failed_rows": failed},
        )


def _add_reference_checks(
    run_dir: Path,
    artifacts: dict[str, dict[str, Any] | None],
    jsonl_artifacts: dict[str, list[dict[str, Any]] | None],
    checks: list[dict[str, Any]],
) -> None:
    manifest = artifacts.get("poster_candidates_manifest.json") or {}
    raw_feedback = jsonl_artifacts.get("poster_feedback.jsonl") or []
    feedback = artifacts.get("poster_feedback_signal_log.json") or {}
    memory_candidates_jsonl = jsonl_artifacts.get("poster_memory_candidates.jsonl") or []
    memory = artifacts.get("poster_memory_candidates.json") or {}
    decisions = artifacts.get("poster_memory_decisions.json") or {}
    memory_review = jsonl_artifacts.get("poster_memory_review.jsonl") or []
    profile = artifacts.get("poster_preference_profile.json") or {}
    context_bundle = artifacts.get("context_bundle.json") or {}
    context_trace = artifacts.get("context_assembly_trace.json") or {}
    next_prompt = artifacts.get("next_round_prompt.json") or {}

    candidate_ids = _ids(manifest.get("candidates"), "candidate_id")
    raw_feedback_ids = _ids(raw_feedback, "target_id")
    feedback_ids = _ids(feedback.get("signals"), "candidate_id")
    memory_ids = _ids(memory.get("candidates"), "memory_candidate_id")
    memory_jsonl_ids = _ids(memory_candidates_jsonl, "memory_candidate_id")
    memory_review_ids = _ids(memory_review, "memory_candidate_id")
    accepted_ids = {
        item.get("memory_candidate_id")
        for item in decisions.get("decisions", [])
        if isinstance(item, dict) and item.get("decision") == "accepted"
    }
    profile_refs = set(profile.get("source_memory_candidates", [])) if isinstance(profile.get("source_memory_candidates"), list) else set()

    _add_check(checks, "posterflow_candidate_count_three", "pass" if len(candidate_ids) == 3 else "fail", {"count": len(candidate_ids)})
    _add_check(checks, "posterflow_candidate_images_exist", "pass" if _candidate_images_exist(run_dir, manifest) else "fail")
    _add_check(
        checks,
        "posterflow_feedback_source_of_truth_is_raw_jsonl",
        "pass" if feedback.get("source_of_truth") == "poster_feedback.jsonl" and bool(raw_feedback) else "fail",
    )
    _add_check(checks, "posterflow_raw_feedback_candidate_refs_known", "pass" if raw_feedback_ids <= candidate_ids and bool(raw_feedback_ids) else "fail")
    _add_check(checks, "posterflow_feedback_candidate_refs_known", "pass" if feedback_ids <= candidate_ids and bool(feedback_ids) else "fail")
    _add_check(checks, "posterflow_memory_jsonl_candidate_only", "pass" if _candidate_only({"candidates": memory_candidates_jsonl}) else "fail")
    _add_check(checks, "posterflow_memory_json_jsonl_match", "pass" if memory_ids == memory_jsonl_ids and bool(memory_ids) else "fail")
    _add_check(checks, "posterflow_memory_candidate_only", "pass" if _candidate_only(memory) else "fail")
    _add_check(checks, "posterflow_memory_review_refs_candidates", "pass" if memory_review_ids <= memory_ids and bool(memory_review_ids) else "fail")
    _add_check(checks, "posterflow_memory_review_no_long_term_write", "pass" if _review_no_long_term_write(memory_review) else "fail")
    _add_check(checks, "posterflow_profile_does_not_write_long_term_memory", "pass" if profile.get("writes_long_term_memory") is False else "fail")
    _add_check(checks, "posterflow_profile_uses_accepted_memory", "pass" if profile_refs <= accepted_ids <= memory_ids and bool(profile_refs) else "fail")
    _add_check(checks, "posterflow_context_bundle_refs_profile", "pass" if context_bundle.get("preference_profile_path") == "poster_preference_profile.json" else "fail")
    _add_check(checks, "posterflow_context_bundle_refs_prefix", "pass" if context_bundle.get("project_prefix_path") == "project_prefix.md" else "fail")
    _add_check(checks, "posterflow_context_trace_refs_bundle", "pass" if context_trace.get("bundle_id") == context_bundle.get("bundle_id") else "fail")
    _add_check(checks, "posterflow_context_trace_cache_key_matches", "pass" if context_trace.get("cache_key") == (context_bundle.get("cache_plan") or {}).get("cache_key") else "fail")
    _add_check(checks, "posterflow_context_does_not_write_long_term_memory", "pass" if context_bundle.get("writes_long_term_memory") is False and context_trace.get("writes_long_term_memory") is False else "fail")
    _add_check(
        checks,
        "posterflow_next_prompt_refs_profile",
        "pass"
        if (next_prompt.get("memory_context") or {}).get("preference_profile_path") == "poster_preference_profile.json"
        else "fail",
    )


def _add_report_checks(run_dir: Path, checks: list[dict[str, Any]]) -> None:
    preview = (run_dir / "poster_preview.html").read_text(encoding="utf-8") if (run_dir / "poster_preview.html").is_file() else ""
    report = (run_dir / "poster_report.md").read_text(encoding="utf-8") if (run_dir / "poster_report.md").is_file() else ""
    _add_check(checks, "posterflow_preview_references_candidate_images", "pass" if "candidate_001.png" in preview else "fail")
    _add_check(checks, "posterflow_report_mentions_memory", "pass" if "Memory Candidates" in report else "fail")


def _candidate_images_exist(run_dir: Path, manifest: dict[str, Any]) -> bool:
    candidates = manifest.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return False
    return all(isinstance(item, dict) and (run_dir / str(item.get("image_path", ""))).is_file() for item in candidates)


def _candidate_only(memory: dict[str, Any]) -> bool:
    candidates = memory.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return False
    return {item.get("promotion_status") for item in candidates if isinstance(item, dict)} <= {"candidate"}


def _read_json_object(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _read_jsonl(path: Path) -> list[dict[str, Any]] | None:
    if not path.is_file():
        return None
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                return None
            rows.append(payload)
    except json.JSONDecodeError:
        return None
    return rows


def _ids(items: object, key: str) -> set[str]:
    if not isinstance(items, list):
        return set()
    return {str(item[key]) for item in items if isinstance(item, dict) and item.get(key)}


def _review_no_long_term_write(items: object) -> bool:
    if not isinstance(items, list) or not items:
        return False
    return all(isinstance(item, dict) and item.get("writes_long_term_memory") is False for item in items)


def _candidate_count(payload: dict[str, Any] | None) -> int:
    items = payload.get("candidates") if isinstance(payload, dict) else None
    return len(items) if isinstance(items, list) else 0


def _add_file_check(path: Path, name: str, checks: list[dict[str, Any]]) -> None:
    _add_check(checks, name, "pass" if path.is_file() else "fail")


def _add_check(checks: list[dict[str, Any]], name: str, status: str, details: dict[str, Any] | None = None) -> None:
    check: dict[str, Any] = {"name": name, "status": status}
    if details is not None:
        check["details"] = details
    checks.append(check)


def _review_check(check: dict[str, Any]) -> dict[str, Any]:
    mapped = "passed" if check["status"] == "pass" else "failed"
    result = {"id": check["name"], "status": mapped, "message": f"{check['name']} {check['status']}"}
    if "details" in check:
        result["details"] = check["details"]
    return result


def _review_status(checks: list[dict[str, Any]]) -> str:
    return "failed" if any(check["status"] == "failed" for check in checks) else "passed"


def _check_name(filename: str) -> str:
    return filename.replace(".jsonl", "").replace(".json", "").replace(".md", "").replace(".html", "")


def _check_error(check: dict[str, Any]) -> str:
    return f"{check['name']} failed"
