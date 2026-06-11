from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow.harness.json_io import write_json
from apps.api.runtime_models import PromptOptimizationRequest
from apps.api.runtime_prompt_memory_engine import assemble_prompt_context
from apps.api.runtime_prompt_memory_assembly import (
    CONTEXT_PRIORITY,
    extract_background_context,
    provider_gate,
)
from apps.api.runtime_prompt_memory_constants import PROMPT_MEMORY_NON_CLAIMS
from apps.api.runtime_prompt_memory_state import (
    background_context_refs,
    extracted_context_refs,
    load_creative_memory_state,
    merge_background_context,
    public_background_counts,
    write_creative_memory_state,
)
from apps.api.runtime_store import RuntimeStore, reject_unsafe_payload


def build_prompt_optimization(
    store: RuntimeStore,
    project_id: str,
    request: PromptOptimizationRequest,
    output_dir: Path,
) -> dict[str, Any]:
    state = load_creative_memory_state(store, project_id)
    assembly = assemble_prompt_context(request, state)
    rules = assembly["knowledge_rules"]
    background_refs = background_context_refs(state)
    extracted = extract_background_context(project_id, request, assembly["selected_slots"])
    assembled_prompt = assembly["optimized_prompt"]
    brief = _creative_brief(request, project_id, assembled_prompt)
    trace = _prompt_trace(request, project_id, assembly, background_refs, extracted)
    safe_manifest = _safe_manifest(project_id, len(background_refs), len(extracted), state, assembly)
    for payload in (brief, trace, safe_manifest):
        reject_unsafe_payload(payload)
    state = merge_background_context(state, extracted)
    write_creative_memory_state(store, project_id, state)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "creative_brief.json", brief)
    write_json(output_dir / "prompt_assembly_trace.json", trace)
    write_json(output_dir / "prompt_optimization_safe_manifest.json", safe_manifest)
    return {
        "brief": brief,
        "trace": trace,
        "safe_manifest": safe_manifest,
        "provider_gate": provider_gate(),
        "original_prompt": request.prompt_text,
        "optimized_prompt": assembled_prompt,
        "user_prompt": assembly["user_prompt"],
        "user_prompt_sections": assembly["user_prompt_sections"],
    }


def _creative_brief(request: PromptOptimizationRequest, project_id: str, assembled_prompt: str) -> dict[str, Any]:
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
        "negative_constraints": [
            "Do not claim provider execution unless an explicit provider gate is opened.",
            "Do not treat background context as durable project memory.",
            "Do not include private asset paths, signed URLs, or raw provider responses.",
        ],
        "director_setup": request.director_setup.model_dump(mode="json") if request.director_setup else {"view": "not_provided"},
        "node_parameters": request.node_parameters or {},
        "asset_refs": list(request.asset_refs),
        "provider_output": False,
        "provider_calls_started": False,
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
) -> dict[str, Any]:
    return {
        "artifact_type": "agentflow_prompt_assembly_trace",
        "schema_version": "0.1.0",
        "project_id": project_id,
        "node_id": request.node_id,
        "node_type": request.node_type,
        "input_prompt_ref": "request_body.prompt_text",
        "generation_target": request.generation_target,
        "context_priority": CONTEXT_PRIORITY,
        "knowledge_rules": assembly["knowledge_rules"],
        "creative_agent": assembly["creative_agent"],
        "selected_slots": assembly["selected_slots"],
        "conflict_resolution": assembly["conflict_resolution"],
        "suppressed_context": assembly["suppressed_context"],
        "background_context_refs": background_refs,
        "extracted_context_refs": extracted_context_refs(extracted),
        "asset_refs": list(request.asset_refs),
        "knowledgebase_version": assembly["knowledgebase_version"],
        "knowledgebase_registry_hash": assembly["knowledgebase_registry_hash"],
        "knowledgebase_rules_count": assembly["knowledgebase_rules_count"],
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": PROMPT_MEMORY_NON_CLAIMS,
    }


def _safe_manifest(
    project_id: str,
    background_context_count: int,
    extracted_context_count: int,
    state: dict[str, Any],
    assembly: dict[str, Any],
) -> dict[str, Any]:
    return {
        "artifact_type": "agentflow_prompt_optimization_safe_manifest",
        "schema_version": "0.1.0",
        "project_id": project_id,
        "status": "succeeded",
        "provider_gate": provider_gate(),
        "provider_calls_started": False,
        "raw_provider_response_stored": False,
        "generated_media_bytes_stored": False,
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


__all__ = (
    "PROMPT_MEMORY_NON_CLAIMS",
    "build_prompt_optimization",
)
