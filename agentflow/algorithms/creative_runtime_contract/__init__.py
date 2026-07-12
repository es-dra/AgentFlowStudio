from __future__ import annotations

import hashlib
import json
from typing import Any

from agentflow.algorithms.model_call_context import sanitize_context_payload, sanitize_context_text
from agentflow.algorithms.provider_gate_manifest import required_gate_for


ALGORITHM_ID = "afs.creative_runtime_contract.v0.1"
INPUT_CONTRACT = "owner intent, memory context, knowledge context, asset context, model-call context, provider gate state, evidence refs"
OUTPUT_CONTRACT = "safe creative runtime contract tying intent, memory, knowledge, assets, model context, gates, and evidence"
FAILURE_MODES = ("unknown_creative_operation", "unsafe_contract_payload_redacted", "provider_gate_not_declared")
EVIDENCE_BOUNDARY = "planning and routing contract only; no provider calls, media QA, durable memory promotion, or human acceptance"

SCHEMA_VERSION = "afs_creative_runtime_contract.v0.1"
CONTRACT_PREFIX = "crtc_"

CREATIVE_OPERATIONS = {
    "idea_to_script",
    "script_generation",
    "script_understanding",
    "storyboard_breakdown",
    "asset_extraction",
    "prompt_optimization",
    "image_generation",
    "video_generation",
    "revision",
}

OPERATION_TARGETS = {
    "idea_to_script": "script",
    "script_generation": "script",
    "script_understanding": "script",
    "storyboard_breakdown": "storyboard",
    "asset_extraction": "asset_graph",
    "prompt_optimization": "prompt",
    "image_generation": "image",
    "video_generation": "video",
    "revision": "revision",
}

TARGET_CAPABILITIES = {
    "script": "llm",
    "storyboard": "llm",
    "asset_graph": "llm",
    "prompt": "llm",
    "image": "image",
    "video": "video",
    "revision": "video",
}

NON_CLAIMS = (
    "not_provider_execution",
    "not_generated_media_qa",
    "not_human_acceptance",
    "not_business_validation",
    "not_public_readiness",
    "not_legal_review",
    "not_durable_memory_promotion",
)


def build_creative_runtime_contract(
    *,
    project_id: str,
    request_id: str,
    operation: str,
    owner_intent: dict[str, Any] | None = None,
    model_call_context: dict[str, Any] | None = None,
    memory_context: dict[str, Any] | None = None,
    knowledge_context: dict[str, Any] | None = None,
    asset_context: dict[str, Any] | None = None,
    provider_context: dict[str, Any] | None = None,
    evidence_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_operation = str(operation or "").strip()
    if normalized_operation not in CREATIVE_OPERATIONS:
        raise ValueError("unknown creative runtime operation")

    generation_target = OPERATION_TARGETS[normalized_operation]
    capability = _capability_for(generation_target, provider_context)
    contract = {
        "artifact_type": "agentflow_creative_runtime_contract",
        "schema_version": SCHEMA_VERSION,
        "algorithm_id": ALGORITHM_ID,
        "project_id": sanitize_context_text(project_id).strip(),
        "request_id": sanitize_context_text(request_id).strip(),
        "operation": normalized_operation,
        "generation_target": generation_target,
        "owner_intent": _owner_intent(owner_intent),
        "memory_context": _memory_context(memory_context),
        "knowledge_context": _knowledge_context(knowledge_context),
        "asset_context": _asset_context(asset_context),
        "model_call_context": _model_call_context(model_call_context),
        "provider_context": _provider_context(
            provider_context,
            capability=capability,
            generation_target=generation_target,
        ),
        "evidence_context": _evidence_context(evidence_context, model_call_context),
        "runtime_policy": {
            "contract_stage": "creative_runtime_planning",
            "provider_calls_started": False,
            "writes_long_term_memory": False,
            "writes_company_kb": False,
            "requires_provider_gate_before_execution": True,
            "requires_evaluator_before_quality_claim": True,
        },
        "safety_boundary": _safety_boundary(),
        "non_claims": list(NON_CLAIMS),
    }
    contract = sanitize_context_payload(contract)
    contract["contract_id"] = _contract_id(contract)
    return contract


def public_creative_runtime_contract_summary(contract: dict[str, Any]) -> dict[str, Any]:
    memory = _dict(contract.get("memory_context"))
    knowledge = _dict(contract.get("knowledge_context"))
    assets = _dict(contract.get("asset_context"))
    provider = _dict(contract.get("provider_context"))
    model_context = _dict(contract.get("model_call_context"))
    evidence = _dict(contract.get("evidence_context"))
    return {
        "contract_id": str(contract.get("contract_id") or ""),
        "schema_version": str(contract.get("schema_version") or ""),
        "operation": str(contract.get("operation") or ""),
        "generation_target": str(contract.get("generation_target") or ""),
        "memory_context": {
            "project_memory_count": len(_list(memory.get("project_memory_refs"))),
            "user_preference_count": len(_list(memory.get("user_preference_refs"))),
            "promotion_candidates_only": bool(memory.get("promotion_candidates_only")),
        },
        "knowledge_context": {
            "rule_count": len(_list(knowledge.get("rule_ids"))),
            "director_scenario_count": len(_list(knowledge.get("director_scenario_ids"))),
            "registry_hash": str(knowledge.get("registry_hash") or ""),
        },
        "asset_context": {
            "fixed_asset_count": len(_list(assets.get("fixed_asset_ids"))),
            "draft_asset_count": len(_list(assets.get("draft_asset_ids"))),
            "unresolved_asset_count": len(_list(assets.get("unresolved_asset_refs"))),
        },
        "model_call_context": {
            "context_id": str(model_context.get("context_id") or ""),
            "schema_version": str(model_context.get("schema_version") or ""),
        },
        "provider_context": {
            "capability": str(provider.get("capability") or ""),
            "required_gate": str(provider.get("required_gate") or ""),
            "gate_status": str(provider.get("gate_status") or ""),
            "provider_calls_started": bool(provider.get("provider_calls_started")),
        },
        "evidence_context": {
            "model_call_context_id": str(evidence.get("model_call_context_id") or ""),
            "safe_manifest_ref": str(evidence.get("safe_manifest_ref") or ""),
        },
        "non_claims": _safe_ref_list(contract.get("non_claims")),
    }


def _owner_intent(value: dict[str, Any] | None) -> dict[str, Any]:
    source = _dict(value)
    return {
        "current_request": _text(source.get("current_request")),
        "goal_state": _text(source.get("goal_state")),
        "hard_constraints": _safe_text_list(source.get("hard_constraints")),
        "soft_preferences": _safe_text_list(source.get("soft_preferences")),
        "explicit_non_goals": _safe_text_list(source.get("explicit_non_goals")),
        "acceptance_signals": _safe_text_list(source.get("acceptance_signals")),
    }


def _memory_context(value: dict[str, Any] | None) -> dict[str, Any]:
    source = _dict(value)
    project_refs = _safe_memory_refs(
        [
            *_list(source.get("project_memory_refs")),
            *_list(source.get("characters")),
            *_list(source.get("scenes")),
        ]
    )
    preference_refs = _safe_memory_refs(
        [
            *_list(source.get("user_preference_refs")),
            *_list(source.get("style_preferences")),
            *_list(source.get("user_preferences")),
        ]
    )
    feedback_refs = _safe_memory_refs(source.get("prior_feedback_refs") or source.get("extracted_context"))
    promotion_candidates = _safe_ref_list(source.get("promotion_candidate_ids"))
    return {
        "project_memory_refs": project_refs,
        "user_preference_refs": preference_refs,
        "prior_feedback_refs": feedback_refs,
        "promotion_candidate_ids": promotion_candidates,
        "promotion_candidates_only": True,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "durable_memory_promotion": False,
        "source_claim_boundary": "runtime_context_not_durable_memory",
    }


def _knowledge_context(value: dict[str, Any] | None) -> dict[str, Any]:
    source = _dict(value)
    rules = source.get("knowledge_rules") if isinstance(source.get("knowledge_rules"), list) else []
    director = _dict(source.get("director_scenario"))
    professional = _dict(source.get("professional_reference"))
    return {
        "knowledgebase_version": _text(source.get("knowledgebase_version") or source.get("registry_version")),
        "registry_hash": _text(source.get("knowledgebase_registry_hash") or source.get("registry_hash")),
        "rule_ids": _safe_ref_list(source.get("rule_ids") or [rule.get("rule_id") for rule in rules if isinstance(rule, dict)]),
        "director_scenario_ids": _director_scenario_ids(source.get("director_scenario_ids"), director),
        "professional_reference_ids": _professional_reference_ids(source.get("professional_reference_ids"), professional),
        "conflict_policy": _text(_dict(source.get("conflict_resolution")).get("policy") or source.get("conflict_policy")),
        "knowledge_is_reference_not_authority_promotion": True,
    }


def _asset_context(value: dict[str, Any] | None) -> dict[str, Any]:
    source = _dict(value)
    fixed = source.get("fixed_assets") or source.get("fixed_visual_assets") or []
    draft = source.get("draft_assets") or []
    rejected = source.get("rejected_assets") or []
    retired = source.get("retired_assets") or []
    unresolved = source.get("unresolved_assets") or source.get("unresolved_asset_refs") or []
    excluded = source.get("excluded_assets") or []
    return {
        "fixed_asset_ids": _asset_ids(fixed),
        "draft_asset_ids": _asset_ids(draft),
        "rejected_asset_ids": _asset_ids(rejected),
        "retired_asset_ids": _asset_ids(retired),
        "excluded_asset_refs": _asset_refs(excluded),
        "unresolved_asset_refs": _asset_refs(unresolved),
        "identity_registry_refs": _safe_ref_list(source.get("identity_registry_refs")),
        "binding_decision_refs": _safe_ref_list(source.get("binding_decision_refs")),
        "context_eligible_asset_ids": _safe_ref_list(source.get("context_eligible_asset_ids") or _asset_ids(fixed)),
        "draft_assets_enter_context": False,
        "asset_identity_claim_boundary": "fixed_or_candidate_asset_context_not_generated_media_quality",
    }


def _model_call_context(value: dict[str, Any] | None) -> dict[str, Any]:
    source = _dict(value)
    return {
        "context_id": _text(source.get("context_id")),
        "schema_version": _text(source.get("schema_version")),
        "operation_intent": _text(source.get("operation_intent")),
        "generation_target": _text(source.get("generation_target")),
        "trace_summary": {
            "warning_ids": _safe_ref_list(_dict(source.get("trace_summary")).get("warning_ids")),
            "feedback_context_overlay_ids": _safe_ref_list(
                _dict(source.get("trace_summary")).get("feedback_context_overlay_ids")
            ),
        },
        "safety_boundary": _dict(source.get("safety_boundary")),
    }


def _provider_context(
    value: dict[str, Any] | None,
    *,
    capability: str,
    generation_target: str,
) -> dict[str, Any]:
    source = _dict(value)
    required_gate = _text(source.get("required_gate") or source.get("provider_gate") or required_gate_for(capability))
    return {
        "capability": capability,
        "generation_target": generation_target,
        "required_gate": required_gate,
        "gate_status": _text(source.get("gate_status") or source.get("status") or "unknown"),
        "provider_service_id": _text(source.get("provider_service_id") or "not_selected"),
        "provider_calls_started": False,
        "source_reported_provider_calls_started": bool(source.get("provider_calls_started")),
        "fallback_policy": _text(source.get("fallback_policy") or "deterministic_or_blocked_until_gate_open"),
        "claim_boundary": "provider_gate_state_not_provider_qa",
    }


def _evidence_context(
    value: dict[str, Any] | None,
    model_call_context: dict[str, Any] | None,
) -> dict[str, Any]:
    source = _dict(value)
    model_context = _dict(model_call_context)
    return {
        "model_call_context_id": _text(source.get("model_call_context_id") or model_context.get("context_id")),
        "model_call_context_ref": _text(source.get("model_call_context_ref")),
        "safe_manifest_ref": _text(source.get("safe_manifest_ref")),
        "run_trace_ref": _text(source.get("run_trace_ref")),
        "quality_report_ref": _text(source.get("quality_report_ref")),
        "runtime_health_ref": _text(source.get("runtime_health_ref")),
        "evidence_state": _text(source.get("evidence_state") or "structure_verification"),
    }


def _capability_for(generation_target: str, provider_context: dict[str, Any] | None) -> str:
    source = _dict(provider_context)
    capability = str(source.get("capability") or "").strip()
    return capability or TARGET_CAPABILITIES.get(generation_target, "llm")


def _safe_memory_refs(values: Any) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for item in _list(values):
        if not isinstance(item, dict):
            continue
        memory_id = _text(item.get("memory_id") or item.get("id") or item.get("label"))
        if not memory_id:
            continue
        ref = {
            "memory_id": memory_id,
            "memory_type": _text(item.get("memory_type") or item.get("type")),
            "label": _text(item.get("label")),
            "source": _text(item.get("source") or "runtime_context"),
        }
        if ref not in refs:
            refs.append(ref)
    return refs


def _director_scenario_ids(values: Any, director: dict[str, Any]) -> list[str]:
    explicit = _safe_ref_list(values)
    if explicit:
        return explicit
    packs = director.get("selected_packs") if isinstance(director.get("selected_packs"), list) else []
    return _safe_ref_list([
        "director_scenario:" + str(pack.get("scenario_id") or "")
        for pack in packs
        if isinstance(pack, dict) and pack.get("scenario_id")
    ])


def _professional_reference_ids(values: Any, professional: dict[str, Any]) -> list[str]:
    explicit = _safe_ref_list(values)
    if explicit:
        return explicit
    refs = professional.get("references") if isinstance(professional.get("references"), list) else []
    return _safe_ref_list([
        str(ref.get("reference_id") or ref.get("id") or "")
        for ref in refs
        if isinstance(ref, dict) and (ref.get("reference_id") or ref.get("id"))
    ])


def _asset_ids(values: Any) -> list[str]:
    refs: list[str] = []
    for item in _list(values):
        if isinstance(item, dict):
            ref = _text(item.get("asset_id") or item.get("id"))
        else:
            ref = _text(item)
        if ref and ref not in refs:
            refs.append(ref)
    return refs


def _asset_refs(values: Any) -> list[str]:
    refs: list[str] = []
    for item in _list(values):
        if isinstance(item, dict):
            ref = _text(item.get("asset_id") or item.get("graph_asset_id") or item.get("label"))
        else:
            ref = _text(item)
        if ref and ref not in refs:
            refs.append(ref)
    return refs


def _safe_ref_list(values: Any) -> list[str]:
    refs: list[str] = []
    for value in _list(values):
        ref = _text(value)
        if ref and ref not in refs:
            refs.append(ref)
    return refs


def _safe_text_list(values: Any) -> list[str]:
    return [_text(value) for value in _list(values) if _text(value)]


def _text(value: Any) -> str:
    return sanitize_context_text(value).strip()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _contract_id(payload: dict[str, Any]) -> str:
    public_payload = {key: value for key, value in payload.items() if key != "contract_id"}
    data = json.dumps(public_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return CONTRACT_PREFIX + hashlib.sha256(data).hexdigest()[:20]


def _safety_boundary() -> dict[str, bool]:
    return {
        "no_secrets": True,
        "no_provider_raw": True,
        "no_credentialed_url": True,
        "no_local_path": True,
        "no_media_bytes": True,
        "provider_gate_required_before_execution": True,
        "feedback_is_not_memory": True,
        "durable_memory_promotion_requires_human_review": True,
    }


__all__ = (
    "ALGORITHM_ID",
    "CONTRACT_PREFIX",
    "CREATIVE_OPERATIONS",
    "EVIDENCE_BOUNDARY",
    "FAILURE_MODES",
    "INPUT_CONTRACT",
    "NON_CLAIMS",
    "OPERATION_TARGETS",
    "OUTPUT_CONTRACT",
    "SCHEMA_VERSION",
    "build_creative_runtime_contract",
    "public_creative_runtime_contract_summary",
)
