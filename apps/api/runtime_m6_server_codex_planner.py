from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Mapping

from agentflow_studio.model_gateway.company_secrets import SERVER_CODEX_SERVICE_ID
from agentflow_studio.model_gateway.errors import ModelConfigError, ModelGatewayError
from agentflow_studio.model_gateway.provider_adapter import (
    ProviderDispatchRequest,
    load_provider_registry,
    structured_output_schema_digest,
)
from apps.api.runtime_m6_script_plan_asset_bible import (
    FILM_SCHEMA_VERSION,
    M6_SCHEMA_VERSION,
    M6PlanningError,
    PRODUCTION_AID_KINDS,
    build_m6_scope_review,
    _knowledge_context,
    _review_requirements,
    _safe_token,
    m6_asset_scope_fields,
    m6_source_canonical_scope,
    validate_m6_candidate,
)
from apps.api.runtime_production_graph import canonical_digest


REMOTE_LLM_ENV = "AFS_ALLOW_REMOTE_LLM"
TRUE_VALUES = {"1", "true", "yes", "on"}
SERVER_CODEX_CONTRACT_ID = "afs.m6.server_codex_script_plan_asset_bible.v0.1"


def server_codex_m6_enabled() -> bool:
    return os.environ.get(REMOTE_LLM_ENV, "").strip().lower() in TRUE_VALUES


def build_m6_server_codex_script_plan_asset_bible(project_id: str, body: Mapping[str, Any]) -> dict[str, Any]:
    source_text = _text(body.get("source_text"))
    if len(source_text) < 40:
        raise M6PlanningError("M6 server_codex preview requires source_text with enough project context.")
    revision_instruction = _text(body.get("revision_instruction"))
    parent_candidate_digest = _text(body.get("parent_candidate_digest"))
    requested_language = _text(body.get("requested_language") or "zh-CN") or "zh-CN"
    schema = m6_server_codex_output_schema()
    schema_digest = structured_output_schema_digest(schema)
    source_digest = canonical_digest({
        "schema_version": M6_SCHEMA_VERSION,
        "source_kind": body.get("source_kind") or "idea",
        "source_text": source_text,
        "revision_instruction": revision_instruction,
        "parent_candidate_digest": parent_candidate_digest,
        "provider": SERVER_CODEX_SERVICE_ID,
        "contract": SERVER_CODEX_CONTRACT_ID,
        "schema_digest": schema_digest,
    })
    dispatch_id = f"m6_server_codex_{source_digest[:16]}"
    prompt = _server_codex_prompt(
        project_id=project_id,
        source_kind=str(body.get("source_kind") or "idea"),
        source_text=source_text,
        requested_language=requested_language,
        revision_instruction=revision_instruction,
        parent_candidate_digest=parent_candidate_digest,
        schema_digest=schema_digest,
        dispatch_id=dispatch_id,
    )
    try:
        result = _dispatch_server_codex_structured_plan(
            prompt=prompt,
            output_dir=Path(os.environ.get("AFS_M6_SERVER_CODEX_OUTPUT_DIR", "/tmp")) / dispatch_id,
            schema=schema,
            schema_digest=schema_digest,
        )
    except (ModelConfigError, ModelGatewayError) as exc:
        raise M6PlanningError(f"server_codex provider dispatch failed: {exc}") from exc
    if result.get("provider_calls_started") is not True:
        raise M6PlanningError("server_codex did not start a real provider dispatch")
    payload = result.get("structured_output")
    if not isinstance(payload, Mapping):
        raise M6PlanningError("server_codex structured output is missing")
    candidate = _candidate_from_provider_payload(
        project_id=project_id,
        body=body,
        payload=payload,
        source_digest=source_digest,
        dispatch_id=dispatch_id,
        schema_digest=schema_digest,
        prompt_chars=len(prompt),
        parent_candidate_digest=parent_candidate_digest,
        revision_instruction=revision_instruction,
    )
    validation = validate_m6_candidate(candidate)
    return {
        "artifact_type": "afs_m6_server_codex_script_plan_asset_bible_preview",
        "schema_version": M6_SCHEMA_VERSION,
        "project_id": project_id,
        "candidate": candidate,
        "candidate_digest": canonical_digest(candidate),
        "validation": validation,
        "provider_dispatch_count": 1,
        "cost_usd": 0,
        "provider_lineage": candidate["provider_lineage"],
        "non_claims": [
            "not_remote_paid_provider_smoke",
            "not_generated_media_qa",
            "not_human_acceptance",
            "not_business_validation",
        ],
    }


def _dispatch_server_codex_structured_plan(
    *,
    prompt: str,
    output_dir: Path,
    schema: dict[str, Any],
    schema_digest: str,
) -> dict[str, Any]:
    registry = load_provider_registry()
    return registry.dispatch(
        "llm",
        SERVER_CODEX_SERVICE_ID,
        ProviderDispatchRequest(
            prompt=prompt,
            output_dir=output_dir,
            task_type="m6_server_codex_script_plan_asset_bible",
            structured_output_contract_id=SERVER_CODEX_CONTRACT_ID,
            structured_output_schema=schema,
            structured_output_schema_digest=schema_digest,
            timeout_sec=float(os.environ.get("AFS_M6_SERVER_CODEX_TIMEOUT_SEC", "600")),
        ),
    )


def m6_server_codex_output_schema() -> dict[str, Any]:
    text = {"type": "string", "minLength": 2}
    sentence = {"type": "string", "minLength": 8}
    lock_list = {"type": "array", "minItems": 2, "maxItems": 8, "items": text}
    index_list = {"type": "array", "minItems": 1, "maxItems": 16, "items": {"type": "integer", "minimum": 1}}
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["language", "title", "logline", "draft_text", "structure", "characters", "scenes", "assets", "shots", "revision_notes"],
        "properties": {
            "language": {"type": "string", "enum": ["zh-CN"]},
            "title": text,
            "logline": {"type": "string", "minLength": 12},
            "draft_text": {"type": "string", "minLength": 240},
            "revision_notes": {"type": "string", "minLength": 12},
            "structure": {
                "type": "object",
                "additionalProperties": False,
                "required": ["sequence_count", "scene_count", "turning_points", "rhythm_strategy", "rights_time_summary"],
                "properties": {
                    "sequence_count": {"type": "integer"},
                    "scene_count": {"type": "integer"},
                    "turning_points": {"type": "array", "minItems": 2, "maxItems": 8, "items": text},
                    "rhythm_strategy": {"type": "string", "minLength": 12},
                    "rights_time_summary": {"type": "string", "minLength": 12},
                },
            },
            "characters": {
                "type": "array",
                "minItems": 1,
                "maxItems": 10,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["display_name", "goal", "conflict", "relationship_arc", "change_vector", "appearance", "wardrobe", "age_range", "proportion", "signature_features", "do_not_change"],
                    "properties": {
                        "display_name": text,
                        "goal": sentence,
                        "conflict": sentence,
                        "relationship_arc": sentence,
                        "change_vector": sentence,
                        "appearance": sentence,
                        "wardrobe": {"type": "string", "minLength": 6},
                        "age_range": text,
                        "proportion": text,
                        "signature_features": lock_list,
                        "do_not_change": lock_list,
                    },
                },
            },
            "scenes": {
                "type": "array",
                "minItems": 1,
                "maxItems": 8,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["name", "space", "time_of_day", "lighting", "season", "continuity", "action", "rhythm", "emotion", "visual_expression", "dialogue_or_sound", "do_not_change"],
                    "properties": {
                        "name": text,
                        "space": {"type": "string", "minLength": 6},
                        "time_of_day": text,
                        "lighting": {"type": "string", "minLength": 6},
                        "season": text,
                        "continuity": {"type": "string", "minLength": 10},
                        "action": {"type": "string", "minLength": 10},
                        "rhythm": sentence,
                        "emotion": sentence,
                        "visual_expression": {"type": "string", "minLength": 10},
                        "dialogue_or_sound": lock_list,
                        "do_not_change": lock_list,
                    },
                },
            },
            "assets": {
                "type": "array",
                "minItems": 1,
                "maxItems": 32,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["name", "kind", "source", "version", "applicable_scope", "confidence", "rights_boundary", "style", "do_not_change"],
                    "properties": {
                        "name": text,
                        "kind": {"type": "string", "enum": ["prop", "closeup", "reference_set", "style"]},
                        "source": {"type": "string", "minLength": 6},
                        "version": text,
                        "applicable_scope": text,
                        "confidence": {"type": "number"},
                        "rights_boundary": {"type": "string", "minLength": 10},
                        "style": text,
                        "do_not_change": lock_list,
                    },
                },
            },
            "shots": {
                "type": "array",
                "minItems": 3,
                "maxItems": 9,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["scene_index", "duration_seconds", "intent", "character_indexes", "asset_indexes", "shot_size", "camera_angle", "camera_movement", "blocking", "sound", "transition", "narrative_purpose", "content_driven_duration_reason"],
                    "properties": {
                        "scene_index": {"type": "integer", "minimum": 1},
                        "duration_seconds": {"type": "number"},
                        "intent": {"type": "string", "minLength": 10},
                        "character_indexes": {"type": "array", "minItems": 1, "maxItems": 5, "items": {"type": "integer", "minimum": 1}},
                        "asset_indexes": index_list,
                        "shot_size": {"type": "string", "enum": ["特写", "近景", "中景", "全景", "远景", "过肩", "主观"]},
                        "camera_angle": text,
                        "camera_movement": text,
                        "blocking": {"type": "string", "minLength": 10},
                        "sound": {"type": "string", "minLength": 6},
                        "transition": {"type": "string", "minLength": 2},
                        "narrative_purpose": {"type": "string", "minLength": 10},
                        "content_driven_duration_reason": {"type": "string", "minLength": 12},
                    },
                },
            },
        },
    }


def _server_codex_prompt(
    *,
    project_id: str,
    source_kind: str,
    source_text: str,
    requested_language: str,
    revision_instruction: str,
    parent_candidate_digest: str,
    schema_digest: str,
    dispatch_id: str,
) -> str:
    source_scope = m6_source_canonical_scope(source_text)
    canonical_clause = "\n".join(
        [
            f"- canonical characters（必须逐字保留且不得增删）: {_join_names(source_scope['characters'])}",
            f"- canonical scenes（必须逐字保留且不得改名）: {_join_names(source_scope['scenes'])}",
            f"- canonical props（仅这些可作为 prop；不得把特写/参考/风格写进 prop）: {_join_names(source_scope['props'])}",
            f"- production aids from user text（只能作为 closeup/style 等辅助项，不是 canonical prop）: closeups={_join_names(source_scope['closeups'])}; styles={_join_names(source_scope['styles'])}",
        ]
    )
    revision_clause = (
        f"这是第二轮或后续修订。上一轮候选谱系校验码: {parent_candidate_digest}。"
        f"该校验码只用于系统确认本次调用引用上一轮，不得写入标题、剧本文本、镜头目的、资产名称或任何创作字段；只针对反馈修复：{revision_instruction}"
        if parent_candidate_digest or revision_instruction
        else "这是第一轮真实创作扩写。必须建立可审查的专业剧本、动态拆镜和资产一致性表。"
    )
    return f"""
你是 AFS 服务器本地 Codex LLM，负责影视制作的结构化剧本规划。只输出符合 schema 的 zh-CN JSON。
项目: {project_id}
输入类型: {source_kind}
请求语言: {requested_language}
dispatch_id: {dispatch_id}
schema_digest: {schema_digest}
修订要求: {revision_clause}

	硬性合同:
	- 写一个精炼但完整的专业影视剧本规划；draft_text 至少 260 个中文字符，但不要扩展成长文。
	- 用户 canonical identity 是最高权威。下列名称必须按原文逐字保留，不能翻译、改名、替换、合并、补别名或提升模型自创名称：
	{canonical_clause}
	- 角色必须有目标、冲突、关系、变化、外观、服装、年龄、比例、标志特征、禁止变化项；用户 canonical 名称保留原始字符和语言，新生成的非 canonical 名称与创作说明使用中文，不得用英文单词加数字的占位名。
	- 禁止把字段写成“占位”“说明”“待定”“无”“未知”或只有标点；必须从用户文本中生成具体角色、场景、道具、特写和关系。
- 场景必须有空间、时间、光线、季节、连续性、动作、节奏、情绪、视觉表达、对白或声音。
- 镜头 3 到 7 个，数量和时长由内容决定；禁止固定 4x15、10x6、固定镜头数或关键词模板。
- 单个镜头 duration_seconds 必须在 3 到 18 秒之间，总时长保持可执行；不要把一个复杂动作塞进超长单镜头。
- 每镜头必须有景别、机位、运动、调度、声音、转场、叙事目的、内容驱动时长理由。
- scene_index、character_indexes、asset_indexes 全部从一开始编号，最小值是 1，绝不能输出 0。
	- assets 必须包含每一个用户 canonical prop，kind 只能为 prop，名称必须逐字等于 canonical props；如用户没有 canonical prop，不得自创 prop。
	- closeup、reference_set、style 只能作为 production aid；它们可以补充制作判断，但不得伪装成 prop，不得增加 canonical 角色/场景/道具数量。
	- asset_indexes 必须引用 assets 数组中真实存在的 1-based 序号，不得越界。
- 必须覆盖权利边界、时间/摘要闭环、关系深度、制片可执行性；禁止媒体兜底或图片/视频承诺。
- 除用户 canonical 名称、原文引述和 schema 代码值外，所有新生成的创作说明用中文；不得翻译、音译或改写 canonical 名称。
- 输出完整闭合 JSON；不要 markdown、解释、路径、登录信息或原始元数据。

用户想法或已有剧本:
{source_text}
""".strip()[:11500]


def _candidate_from_provider_payload(
    *,
    project_id: str,
    body: Mapping[str, Any],
    payload: Mapping[str, Any],
    source_digest: str,
    dispatch_id: str,
    schema_digest: str,
    prompt_chars: int,
    parent_candidate_digest: str,
    revision_instruction: str,
) -> dict[str, Any]:
    if payload.get("language") != "zh-CN":
        raise M6PlanningError("server_codex output must use zh-CN", validator_code="output_language_mismatch")
    project_key = _safe_token(project_id)
    candidate_key = source_digest[:12]
    revision_number = 2 if parent_candidate_digest else 1
    revision_id = f"{project_key}-m6-codex-revision-{revision_number}-{candidate_key}"
    characters = [
        {
            "character_id": f"{project_key}-m6-character-{index}-{candidate_key}",
            "aliases": [],
            "source_evidence_refs": [{"source_kind": "server_codex_structured_output", "source_id": dispatch_id, "quote": _text(row.get("goal"))[:180]}],
            **_copy_required(row, ("display_name", "goal", "conflict", "relationship_arc", "change_vector", "appearance", "wardrobe", "age_range", "proportion", "signature_features", "do_not_change")),
        }
        for index, row in enumerate(_rows(payload, "characters"), start=1)
    ]
    scenes = [
        {
            "scene_id": f"{project_key}-m6-scene-{index}-{candidate_key}",
            "lineage": [revision_id],
            "dialogue_refs": list(row.get("dialogue_or_sound") or [])[:8],
            "source_evidence_refs": [{"source_kind": "server_codex_structured_output", "source_id": dispatch_id, "quote": _text(row.get("action"))[:180]}],
            **_copy_required(row, ("name", "space", "time_of_day", "lighting", "season", "continuity", "action", "rhythm", "emotion", "visual_expression", "do_not_change")),
        }
        for index, row in enumerate(_rows(payload, "scenes"), start=1)
    ]
    assets = [
        {
            "asset_id": f"{project_key}-m6-{_safe_token(str(row.get('kind') or 'asset'))}-{index}-{candidate_key}",
            "source_digest": source_digest,
            **_copy_required(row, ("name", "kind", "source", "version", "applicable_scope", "confidence", "rights_boundary", "style", "do_not_change")),
            **m6_asset_scope_fields(str(row.get("kind") or "")),
        }
        for index, row in enumerate(_rows(payload, "assets"), start=1)
    ]
    if not any(row["kind"] == "reference_set" for row in assets):
        raise M6PlanningError(
            "server_codex output must include at least one ReferenceSet asset",
            validator_code="production_aid_reference_set_missing",
        )
    shots = []
    for index, row in enumerate(_rows(payload, "shots"), start=1):
        scene = _by_one_based_index(scenes, int(row.get("scene_index") or 0), "scene_index")
        character_refs = [_by_one_based_index(characters, int(item), "character_indexes")["character_id"] for item in row.get("character_indexes") or []]
        asset_refs = [_by_one_based_index(assets, int(item), "asset_indexes")["asset_id"] for item in row.get("asset_indexes") or []]
        shots.append({
            "shot_id": f"{project_key}-m6-shot-{index}-{candidate_key}",
            "scene_id": scene["scene_id"],
            "character_refs": character_refs,
            "asset_refs": asset_refs,
            "source_evidence_refs": [{"source_kind": "script_revision", "source_id": revision_id, "quote": _text(row.get("intent"))[:220]}],
            **_copy_required(row, ("duration_seconds", "intent", "shot_size", "camera_angle", "camera_movement", "blocking", "sound", "transition", "narrative_purpose", "content_driven_duration_reason")),
        })
    durations = [round(float(row.get("duration_seconds") or 0), 2) for row in shots]
    timing_contract = _source_timing_contract(_text(body.get("source_text")))
    _validate_source_timing_contract(shots, timing_contract)
    structure = dict(payload.get("structure") or {})
    output_chars = len(str(payload))
    scope_review = build_m6_scope_review(
        source_text=_text(body.get("source_text")),
        characters=characters,
        scenes=scenes,
        assets=assets,
        shots=shots,
    )
    if scope_review.get("fail_closed", {}).get("status") != "pass":
        fail_closed = scope_review.get("fail_closed") or {}
        reasons = ", ".join(fail_closed.get("reasons") or ["canonical_scope_drift"])
        raise M6PlanningError(
            f"server_codex canonical scope drift failed closed: {reasons}",
            validator_code="canonical_scope_drift",
        )
    candidate = {
        "schema_version": FILM_SCHEMA_VERSION,
        "m6_schema_version": M6_SCHEMA_VERSION,
        "trusted_candidate": True,
        "source_digest": source_digest,
        "provider_dispatch_count": 1,
        "cost_usd": 0,
        "provider_lineage": {
            "service_id": SERVER_CODEX_SERVICE_ID,
            "provider": "codex_local",
            "model": "gpt-5.5",
            "model_surface": "server-codex-login",
            "dispatch_id": dispatch_id,
            "request_id": dispatch_id,
            "structured_output_contract_id": SERVER_CODEX_CONTRACT_ID,
            "structured_output_schema_digest": schema_digest,
            "provider_calls_started": True,
            "provider_raw_response_stored": False,
            "external_paid_cost_usd": 0,
            "usage": {
                "source": "estimated_from_safe_prompt_and_payload_chars",
                "prompt_chars": prompt_chars,
                "output_chars": output_chars,
                "estimated_input_tokens": max(1, round(prompt_chars / 3.3)),
                "estimated_output_tokens": max(1, round(output_chars / 3.3)),
                "provider_reported_tokens": False,
                "external_paid_cost_usd": 0,
            },
        },
        "brief": {
            "brief_id": f"{project_key}-m6-brief-{candidate_key}",
            "source_kind": body.get("source_kind") or "idea",
            "title": _text(payload.get("title"))[:120],
            "logline": _text(payload.get("logline")),
            "professional_contract": {
                "requires_named_characters": True,
                "requires_conflict_relationship_change": True,
                "requires_scene_time_place_action_dialogue": True,
                "requires_rhythm_emotion_visual_expression": True,
            },
            "lineage": {
                "source_digest": source_digest,
                "parent_candidate_digest": parent_candidate_digest,
                "revision_instruction": revision_instruction,
                "provider_dispatch_id": dispatch_id,
            },
        },
        "script_revision": {
            "revision_id": revision_id,
            "revision_number": revision_number,
            "source_digest": source_digest,
            "parent_candidate_digest": parent_candidate_digest,
            "draft_text": _text(payload.get("draft_text")),
            "revision_instruction": revision_instruction,
            "revision_notes": _text(payload.get("revision_notes")),
            "structure": {
                "sequence_count": int(structure.get("sequence_count") or 1),
                "scene_count": len(scenes),
                "beat_count": len(shots),
                "turning_points": list(structure.get("turning_points") or [])[:8],
                "rhythm_strategy": _text(structure.get("rhythm_strategy")),
                "rights_time_summary": _text(structure.get("rights_time_summary")),
            },
            "script_contract": {
                "named_character_count": len(characters),
                "scene_count": len(scenes),
                "has_dialogue_or_sound_design": True,
                "lineage_state": "server_codex_candidate_pending_confirmation",
            },
        },
        "sequence": {
            "sequence_id": f"{project_key}-m6-sequence-{candidate_key}",
            "name": f"{_text(payload.get('title'))[:96] or '未命名制作方案'} · 制作序列",
            "target_duration_seconds": round(sum(durations), 2),
            "dynamic_policy": {
                "shot_count_decided_by_content": True,
                "source_segment_count": len(shots),
                "fixed_profile_forbidden": ["4x15", "4×15", "10x6", "10×6", "fixed_shot_count"],
                "source_timing_contract": timing_contract,
            },
        },
        "characters": characters,
        "scenes": scenes,
        "assets": assets,
        "shots": shots,
        "asset_bible": {
            "status": "pending_confirmation",
            "character_refs": [row["character_id"] for row in characters],
            "scene_refs": [row["scene_id"] for row in scenes],
            "prop_refs": [row["asset_id"] for row in assets if row["kind"] == "prop"],
            "closeup_refs": [row["asset_id"] for row in assets if row["kind"] == "closeup"],
            "reference_set_refs": [row["asset_id"] for row in assets if row["kind"] == "reference_set"],
            "style_refs": [row["asset_id"] for row in assets if row["kind"] == "style"],
            "production_aid_refs": [row["asset_id"] for row in assets if row["kind"] in PRODUCTION_AID_KINDS],
            "continuity_policy": "creator_confirmed_before_any_media_provider_dispatch",
        },
        "m6_scope_review": scope_review,
        "knowledge_context": _knowledge_context(source_digest),
        "review_requirements": _review_requirements(),
        "issue_ledger": {
            "schema_version": "afs.m6.issue_ledger.v0.1",
            "status": "open_pending_strict_m6_1_review",
            "findings": [],
            "residual_risk": ["server_codex_text_planning_is_not_image_or_video_media_qa"],
        },
        "delivery_id": f"{project_key}-m6-delivery-{candidate_key}",
        "timeline_refs": [f"timeline:m6:server_codex:{candidate_key}"],
        "rights_refs": ["rights:project-original-or-user-supplied-pending-confirmation"],
    }
    return candidate


def _rows(value: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    rows = value.get(key)
    if not isinstance(rows, list) or not rows:
        raise M6PlanningError(
            f"server_codex output missing {key}",
            validator_code=f"provider_missing_{_safe_token(key)}",
        )
    return [row for row in rows if isinstance(row, Mapping)]


def _copy_required(row: Mapping[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    copied = {}
    for key in keys:
        if key not in row:
            raise M6PlanningError(
                f"server_codex output missing {key}",
                validator_code=f"provider_missing_{_safe_token(key)}",
            )
        copied[key] = row[key]
    return copied


def _by_one_based_index(rows: list[dict[str, Any]], index: int, field: str) -> dict[str, Any]:
    if index < 1 or index > len(rows):
        raise M6PlanningError(
            f"server_codex output has unresolved {field}: {index}",
            validator_code=f"provider_unresolved_{_safe_token(field)}",
        )
    return rows[index - 1]


def _source_timing_contract(source_text: str) -> dict[str, Any]:
    shot_counts: set[int] = set()
    for pattern in (
        r"(?:规划|安排|拆分|生成|制作|共|总共)?\s*(?<!第)(\d{1,2})\s*(?:个|支|段)?\s*(?:连续)?\s*(?:镜头|分镜)",
        r"(?:plan|create|use|with|total(?:ling)?)?\s*(\d{1,2})\s*(?:continuous\s+)?shots?\b",
    ):
        for match in re.finditer(pattern, source_text, flags=re.I):
            if re.search(r"第\s*$", source_text[:match.start(1)]):
                continue
            count = int(match.group(1))
            if count > 0:
                shot_counts.add(count)
    shot_counts = sorted(shot_counts)
    if len(shot_counts) > 1:
        raise M6PlanningError(
            "source declares conflicting shot counts",
            validator_code="source_shot_count_ambiguous",
        )
    duration_matches = []
    for pattern in (
        r"(?:总时长|总长度|成片时长)\s*(约|大约|大概|近|approximately|about|around)?\s*(\d+(?:\.\d+)?)\s*(?:秒|s\b|seconds?\b)",
        r"(?:total\s+duration)\s*(?:is|of|:)?\s*(approximately|about|around)?\s*(\d+(?:\.\d+)?)\s*(?:s\b|seconds?\b)",
    ):
        duration_matches.extend(re.findall(pattern, source_text, flags=re.I))
    duration_values = sorted({round(float(value), 2) for _, value in duration_matches if float(value) > 0})
    if len(duration_values) > 1:
        raise M6PlanningError(
            "source declares conflicting total durations",
            validator_code="source_total_duration_ambiguous",
        )
    target_duration = duration_values[0] if duration_values else None
    approximate = any(bool(marker) for marker, _ in duration_matches)
    tolerance = round(max(1.0, target_duration * 0.1), 2) if target_duration and approximate else 0.25 if target_duration else None
    return {
        "source_authority": "user_supplied_timing_scope",
        "requested_shot_count": shot_counts[0] if shot_counts else None,
        "requested_total_duration_seconds": target_duration,
        "duration_tolerance_seconds": tolerance,
        "approximate_total_duration": bool(target_duration and approximate),
    }
def _validate_source_timing_contract(shots: list[dict[str, Any]], contract: Mapping[str, Any]) -> None:
    requested_count = contract.get("requested_shot_count")
    if requested_count is not None and len(shots) != int(requested_count):
        raise M6PlanningError(
            f"server_codex output shot count does not match source: expected {requested_count}, received {len(shots)}",
            validator_code="source_shot_count_mismatch",
        )
    durations = [round(float(shot.get("duration_seconds") or 0), 2) for shot in shots]
    if any(duration < 3 or duration > 18 for duration in durations):
        raise M6PlanningError(
            "server_codex output contains a shot duration outside the 3-18 second planning range",
            validator_code="shot_duration_out_of_range",
        )
    requested_total = contract.get("requested_total_duration_seconds")
    if requested_total is None:
        return
    actual_total = round(sum(durations), 2)
    tolerance = float(contract.get("duration_tolerance_seconds") or 0)
    if abs(actual_total - float(requested_total)) > tolerance:
        raise M6PlanningError(
            f"server_codex output total duration does not match source: expected {requested_total}, received {actual_total}",
            validator_code="source_total_duration_mismatch",
        )


def _text(value: Any) -> str:
    return str(value or "").strip()


def _join_names(values: list[str]) -> str:
    return "、".join(value for value in values if value) or "（无）"


__all__ = (
    "SERVER_CODEX_CONTRACT_ID",
    "build_m6_server_codex_script_plan_asset_bible",
    "m6_server_codex_output_schema",
    "server_codex_m6_enabled",
)
