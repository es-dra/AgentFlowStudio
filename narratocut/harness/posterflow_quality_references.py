from __future__ import annotations

from pathlib import Path
from typing import Any


def add_reference_checks(
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


def candidate_count(payload: dict[str, Any] | None) -> int:
    items = payload.get("candidates") if isinstance(payload, dict) else None
    return len(items) if isinstance(items, list) else 0


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


def _ids(items: object, key: str) -> set[str]:
    if not isinstance(items, list):
        return set()
    return {str(item[key]) for item in items if isinstance(item, dict) and item.get(key)}


def _review_no_long_term_write(items: object) -> bool:
    if not isinstance(items, list) or not items:
        return False
    return all(isinstance(item, dict) and item.get("writes_long_term_memory") is False for item in items)


def _add_check(checks: list[dict[str, Any]], name: str, status: str, details: dict[str, Any] | None = None) -> None:
    check: dict[str, Any] = {"name": name, "status": status}
    if details is not None:
        check["details"] = details
    checks.append(check)
