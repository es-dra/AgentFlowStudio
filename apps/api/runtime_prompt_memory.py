from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow.harness.json_io import write_json
from apps.api.runtime_models import PromptOptimizationRequest
from apps.api.runtime_context_resolver import resolve_context_bundle
from apps.api.runtime_llm_enhancement import maybe_enhance_prompt_with_llm
from apps.api.runtime_model_call_context import prompt_optimization_model_call_context
from apps.api.runtime_prompt_memory_engine import assemble_prompt_context
from apps.api.runtime_prompt_memory_assembly import (
    CONTEXT_PRIORITY,
    extract_background_context,
    provider_gate,
)
from apps.api.runtime_prompt_memory_constants import PROMPT_MEMORY_NON_CLAIMS
from apps.api.runtime_prompt_memory_state import (
    background_context_refs,
    append_extracted_context,
    extracted_context_refs,
    load_creative_memory_state,
    public_background_counts,
    write_creative_memory_state,
)
from apps.api.runtime_prompt_text import strip_user_prompt_section_headers
from apps.api.runtime_script_plan import build_script_plan
from apps.api.runtime_store import RuntimeStore, reject_unsafe_payload


def build_prompt_optimization(
    store: RuntimeStore,
    project_id: str,
    request: PromptOptimizationRequest,
    output_dir: Path,
) -> dict[str, Any]:
    state = load_creative_memory_state(store, project_id)
    assembly_state = _resolver_safe_state(state) if request.context_subgraph else state
    assembly = assemble_prompt_context(request, assembly_state)
    context_bundle = _context_bundle(store, project_id, request)
    llm_enhancement = maybe_enhance_prompt_with_llm(request, assembly)
    if _remote_optimizer_required(request) and llm_enhancement.get("status") != "applied":
        reason = str(llm_enhancement.get("discard_reason") or llm_enhancement.get("status") or "not_available")
        raise ValueError(f"remote LLM prompt optimization unavailable: {reason}")
    rules = assembly["knowledge_rules"]
    background_refs = background_context_refs(state)
    extracted = extract_background_context(project_id, request, assembly["selected_slots"])
    assembled_prompt = str(llm_enhancement.get("optimized_prompt") or assembly["optimized_prompt"])
    user_prompt = str(llm_enhancement.get("user_prompt") or assembly["user_prompt"])
    user_prompt_plain = str(
        llm_enhancement.get("user_prompt_plain")
        or assembly.get("user_prompt_plain")
        or strip_user_prompt_section_headers(user_prompt)
    )
    user_prompt_sections = llm_enhancement.get("user_prompt_sections") or assembly["user_prompt_sections"]
    script_plan = build_script_plan(request)
    if context_bundle:
        signature_segment = str(context_bundle.get("text_channel", {}).get("asset_signature_segment") or "")
        if signature_segment:
            assembled_prompt = f"{assembled_prompt}\nAsset Signatures:\n{signature_segment}"
            user_prompt = f"{user_prompt}\n璧勪骇绛惧悕锛歕n{signature_segment}"
            user_prompt_plain = "\n".join(part for part in (user_prompt_plain, signature_segment) if part)
    brief = _creative_brief(request, project_id, assembled_prompt, llm_enhancement)
    if script_plan:
        brief["script_plan"] = script_plan
    if context_bundle:
        brief["context_bundle"] = context_bundle
    trace = _prompt_trace(request, project_id, assembly, background_refs, extracted, llm_enhancement, context_bundle)
    if script_plan:
        trace["script_plan"] = script_plan
    safe_manifest = _safe_manifest(project_id, len(background_refs), len(extracted), state, assembly, llm_enhancement, context_bundle)
    if script_plan:
        safe_manifest["script_plan_ref"] = "script_plan.json"
        safe_manifest["safe_artifacts"] = [*safe_manifest["safe_artifacts"], "script_plan.json"]
    model_call_context = prompt_optimization_model_call_context(
        project_id=project_id,
        request=request,
        assembly=assembly,
        context_bundle=context_bundle,
    )
    for payload in (brief, trace, safe_manifest, model_call_context):
        reject_unsafe_payload(payload)
    state = append_extracted_context(state, extracted)
    write_creative_memory_state(store, project_id, state)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "model_call_context.json", model_call_context)
    write_json(output_dir / "creative_brief.json", brief)
    if script_plan:
        write_json(output_dir / "script_plan.json", script_plan)
    write_json(output_dir / "prompt_assembly_trace.json", trace)
    write_json(output_dir / "prompt_optimization_safe_manifest.json", safe_manifest)
    return {
        "brief": brief,
        "trace": trace,
        "safe_manifest": safe_manifest,
        "provider_gate": provider_gate(),
        "provider_calls_started": llm_enhancement["provider_calls_started"],
        "original_prompt": request.prompt_text,
        "optimized_prompt": assembled_prompt,
        "optimization_mode": str(llm_enhancement.get("optimization_mode") or "not_applicable"),
        "user_prompt": user_prompt,
        "user_prompt_plain": user_prompt_plain,
        "user_prompt_sections": user_prompt_sections,
        "context_bundle": context_bundle,
        "model_call_context": model_call_context,
        "script_plan": script_plan,
    }


def _context_bundle(
    store: RuntimeStore,
    project_id: str,
    request: PromptOptimizationRequest,
) -> dict[str, Any] | None:
    if not request.context_subgraph:
        return None
    return resolve_context_bundle(
        store,
        project_id,
        mode="optimize",
        visible_prompt=request.prompt_text,
        context_subgraph=request.context_subgraph,
        director_setup=request.director_setup,
    )


def _remote_optimizer_required(request: PromptOptimizationRequest) -> bool:
    params = request.node_parameters or {}
    return bool(params.get("remote_optimizer_required"))


def _resolver_safe_state(state: dict[str, Any]) -> dict[str, Any]:
    safe_state = dict(state)
    for field in ("characters", "scenes", "style_preferences", "user_preferences"):
        safe_state[field] = []
    return safe_state


def _creative_brief(
    request: PromptOptimizationRequest,
    project_id: str,
    assembled_prompt: str,
    llm_enhancement: dict[str, Any],
) -> dict[str, Any]:
    return {
        "artifact_type": "agentflow_creative_brief",
        "schema_version": "0.1.0",
        "project_id": project_id,
        "node_id": request.node_id,
        "node_type": request.node_type,
        "original_prompt": request.prompt_text,
        "optimized_prompt": assembled_prompt,
        "generation_target": request.generation_target,
        "target_platform": request.target_platform,
        "style": request.style,
        "optimization_mode": str(llm_enhancement.get("optimization_mode") or "not_applicable"),
        "negative_constraints": [
            "Do not claim provider execution unless an explicit provider gate is opened.",
            "Do not treat background context as durable project memory.",
            "Do not include private asset paths, signed URLs, or raw provider responses.",
        ],
        "director_setup": request.director_setup.model_dump(mode="json") if request.director_setup else {"view": "not_provided"},
        "node_parameters": request.node_parameters or {},
        "asset_refs": list(request.asset_refs),
        "provider_output": False,
        "provider_calls_started": llm_enhancement["provider_calls_started"],
        "llm_enhancement": _public_llm_enhancement(llm_enhancement),
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": PROMPT_MEMORY_NON_CLAIMS,
    }


def _prompt_trace(
    request: PromptOptimizationRequest,
    project_id: str,
    assembly: dict[str, Any],
    background_refs: list[dict[str, str]],
    extracted: list[dict[str, Any]],
    llm_enhancement: dict[str, Any],
    context_bundle: dict[str, Any] | None,
) -> dict[str, Any]:
    payload = {
        "artifact_type": "agentflow_prompt_assembly_trace",
        "schema_version": "0.1.0",
        "project_id": project_id,
        "node_id": request.node_id,
        "node_type": request.node_type,
        "input_prompt_ref": "request_body.prompt_text",
        "generation_target": request.generation_target,
        "optimization_mode": str(llm_enhancement.get("optimization_mode") or "not_applicable"),
        "context_priority": CONTEXT_PRIORITY,
        "knowledge_rules": assembly["knowledge_rules"],
        "creative_agent": assembly["creative_agent"],
        "selected_slots": assembly["selected_slots"],
        "conflict_resolution": assembly["conflict_resolution"],
        "suppressed_context": assembly["suppressed_context"],
        "professional_reference": assembly["professional_reference"],
        "director_scenario": assembly["director_scenario"],
        "background_context_refs": background_refs,
        "extracted_context_refs": extracted_context_refs(extracted),
        "asset_refs": list(request.asset_refs),
        "knowledgebase_version": assembly["knowledgebase_version"],
        "knowledgebase_registry_hash": assembly["knowledgebase_registry_hash"],
        "knowledgebase_rules_count": assembly["knowledgebase_rules_count"],
        "llm_enhancement": _public_llm_enhancement(llm_enhancement),
        "provider_calls_started": llm_enhancement["provider_calls_started"],
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": PROMPT_MEMORY_NON_CLAIMS,
    }
    if context_bundle:
        payload["context_bundle"] = context_bundle
    return payload


def _safe_manifest(
    project_id: str,
    background_context_count: int,
    extracted_context_count: int,
    state: dict[str, Any],
    assembly: dict[str, Any],
    llm_enhancement: dict[str, Any],
    context_bundle: dict[str, Any] | None,
) -> dict[str, Any]:
    payload = {
        "artifact_type": "agentflow_prompt_optimization_safe_manifest",
        "schema_version": "0.1.0",
        "project_id": project_id,
        "status": "succeeded",
        "provider_gate": provider_gate(),
        "provider_calls_started": llm_enhancement["provider_calls_started"],
        "optimization_mode": str(llm_enhancement.get("optimization_mode") or "not_applicable"),
        "raw_provider_response_stored": False,
        "generated_media_bytes_stored": False,
        "llm_enhancement": _public_llm_enhancement(llm_enhancement),
        "safe_artifacts": [
            "creative_brief.json",
            "prompt_assembly_trace.json",
            "prompt_optimization_safe_manifest.json",
        ],
        "memory_policy": "background context is internal; canvas UI receives optimized prompt and safe artifact refs only",
        "background_context_count": background_context_count,
        "extracted_context_count": extracted_context_count,
        "background_counts_before_run": public_background_counts(state),
        "knowledgebase_version": assembly["knowledgebase_version"],
        "knowledgebase_registry_hash": assembly["knowledgebase_registry_hash"],
        "knowledgebase_rules_count": assembly["knowledgebase_rules_count"],
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": PROMPT_MEMORY_NON_CLAIMS,
    }
    if context_bundle:
        payload["context_bundle_mode"] = context_bundle.get("mode")
        payload["context_included_asset_count"] = len(context_bundle.get("included_assets", []))
    return payload


def _public_llm_enhancement(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "requested": bool(value.get("requested")),
        "status": str(value.get("status") or "not_requested"),
        "provider": str(value.get("provider") or "not_requested"),
        "model": str(value.get("model") or "not_requested"),
        "optimization_mode": str(value.get("optimization_mode") or "not_applicable"),
        "provider_calls_started": bool(value.get("provider_calls_started")),
        "raw_response_stored": False,
        "discard_reason": value.get("discard_reason"),
        "guardrail_fallback_used": bool(value.get("guardrail_fallback_used")),
        "format_retry_count": int(value.get("format_retry_count") or 0),
        "format_salvage_used": bool(value.get("format_salvage_used")),
    }


__all__ = (
    "PROMPT_MEMORY_NON_CLAIMS",
    "build_prompt_optimization",
)
