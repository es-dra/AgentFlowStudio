from __future__ import annotations
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException

from agentflow.algorithms.asset_card_candidates import build_asset_card_candidates
from agentflow.algorithms.content_quality_evaluation import evaluate_storyboard_content_quality
from agentflow.algorithms.evidence_ledger import build_storyboard_evidence_ledger
from agentflow.algorithms.production_graph import build_storyboard_production_graph
from agentflow_studio.model_gateway.errors import ModelGatewayError
from agentflow_studio.model_gateway.provider_adapter import ProviderDispatchRequest, load_provider_registry
from apps.api.runtime_asset_graph import attach_graph_asset_ids_to_shots, build_asset_graph
from apps.api.runtime_errors import safe_error_detail
from apps.api.runtime_flow import build_flow_summary
from apps.api.runtime_jobs import runtime_job
from apps.api.runtime_llm_enhancement_dispatch import dispatch_llm_with_fallback
from apps.api.runtime_llm_enhancement_gate import llm_provider_gate
from apps.api.runtime_models import PromptOptimizationRequest, StoryboardBreakdownRequest
from apps.api.runtime_storyboard_artifacts import write_storyboard_artifacts
from apps.api.runtime_storyboard_local import local_storyboard_shots
from apps.api.runtime_storyboard_provider_parse import shots_from_provider_text
from apps.api.runtime_store import RuntimeStore, reject_unsafe_payload
from apps.api.runtime_tracing import artifact_refs, write_run_trace
from apps.api.runtime_visual_assets import list_visual_assets, public_visual_asset


STORYBOARD_NON_CLAIMS = [
    "not human acceptance",
    "not fixed asset memory",
    "not provider smoke when provider_calls_started is false",
]


def register_runtime_storyboard_routes(app: FastAPI, store: RuntimeStore) -> None:
    @app.post("/projects/{project_id}/storyboard-breakdowns")
    def storyboard_breakdown(project_id: str, request: StoryboardBreakdownRequest) -> dict[str, Any]:
        store.ensure_project_manifest(project_id)
        job_id = store.new_job_id("storyboard_breakdown", project_id)
        output_dir = store.run_dir(project_id, job_id)
        try:
            fixed_visual_assets = [public_visual_asset(item) for item in list_visual_assets(store, project_id, status="fixed")]
            result = build_storyboard_breakdown(project_id, request, output_dir, fixed_visual_assets=fixed_visual_assets)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=safe_error_detail("invalid_storyboard_breakdown")) from exc

        artifacts = write_storyboard_artifacts(store, output_dir, result)
        trace_path = write_run_trace(
            output_dir,
            project_id=project_id,
            job_id=job_id,
            action="storyboard_breakdown",
            status="succeeded",
            input_refs=[
                {"role": "node_id", "ref": request.node_id or "not_provided"},
                {"role": "script_text", "ref": "request_body.script_text"},
                {"role": "target_platform", "ref": request.target_platform},
                {"role": "style", "ref": request.style},
            ],
            generated_artifact_refs=artifact_refs(artifacts),
            tester_feedback={"status": "storyboard_breakdown_ready_for_human_review"},
            tool_gate_state={
                "remote_llm": str(result["provider_gate"].get("status") or "blocked"),
                "remote_asr": "not_requested",
                "remote_image": "not_requested",
                "remote_video": "not_requested",
                "remote_vision": "not_requested",
            },
        )
        artifacts["agentflow_run_trace"] = store.register_artifact(trace_path, role="agentflow_run_trace")
        public_job = store.write_job(runtime_job(job_id, project_id, "storyboard_breakdown", "succeeded", artifacts=artifacts))
        return {
            "job": public_job,
            "shots": result["shots"],
            "asset_graph": result["asset_graph"],
            "asset_auto_binding_graph": result["asset_auto_binding_graph"],
            "content_quality_report": result["content_quality_report"],
            "production_graph": result["production_graph"],
            "asset_card_candidates": result["asset_card_candidates"],
            "evidence_ledger": result["evidence_ledger"],
            "provider_gate": result["provider_gate"],
            "provider_calls_started": result["provider_calls_started"],
            "writes_long_term_memory": False,
            "writes_company_kb": False,
            "safe_manifest": result["safe_manifest"],
            "artifacts": artifacts,
            "flow": build_flow_summary(store, project_id),
            "non_claims": STORYBOARD_NON_CLAIMS,
        }


def build_storyboard_breakdown(
    project_id: str,
    request: StoryboardBreakdownRequest,
    output_dir: Path,
    *,
    fixed_visual_assets: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    gate = llm_provider_gate()
    provider_calls_started = False
    shots: list[dict[str, Any]] | None = None
    status = "local_fallback"
    discard_reason = None
    if gate["status"] != "blocked":
        try:
            registry = load_provider_registry()
            llm_request = _llm_request(request)
            dispatch_request = ProviderDispatchRequest(
                prompt=_storyboard_instruction(request),
                output_dir=output_dir,
                task_type="storyboard_breakdown",
            )
            provider_result = dispatch_llm_with_fallback(registry, llm_request, dispatch_request)
            provider_calls_started = bool(provider_result.get("provider_calls_started", True))
            shots = shots_from_provider_text(str(provider_result.get("text") or ""), source_script_text=request.script_text)
            status = "provider_structured"
        except ValueError as exc:
            discard_reason = _safe_reason(str(exc))
            shots = None
            status = "local_fallback"
        except ModelGatewayError as exc:
            discard_reason = _safe_reason(str(exc))
            shots = None
            provider_calls_started = False
            status = "local_fallback"
    if not shots:
        shots = local_storyboard_shots(request.script_text, request.shot_count_hint)
    asset_graph = build_asset_graph(shots, source_text=request.script_text, graph_source=f"storyboard_{status}")
    shots = attach_graph_asset_ids_to_shots(shots, asset_graph)
    content_quality_report = evaluate_storyboard_content_quality(
        project_id=project_id,
        node_id=request.node_id,
        script_text=request.script_text,
        shots=shots,
        asset_graph=asset_graph,
        provider_calls_started=provider_calls_started,
        shot_count_hint=request.shot_count_hint,
    )
    production_graph = build_storyboard_production_graph(
        project_id=project_id,
        script_node_id=request.node_id,
        script_text=request.script_text,
        shots=shots,
        asset_graph=asset_graph,
        content_quality_report=content_quality_report,
        fixed_visual_assets=fixed_visual_assets or [],
    )
    asset_auto_binding_graph = production_graph.get("asset_auto_binding_graph") if isinstance(production_graph.get("asset_auto_binding_graph"), dict) else {}
    asset_card_candidates = build_asset_card_candidates(project_id=project_id, asset_graph=asset_graph)
    safe_manifest = {
        "artifact_type": "agentflow_storyboard_breakdown_safe_manifest",
        "schema_version": "0.1.0",
        "project_id": project_id,
        "node_id": request.node_id,
        "status": status,
        "provider_gate": gate,
        "provider_calls_started": provider_calls_started,
        "raw_provider_response_stored": False,
        "generated_media_bytes_stored": False,
        "asset_nodes_created": False,
        "shot_count": len(shots),
        "asset_graph_asset_count": int(asset_graph.get("asset_count") or 0),
        "content_quality_report_status": content_quality_report["summary"]["status"],
        "production_graph_node_count": production_graph["summary"]["node_count"],
        "asset_auto_binding_suggested_count": int(
            (asset_auto_binding_graph.get("summary") or {}).get("suggested_binding_count") or 0
        ),
        "asset_auto_binding_established_count": int(
            (asset_auto_binding_graph.get("summary") or {}).get("established_binding_count") or 0
        ),
        "asset_auto_binding_blocked_count": int(
            (asset_auto_binding_graph.get("summary") or {}).get("blocked_candidate_count") or 0
        ),
        "fixed_visual_asset_source_evidence_count": sum(
            1 for item in (fixed_visual_assets or []) if isinstance(item, dict) and item.get("source_evidence")
        ),
        "asset_card_candidate_count": asset_card_candidates["summary"]["candidate_count"],
        "asset_card_project_reuse_candidate_count": int(
            (asset_card_candidates["summary"].get("reuse_scope_counts") or {}).get("project_reuse_candidate") or 0
        ),
        "unsupported_addition_count": len(asset_graph.get("unsupported_additions") or []),
        "held_asset_ref_count": int(asset_graph.get("held_asset_ref_count") or 0),
        "discard_reason": discard_reason,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": STORYBOARD_NON_CLAIMS,
    }
    evidence_ledger = build_storyboard_evidence_ledger(
        project_id=project_id,
        script_node_id=request.node_id,
        provider_gate=gate,
        provider_calls_started=provider_calls_started,
        safe_manifest=safe_manifest,
        asset_graph=asset_graph,
        content_quality_report=content_quality_report,
        production_graph=production_graph,
        asset_card_candidates=asset_card_candidates,
        asset_auto_binding_graph=asset_auto_binding_graph,
    )
    safe_manifest["evidence_ledger_entry_count"] = len(evidence_ledger["evidence_items"])
    safe_manifest["evidence_ledger_stage"] = evidence_ledger["ledger_stage"]
    artifact = {
        "artifact_type": "agentflow_storyboard_breakdown_safe_artifact",
        "schema_version": "0.1.0",
        "project_id": project_id,
        "node_id": request.node_id,
        "provider_output": provider_calls_started,
        "shots": shots,
        "asset_graph": asset_graph,
        "asset_nodes_created": False,
        "review_state": "needs_human_review_before_asset_identification",
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }
    request_plan = {
        "artifact_type": "agentflow_storyboard_breakdown_request_plan",
        "schema_version": "0.1.0",
        "project_id": project_id,
        "node_id": request.node_id,
        "target_platform": request.target_platform,
        "style": request.style,
        "shot_count_hint": request.shot_count_hint,
        "provider_gate": gate,
        "provider_calls_started": provider_calls_started,
        "raw_provider_response_stored": False,
        "asset_graph_contract": "candidate_asset_graph",
    }
    for payload in (safe_manifest, artifact, request_plan, asset_graph):
        reject_unsafe_payload(payload)
    reject_unsafe_payload(content_quality_report)
    reject_unsafe_payload(production_graph)
    reject_unsafe_payload(asset_auto_binding_graph)
    reject_unsafe_payload(asset_card_candidates)
    reject_unsafe_payload(evidence_ledger)
    return {
        "shots": shots,
        "provider_gate": gate,
        "provider_calls_started": provider_calls_started,
        "safe_manifest": safe_manifest,
        "safe_artifact": artifact,
        "asset_graph": asset_graph,
        "asset_auto_binding_graph": asset_auto_binding_graph,
        "content_quality_report": content_quality_report,
        "production_graph": production_graph,
        "asset_card_candidates": asset_card_candidates,
        "evidence_ledger": evidence_ledger,
        "request_plan": request_plan,
    }


def _llm_request(request: StoryboardBreakdownRequest) -> PromptOptimizationRequest:
    params = dict(request.node_parameters or {})
    params.setdefault("llm_provider", "prompt_optimizer")
    return PromptOptimizationRequest(
        node_id=request.node_id,
        node_type="text",
        prompt_text=request.script_text,
        generation_target="script",
        target_platform=request.target_platform,
        style=request.style,
        node_parameters=params,
        generated_at=request.generated_at,
    )


def _storyboard_instruction(request: StoryboardBreakdownRequest) -> str:
    count_line = f"建议镜头数量：{request.shot_count_hint}" if request.shot_count_hint else "根据剧情自动决定镜头数量，避免机械三段切分。"
    return "\n".join(
        [
            "你是影视分镜导演。请把输入剧本拆成专业分镜脚本，输出严格 JSON，不要 Markdown。",
            count_line,
            "JSON 格式：{\"shots\":[{shot_id,index,duration,description,shot_size,light_atmosphere,camera_motion,dialogue,sound,source_span,unsupported_additions,asset_refs}]}",
            "source_span 必须包含 span_id 与 text，text 必须逐字来自剧本原文；不能为镜头效果擅自新增人物、道具、家具、屋檐或场景结构。",
            "unsupported_additions 必须列出所有剧本未提供但你认为需要补入的内容；正常情况下应为空数组，不能静默添加。",
            "asset_refs 每项必须包含 label, asset_type(character|scene|prop), status, source, evidence_text, confidence。描述中涉及角色、场景、道具时必须用 @名称 显式标注。",
            "不要用泛化的“主角”“主要场景”替代剧本里的真实名称；例如孙悟空、金刚狼必须分别作为 character，金箍棒、武器、信件、地图等必须作为 prop。",
            "每个镜头要包含时长、画面描述、景别、光影氛围、运镜、对白/旁白、音效。",
            f"平台：{request.target_platform}；风格：{request.style}",
            "剧本：",
            request.script_text,
        ]
    )


def _safe_reason(value: str) -> str:
    lowered = value.lower()
    if any(term in lowered for term in ("api", "key", "secret", "token", "authorization", "cookie")):
        return "llm provider configuration is not ready"
    return " ".join(value.split())[:160] or "llm provider is not ready"


__all__ = (
    "STORYBOARD_NON_CLAIMS",
    "build_storyboard_breakdown",
    "local_storyboard_shots",
    "register_runtime_storyboard_routes",
)
