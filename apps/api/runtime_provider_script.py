from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from agentflow.harness.json_io import write_json
from agentflow_studio.schemas import ShortVideoScript
from apps.api.runtime_models import ProviderScriptDraftPlanRequest
from apps.api.runtime_store import reject_unsafe_payload


REMOTE_LLM_ENV = "AFS_ALLOW_REMOTE_LLM"
REMOTE_TRUE_VALUES = {"1", "true", "yes", "on"}
LLM_SCRIPT_NON_CLAIMS = [
    "runtime verification only",
    "not human acceptance",
    "not provider smoke",
    "not business validation",
    "not durable memory",
]


def build_llm_script_draft_plan(
    request: ProviderScriptDraftPlanRequest,
    output_dir: Path,
    *,
    review_note: str | None = None,
) -> dict[str, Any]:
    gate_open = _remote_llm_gate_open()
    gate_status = "ready_not_run" if gate_open else "blocked"
    scaffold_status = "rehearsal" if gate_open else "blocked"
    blockers = [_provider_not_dispatched_block()] if gate_open else [_gate_closed_block()]
    feedback_reuse = _feedback_reuse(
        request.review_feedback_artifact_id,
        previous_script_artifact_id=request.previous_script_artifact_id,
        review_note=review_note,
    )
    provider_gate = {"capability": "llm", "env": REMOTE_LLM_ENV, "status": gate_status}
    policy = _execution_policy()
    local_draft = _local_script_draft(request, feedback_reuse)
    plan = {
        "artifact_type": "agentflow_llm_script_request_plan",
        "schema_version": "0.1.0",
        "project_id": request.project_id,
        "requested_capability": "llm_script",
        "goal": request.goal,
        "target_platform": request.target_platform,
        "style": request.style,
        "generated_at": request.generated_at,
        "provider_gate": provider_gate,
        "prompt_contract": {
            "task_type": "short_video_script",
            "expected_output": "script and storyboard text only",
            "storage_boundary": "safe artifact only; no provider raw payload",
            "review_loop": "keep/revise/reject feedback before second round",
        },
        "feedback_reuse": feedback_reuse,
        "local_draft_available": True,
        **policy,
        "non_claims": LLM_SCRIPT_NON_CLAIMS,
    }
    script_artifact = {
        "artifact_type": "agentflow_script_storyboard_safe_artifact",
        "schema_version": "0.1.0",
        "project_id": request.project_id,
        "status": scaffold_status,
        "source": "local_pre_provider_scaffold",
        "provider_output": False,
        "remote_provider_calls_started": False,
        "goal": request.goal,
        "title": local_draft["scripts"][0]["title"],
        "local_draft": local_draft["summary"],
        "scripts": local_draft["scripts"],
        "storyboard": local_draft["storyboard"],
        "storyboard_text": [item["text"] for item in local_draft["storyboard"]],
        "candidate_constraints": feedback_reuse,
        "review_actions": ["keep", "revise", "reject"],
        "feedback_reuse_policy": feedback_reuse["policy"],
        **policy,
        "non_claims": LLM_SCRIPT_NON_CLAIMS,
    }
    safe_manifest = {
        "artifact_type": "agentflow_llm_script_safe_manifest",
        "schema_version": "0.1.0",
        "project_id": request.project_id,
        "status": scaffold_status,
        "provider_gate": provider_gate,
        "provider_calls_started": False,
        "raw_provider_response_stored": False,
        "generated_media_bytes_stored": False,
        "local_draft_created": True,
        "local_draft_source": local_draft["summary"]["source"],
        "safe_artifacts": [
            "llm_script_request_plan.json",
            "script_storyboard_safe_artifact.json",
        ],
        "blocks": blockers,
        "blockers": blockers,
        "feedback_reuse": feedback_reuse,
        **policy,
        "non_claims": LLM_SCRIPT_NON_CLAIMS,
    }
    for payload in (plan, script_artifact, safe_manifest):
        reject_unsafe_payload(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "llm_script_request_plan.json", plan)
    write_json(output_dir / "script_storyboard_safe_artifact.json", script_artifact)
    write_json(output_dir / "script_provider_safe_manifest.json", safe_manifest)
    return {
        "job_status": "blocked",
        "provider_gate": provider_gate,
        "safe_manifest": safe_manifest,
        "tool_gate_state": {
            "remote_llm": gate_status,
            "remote_asr": "blocked_by_default",
            "remote_image": "not_requested",
            "remote_video": "not_requested",
        },
    }


def _remote_llm_gate_open() -> bool:
    return os.environ.get(REMOTE_LLM_ENV, "").strip().lower() in REMOTE_TRUE_VALUES


def _gate_closed_block() -> dict[str, str]:
    return {
        "block_id": "remote_llm_gate_closed",
        "reason": f"Set {REMOTE_LLM_ENV}=true only for an explicit LLM provider smoke.",
        "required_gate": REMOTE_LLM_ENV,
    }


def _provider_not_dispatched_block() -> dict[str, str]:
    return {
        "block_id": "local_pre_provider_scaffold_rehearsal",
        "reason": "The legacy script draft endpoint does not dispatch provider text; use the M6 server_codex route for real structured LLM planning.",
        "required_route": "/projects/{project_id}/m6/script-plan-asset-bible/preview",
    }


def _execution_policy() -> dict[str, bool]:
    return {
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }


def _feedback_reuse(
    artifact_id: str | None,
    *,
    previous_script_artifact_id: str | None,
    review_note: str | None,
) -> dict[str, str | None]:
    return {
        "source_artifact_id": artifact_id,
        "review_feedback_artifact_id": artifact_id,
        "previous_script_artifact_id": previous_script_artifact_id,
        "constraint_note": review_note,
        "review_note": review_note,
        "policy": "candidate_constraints_only",
        "durable_memory_promotion": "not_allowed_by_runtime",
    }


def _local_script_draft(request: ProviderScriptDraftPlanRequest, feedback_reuse: dict[str, str | None]) -> dict[str, Any]:
    duration = 30 if "30" in request.goal else 45 if "45" in request.goal else 60
    title_goal = _short_goal(request.goal, 18)
    review_note = feedback_reuse.get("review_note") or "暂无审片约束，先按目标生成可审草案。"
    script = {
        "script_id": "script_local_001",
        "project_id": request.project_id,
        "hook_id": "goal_hook_001",
        "platform": request.target_platform,
        "target_duration_sec": duration,
        "style": request.style,
        "title": f"{title_goal}｜本地草案",
        "cover_text": "目标清晰",
        "opening_3s": f"先用一句话说明目标：{request.goal}",
        "segments": [
            {
                "segment_type": "opening",
                "text": f"开场直接交代用户要完成的事：{request.goal}",
                "duration_sec": 3,
            },
            {
                "segment_type": "body",
                "text": "展示输入目标、生成脚本、进入审片、保留证据链的主路径。",
                "duration_sec": max(duration - 13, 10),
            },
            {
                "segment_type": "climax",
                "text": f"按审片约束调整：{review_note}",
                "duration_sec": 7,
            },
            {
                "segment_type": "cta",
                "text": "保留本版草案，等待人工审片后再决定是否进入下一轮。",
                "duration_sec": 3,
            },
        ],
        "cta": "确认这版方向后，再进入下一轮生成或真实 provider smoke。",
        "risk_tags": ["requires_review", "local_draft_only"],
        "score": 0.72,
        "metadata": {
            "source": "local_deterministic_script_draft",
            "provider_smoke": False,
            "feedback_reuse_policy": feedback_reuse["policy"],
        },
    }
    validated_script = ShortVideoScript.model_validate(script).model_dump(mode="json")
    return {
        "summary": {
            "source": "local_deterministic_script_draft",
            "iteration": 2 if feedback_reuse.get("source_artifact_id") or feedback_reuse.get("previous_script_artifact_id") else 1,
            "remote_provider_calls_started": False,
            "provider_smoke": False,
        },
        "scripts": [validated_script],
        "storyboard": _storyboard_from_script(validated_script),
    }


def _storyboard_from_script(script: dict[str, Any]) -> list[dict[str, Any]]:
    labels = {"opening": "开场", "body": "展示", "climax": "转折", "cta": "行动"}
    return [
        {
            "scene_id": f"storyboard_{index:03d}",
            "label": labels.get(str(segment.get("segment_type")), "片段"),
            "text": str(segment.get("text") or ""),
            "duration_sec": segment.get("duration_sec"),
        }
        for index, segment in enumerate(script.get("segments", []), start=1)
        if isinstance(segment, dict)
    ]


def _short_goal(value: str, limit: int) -> str:
    compacted = re.sub(r"\s+", " ", value).strip()
    return compacted[:limit] if len(compacted) > limit else compacted


__all__ = (
    "LLM_SCRIPT_NON_CLAIMS",
    "REMOTE_LLM_ENV",
    "build_llm_script_draft_plan",
)
