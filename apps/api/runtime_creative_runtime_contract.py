from __future__ import annotations

from typing import Any

from agentflow.algorithms.creative_runtime_contract import (
    build_creative_runtime_contract,
    public_creative_runtime_contract_summary,
)
from apps.api.runtime_models import PromptOptimizationRequest
from apps.api.runtime_script_generation_body import (
    is_script_generation_request,
    is_script_surface_request,
)


def prompt_optimization_creative_runtime_contract(
    *,
    project_id: str,
    request_id: str,
    request: PromptOptimizationRequest,
    state: dict[str, Any],
    assembly: dict[str, Any],
    context_bundle: dict[str, Any] | None,
    model_call_context: dict[str, Any],
    provider_gate_state: dict[str, Any],
    llm_enhancement: dict[str, Any],
) -> dict[str, Any]:
    return build_creative_runtime_contract(
        project_id=project_id,
        request_id=request_id or request.node_id or project_id,
        operation=_operation_for(request),
        owner_intent=_owner_intent(request),
        model_call_context=model_call_context,
        memory_context=_memory_context(state, assembly),
        knowledge_context=assembly,
        asset_context=_asset_context(context_bundle),
        provider_context=_provider_context(provider_gate_state, llm_enhancement),
        evidence_context={
            "model_call_context_ref": "model_call_context.json",
            "safe_manifest_ref": "prompt_optimization_safe_manifest.json",
            "run_trace_ref": "agentflow_run_trace",
            "quality_report_ref": "prompt_optimization_review_summary.json",
            "evidence_state": "structure_verification",
        },
    )


def public_prompt_creative_runtime_contract_summary(
    contract: dict[str, Any],
    *,
    artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    summary = public_creative_runtime_contract_summary(contract)
    if artifact:
        summary["artifact"] = {
            "artifact_id": str(artifact.get("artifact_id") or ""),
            "artifact_type": str(artifact.get("artifact_type") or ""),
            "filename": str(artifact.get("filename") or ""),
            "role": str(artifact.get("role") or ""),
            "media_type": str(artifact.get("media_type") or ""),
        }
    return summary


def _operation_for(request: PromptOptimizationRequest) -> str:
    if is_script_generation_request(request):
        params = request.node_parameters or {}
        if str(params.get("script_generation_mode") or "") == "idea_to_script":
            return "idea_to_script"
        return "script_generation"
    if is_script_surface_request(request):
        return "script_understanding"
    return "prompt_optimization"


def _owner_intent(request: PromptOptimizationRequest) -> dict[str, Any]:
    params = request.node_parameters or {}
    hard_constraints = [
        f"node_type={request.node_type}",
        f"generation_target={request.generation_target}",
        f"target_platform={request.target_platform}",
    ]
    if params.get("remote_optimizer_required") is True:
        hard_constraints.append("remote_optimizer_required")
    if params.get("forbidden_output"):
        hard_constraints.append(f"forbidden_output={params.get('forbidden_output')}")
    soft_preferences = [request.style] if request.style else []
    return {
        "current_request": request.prompt_text,
        "goal_state": _goal_state(request),
        "hard_constraints": hard_constraints,
        "soft_preferences": soft_preferences,
        "explicit_non_goals": [
            "provider media generation",
            "generated media quality claim",
            "durable memory promotion",
        ],
        "acceptance_signals": [
            "safe optimized text returned",
            "model-call context artifact registered",
            "creative runtime contract artifact registered",
        ],
    }


def _goal_state(request: PromptOptimizationRequest) -> str:
    if is_script_generation_request(request):
        return "formal script text ready for later storyboard breakdown"
    if is_script_surface_request(request):
        return "existing script surface preserved with safe optimization trace"
    return f"safe prompt optimization contract for {request.generation_target}"


def _memory_context(state: dict[str, Any], assembly: dict[str, Any]) -> dict[str, Any]:
    return {
        "characters": _list(state.get("characters")),
        "scenes": _list(state.get("scenes")),
        "style_preferences": _list(state.get("style_preferences")),
        "user_preferences": _list(state.get("user_preferences")),
        "extracted_context": _list(state.get("extracted_context")),
        "promotion_candidate_ids": [
            str(item.get("memory_id") or "")
            for item in _list(state.get("extracted_context"))
            if isinstance(item, dict) and item.get("memory_id")
        ],
        "conflict_policy": (assembly.get("conflict_resolution") or {}).get("policy"),
    }


def _asset_context(context_bundle: dict[str, Any] | None) -> dict[str, Any]:
    bundle = context_bundle if isinstance(context_bundle, dict) else {}
    included = _list(bundle.get("included_assets"))
    excluded = _list(bundle.get("excluded_assets"))
    return {
        "fixed_assets": included,
        "excluded_assets": excluded,
        "context_eligible_asset_ids": [
            str(item.get("asset_id") or "")
            for item in included
            if isinstance(item, dict) and item.get("asset_id")
        ],
        "unresolved_asset_refs": [
            str(item.get("asset_id") or item.get("label") or "")
            for item in excluded
            if isinstance(item, dict) and (item.get("asset_id") or item.get("label"))
        ],
    }


def _provider_context(
    provider_gate_state: dict[str, Any],
    llm_enhancement: dict[str, Any],
) -> dict[str, Any]:
    return {
        "capability": "llm",
        "required_gate": str(provider_gate_state.get("required_gate") or "AFS_ALLOW_REMOTE_LLM"),
        "gate_status": str(provider_gate_state.get("status") or "unknown"),
        "provider_service_id": str(llm_enhancement.get("provider") or "not_requested"),
        "provider_calls_started": bool(llm_enhancement.get("provider_calls_started")),
        "fallback_policy": "deterministic_prompt_assembly_or_blocked_remote_optimizer",
    }


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = (
    "prompt_optimization_creative_runtime_contract",
    "public_prompt_creative_runtime_contract_summary",
)
