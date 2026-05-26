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
    round_2_prompt = artifacts.get("round_2/poster_prompt_pack.json") or {}
    round_2_manifest = artifacts.get("round_2/poster_candidates_manifest.json") or {}
    comparison = artifacts.get("poster_round_comparison.json") or {}

    candidate_ids = _ids(manifest.get("candidates"), "candidate_id")
    raw_feedback_ids = _ids(raw_feedback, "target_id")
    feedback_ids = _ids(feedback.get("signals"), "candidate_id")
    memory_ids = _ids(memory.get("candidates"), "memory_candidate_id")
    memory_jsonl_ids = _ids(memory_candidates_jsonl, "memory_candidate_id")
    memory_review_ids = _ids(memory_review, "memory_candidate_id")
    memory_decision_map = {
        item.get("decision_id"): item.get("memory_candidate_id")
        for item in decisions.get("decisions", [])
        if isinstance(item, dict) and item.get("decision_id") and item.get("memory_candidate_id")
    }
    memory_review_map = {
        item.get("review_id"): item.get("memory_candidate_id")
        for item in memory_review
        if isinstance(item, dict) and item.get("review_id") and item.get("memory_candidate_id")
    }
    accepted_ids = {
        item.get("memory_candidate_id")
        for item in decisions.get("decisions", [])
        if isinstance(item, dict) and item.get("decision") == "accepted"
    }
    profile_refs = set(profile.get("source_memory_candidates", [])) if isinstance(profile.get("source_memory_candidates"), list) else set()
    profile_decision_refs = _string_set(profile.get("source_promotion_decisions"))
    bundle_decision_refs = _string_set(context_bundle.get("source_promotion_decisions"))
    next_prompt_decision_refs = _string_set((next_prompt.get("memory_context") or {}).get("promotion_decision_refs"))

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
    _add_check(
        checks,
        "posterflow_memory_review_matches_decisions",
        "pass" if bool(memory_review_map) and memory_review_map == memory_decision_map else "fail",
    )
    _add_check(checks, "posterflow_memory_review_no_long_term_write", "pass" if _review_no_long_term_write(memory_review) else "fail")
    _add_check(checks, "posterflow_profile_does_not_write_long_term_memory", "pass" if profile.get("writes_long_term_memory") is False else "fail")
    _add_check(checks, "posterflow_profile_uses_accepted_memory", "pass" if profile_refs <= accepted_ids <= memory_ids and bool(profile_refs) else "fail")
    _add_check(
        checks,
        "posterflow_profile_refs_promotion_decisions",
        "pass" if profile_decision_refs == set(memory_decision_map) and bool(profile_decision_refs) else "fail",
    )
    _add_check(checks, "posterflow_context_bundle_refs_profile", "pass" if context_bundle.get("preference_profile_path") == "poster_preference_profile.json" else "fail")
    _add_check(checks, "posterflow_context_bundle_refs_prefix", "pass" if context_bundle.get("project_prefix_path") == "project_prefix.md" else "fail")
    _add_check(
        checks,
        "posterflow_context_bundle_refs_promotion_decisions",
        "pass"
        if bundle_decision_refs == profile_decision_refs
        and _string_set((context_bundle.get("context_layers") or {}).get("warm", {}).get("promotion_decision_refs"))
        == profile_decision_refs
        and bool(bundle_decision_refs)
        else "fail",
    )
    _add_check(checks, "posterflow_context_trace_refs_bundle", "pass" if context_trace.get("bundle_id") == context_bundle.get("bundle_id") else "fail")
    _add_check(checks, "posterflow_context_trace_cache_key_matches", "pass" if context_trace.get("cache_key") == (context_bundle.get("cache_plan") or {}).get("cache_key") else "fail")
    _add_check(
        checks,
        "posterflow_context_trace_refs_promotion_decisions",
        "pass" if _string_set(context_trace.get("promotion_decision_refs")) == profile_decision_refs and bool(profile_decision_refs) else "fail",
    )
    _add_check(checks, "posterflow_context_does_not_write_long_term_memory", "pass" if context_bundle.get("writes_long_term_memory") is False and context_trace.get("writes_long_term_memory") is False else "fail")
    _add_check(
        checks,
        "posterflow_next_prompt_refs_profile",
        "pass"
        if (next_prompt.get("memory_context") or {}).get("preference_profile_path") == "poster_preference_profile.json"
        else "fail",
    )
    _add_check(
        checks,
        "posterflow_next_prompt_refs_promotion_decisions",
        "pass" if next_prompt_decision_refs == profile_decision_refs and bool(next_prompt_decision_refs) else "fail",
    )
    _add_check(
        checks,
        "posterflow_next_prompt_does_not_write_long_term_memory",
        "pass" if next_prompt.get("writes_long_term_memory") is False else "fail",
    )
    _add_round_2_checks(run_dir, next_prompt, profile, round_2_prompt, round_2_manifest, comparison, checks)


def candidate_count(payload: dict[str, Any] | None) -> int:
    items = payload.get("candidates") if isinstance(payload, dict) else None
    return len(items) if isinstance(items, list) else 0


def _add_round_2_checks(
    run_dir: Path,
    next_prompt: dict[str, Any],
    profile: dict[str, Any],
    round_2_prompt: dict[str, Any],
    round_2_manifest: dict[str, Any],
    comparison: dict[str, Any],
    checks: list[dict[str, Any]],
) -> None:
    next_run_id = str(next_prompt.get("new_run_id") or "")
    memory_refs = set(profile.get("source_memory_candidates", [])) if isinstance(profile.get("source_memory_candidates"), list) else set()
    round_2_usage = round_2_prompt.get("context_usage") if isinstance(round_2_prompt.get("context_usage"), dict) else {}
    round_2_images = _candidate_image_paths(round_2_manifest)
    comparison_round_2 = comparison.get("round_2") if isinstance(comparison.get("round_2"), dict) else {}
    comparison_memory = comparison.get("memory_reuse") if isinstance(comparison.get("memory_reuse"), dict) else {}
    evidence_chain = comparison.get("evidence_chain")
    promotion_decision_refs = _string_set(profile.get("source_promotion_decisions"))

    _add_check(checks, "posterflow_round_2_prompt_uses_next_run_id", "pass" if round_2_prompt.get("run_id") == next_run_id else "fail")
    _add_check(
        checks,
        "posterflow_round_2_prompt_uses_memory_context",
        "pass"
        if round_2_usage.get("preference_profile_used") is True
        and round_2_usage.get("project_prefix_used") is True
        and set(round_2_usage.get("memory_refs", [])) == memory_refs
        and _string_set(round_2_usage.get("promotion_decision_refs")) == promotion_decision_refs
        and bool(memory_refs)
        and bool(promotion_decision_refs)
        else "fail",
    )
    _add_check(checks, "posterflow_round_2_manifest_uses_next_run_id", "pass" if round_2_manifest.get("run_id") == next_run_id else "fail")
    _add_check(checks, "posterflow_round_2_candidate_count_three", "pass" if len(round_2_images) == 3 else "fail", {"count": len(round_2_images)})
    _add_check(checks, "posterflow_round_2_candidate_images_exist", "pass" if _candidate_images_exist(run_dir, round_2_manifest) else "fail")
    _add_check(
        checks,
        "posterflow_round_2_comparison_candidate_images_match",
        "pass" if set(comparison_round_2.get("candidate_images", [])) == round_2_images and bool(round_2_images) else "fail",
    )
    _add_check(
        checks,
        "posterflow_round_2_comparison_refs_memory",
        "pass"
        if comparison.get("artifact_type") == "poster_round_comparison"
        and set(comparison_memory.get("memory_refs", [])) == memory_refs
        and _string_set(comparison_memory.get("promotion_decision_refs")) == promotion_decision_refs
        and comparison_memory.get("writes_long_term_memory") is False
        else "fail",
    )
    _add_check(
        checks,
        "posterflow_evidence_chain_stages_complete",
        "pass" if _evidence_chain_stages(evidence_chain) == _expected_evidence_chain_stages() else "fail",
    )
    _add_check(
        checks,
        "posterflow_evidence_chain_review_decision_refs_review",
        "pass"
        if _chain_stage_refs(evidence_chain, "review_decision") >= {
            "poster_memory_decisions.json",
            "poster_memory_review.jsonl",
        }
        else "fail",
    )
    _add_check(
        checks,
        "posterflow_evidence_chain_context_refs_bundle",
        "pass" if "context_bundle.json" in _chain_stage_refs(evidence_chain, "context_bundle") else "fail",
    )
    _add_check(
        checks,
        "posterflow_evidence_chain_reuse_refs_promotion_decisions",
        "pass"
        if _chain_stage_source_refs(evidence_chain, "round_2_reuse").get("promotion_decision_refs")
        == ", ".join(sorted(promotion_decision_refs))
        else "fail",
    )
    _add_check(
        checks,
        "posterflow_evidence_chain_no_long_term_write",
        "pass" if _evidence_chain_no_long_term_write(evidence_chain) else "fail",
    )


def _candidate_images_exist(run_dir: Path, manifest: dict[str, Any]) -> bool:
    candidates = manifest.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return False
    return all(isinstance(item, dict) and (run_dir / str(item.get("image_path", ""))).is_file() for item in candidates)


def _candidate_image_paths(manifest: dict[str, Any]) -> set[str]:
    candidates = manifest.get("candidates")
    if not isinstance(candidates, list):
        return set()
    return {str(item.get("image_path")) for item in candidates if isinstance(item, dict) and item.get("image_path")}


def _expected_evidence_chain_stages() -> list[str]:
    return [
        "round_1_evidence",
        "candidate_memory",
        "review_decision",
        "context_bundle",
        "round_2_reuse",
        "comparison_output",
    ]


def _evidence_chain_stages(chain: object) -> list[str]:
    if not isinstance(chain, list):
        return []
    return [str(item.get("stage")) for item in chain if isinstance(item, dict) and item.get("stage")]


def _chain_stage_refs(chain: object, stage: str) -> set[str]:
    if not isinstance(chain, list):
        return set()
    for item in chain:
        if isinstance(item, dict) and item.get("stage") == stage and isinstance(item.get("artifact_refs"), list):
            return {str(ref) for ref in item["artifact_refs"] if ref}
    return set()


def _chain_stage_source_refs(chain: object, stage: str) -> dict[str, Any]:
    if not isinstance(chain, list):
        return {}
    for item in chain:
        if isinstance(item, dict) and item.get("stage") == stage and isinstance(item.get("source_refs"), dict):
            return item["source_refs"]
    return {}


def _evidence_chain_no_long_term_write(chain: object) -> bool:
    if not isinstance(chain, list) or not chain:
        return False
    return all(isinstance(item, dict) and item.get("writes_long_term_memory") is False for item in chain)


def _candidate_only(memory: dict[str, Any]) -> bool:
    candidates = memory.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return False
    return {item.get("promotion_status") for item in candidates if isinstance(item, dict)} <= {"candidate"}


def _ids(items: object, key: str) -> set[str]:
    if not isinstance(items, list):
        return set()
    return {str(item[key]) for item in items if isinstance(item, dict) and item.get(key)}


def _string_set(items: object) -> set[str]:
    if not isinstance(items, list):
        return set()
    return {str(item) for item in items if item}


def _review_no_long_term_write(items: object) -> bool:
    if not isinstance(items, list) or not items:
        return False
    return all(isinstance(item, dict) and item.get("writes_long_term_memory") is False for item in items)


def _add_check(checks: list[dict[str, Any]], name: str, status: str, details: dict[str, Any] | None = None) -> None:
    check: dict[str, Any] = {"name": name, "status": status}
    if details is not None:
        check["details"] = details
    checks.append(check)
