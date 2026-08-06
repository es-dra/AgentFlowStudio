"""Paid remote-LLM indirect-mention proposals for analysis-candidates.

COST WARNING
------------
Unlike AFS_ENABLE_ALIAS_LINK_PROPOSALS and
AFS_ENABLE_SCENE_NAME_NORMALIZATION_PROPOSALS (free deterministic builders),
this path issues real remote LLM chat-completions via the provider registry.

Gates (all required):
  - AFS_ENABLE_INDIRECT_MENTION_LLM_PROPOSALS=true  (default OFF)
  - AFS_ALLOW_REMOTE_LLM=true
  - AFS_PROVIDER_CONFIG pointing at a live LLM service (e.g. prompt_optimizer)

Budget:
  - AFS_INDIRECT_MENTION_LLM_MAX_CALLS (default 12) caps LLM calls per extract.
  - Mentions beyond the budget are returned as budget_skipped_unjudged records
    (never silently dropped).

Authority:
  Proposals are status=candidate / authority=non_authoritative_proposal only.
  Human confirmation uses core-asset command create_manual_character
  (preview → confirm). Extract never writes authoritative character identity.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Callable

from apps.api.runtime_script_indirect_mention_discovery import (
    context_window,
    discover_indirect_mention_candidates,
)
from apps.api.runtime_script_candidate_extraction import _is_person_name

INDIRECT_MENTION_PROPOSALS_ENV = "AFS_ENABLE_INDIRECT_MENTION_LLM_PROPOSALS"
INDIRECT_MENTION_LLM_MAX_CALLS_ENV = "AFS_INDIRECT_MENTION_LLM_MAX_CALLS"
INDIRECT_MENTION_PROPOSAL_SCHEMA_VERSION = "afs.indirect_mention_proposal.v0.1"
DEFAULT_LLM_MAX_CALLS = 12
DEFAULT_SERVICE_ID = "prompt_optimizer"
COST_CLASS_PAID = "paid_remote_llm"

SYSTEM_RULES = """你是剧本理解助手。任务：对给定「疑似提及」分别回答两个独立问题，不要混成一个结论。

重要约束：两个字段都只评价「疑似提及」这个字符串本身，不要把上下文里的其他人物答案套到它头上。

问题 A — refers_to_real_character
  「疑似提及」字符串本身，是否是在指代一个真实的、有身份的、值得追踪的故事人物（姓名/小名/别名）？
  - true：该字符串本身就是（或明显用作）具体人物的姓名/小名/别名，哪怕只出现在回忆、传闻、信件、照片背面、电话、日记转述里。
  - false：该字符串是完整对白、祈使/口号、业务术语、告示/UI、物品标签、地点片段、抽象概念；
    或只是「说给某人听的话」但字符串本身并不是那个人的名字。
    即使上下文里另有真实人物，只要疑似提及本身不是人名/别名，也必须 false。

问题 B — is_present_in_scene
  在这段片段里，该人物（由疑似提及所指）是否有直接出场证据？
  - true：有对白行 speaker、舞台指示中的在场动作/行为、作为出场人物被介绍并在场上活动；
    或在场角色明确承认该称呼就是自己的别名/小名（别名指向在场者）。
  - false：仅被提及、转述、写在物品/信件上、电话里被叫到但未到场；
    或疑似提及根本不是人物（此时本字段必须 false）。

组合含义（供你自检，不要输出组合字段）：
  - 间接提及 ≈ refers_to_real_character=true 且 is_present_in_scene=false
  - 在场角色/在场别名 ≈ 两者皆 true
  - 噪声 ≈ refers_to_real_character=false（此时 is_present_in_scene 也必须 false）

硬规则：
0. 两个问题必须分开判断；不要因为「没出场」就把 refers_to_real_character 打成 false。
1. 先看字符串是不是人名形态/人名用法，再谈是否在场。
2. 不确定时：对应字段取 false，并降低该字段 confidence。
3. 只根据给定片段判断，不要臆造片段外剧情。
4. 只输出一个 JSON 对象，不要 Markdown，不要代码围栏。字段严格为：
   {
     "refers_to_real_character": boolean,
     "refers_to_real_character_confidence": number,
     "refers_to_real_character_reason": string,
     "is_present_in_scene": boolean,
     "is_present_in_scene_confidence": number,
     "is_present_in_scene_reason": string
   }
   confidence 范围 0 到 1；reason 用简短中文，且必须围绕「疑似提及」本身。
"""


JudgeFn = Callable[[str, str, Path], dict[str, Any]]


def indirect_mention_llm_proposals_enabled() -> bool:
    return str(os.getenv(INDIRECT_MENTION_PROPOSALS_ENV, "")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def indirect_mention_llm_max_calls() -> int:
    raw = str(os.getenv(INDIRECT_MENTION_LLM_MAX_CALLS_ENV, "")).strip()
    if not raw:
        return DEFAULT_LLM_MAX_CALLS
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_LLM_MAX_CALLS
    return max(0, min(value, 120))


def build_indirect_mention_proposals(
    source_text: str,
    *,
    judge: JudgeFn | None = None,
    max_calls: int | None = None,
    context_radius: int = 220,
    known_identity_surfaces: set[str] | frozenset[str] | None = None,
) -> dict[str, Any]:
    """Build non-authoritative indirect-mention proposals via paid LLM judgment.

    Returns dict with:
      proposals: list[dict]  (only refers=true & present=false; never for known identities)
      budget_skipped: list[dict]  (discovered but not judged — explicit)
      suppressed_known_identity: list[dict]  (exact match to canonical/alias — not proposed)
      provider_dispatch_count / remote_dispatch_count
      discovered_count / judged_count
      cost_class
    """
    discoveries = discover_indirect_mention_candidates(
        source_text,
        known_identity_surfaces=known_identity_surfaces,
    )
    known = {str(item).strip() for item in (known_identity_surfaces or set()) if str(item).strip()}
    eligible: list[dict[str, Any]] = []
    suppressed_known: list[dict[str, Any]] = []
    for item in discoveries:
        mention = str(item["mention"])
        if bool(item.get("already_extracted_as_character")) or mention in known:
            suppressed_known.append(
                {
                    "mention": mention,
                    "source_span": dict(item.get("source_span") or {}),
                    "status": "suppressed_known_identity",
                    "authority": "non_authoritative_proposal",
                    "cost_class": COST_CLASS_PAID,
                    "reason": (
                        "Mention exactly matches an already extracted character name "
                        "or a known confirmed identity surface; no create_manual_character "
                        "proposal is emitted."
                    ),
                    "discovery_method": item.get("discovery_method"),
                    "discovery_methods": list(item.get("discovery_methods") or []),
                    "already_extracted_as_character": True,
                    "provider_dispatch_count": 0,
                    "remote_dispatch_count": 0,
                }
            )
            continue
        eligible.append(item)

    budget = DEFAULT_LLM_MAX_CALLS if max_calls is None else max(0, min(int(max_calls), 120))
    to_judge = eligible[:budget]
    skipped = eligible[budget:]
    judge_fn = judge or _default_remote_judge

    proposals: list[dict[str, Any]] = []
    dispatch_count = 0
    with tempfile.TemporaryDirectory(prefix="afs-indirect-mention-prod-") as tmp:
        out_root = Path(tmp)
        for index, discovery in enumerate(to_judge, start=1):
            window = context_window(
                source_text,
                int(discovery["start"]),
                int(discovery["end"]),
                radius=context_radius,
            )
            case_dir = out_root / f"{index:02d}"
            case_dir.mkdir(parents=True, exist_ok=True)
            judgment = judge_fn(window, str(discovery["mention"]), case_dir)
            dispatch_count += 1
            if not (
                bool(judgment.get("refers_to_real_character"))
                and not bool(judgment.get("is_present_in_scene"))
            ):
                continue
            # Defense in depth after live e2e: LLM can mark long quoted clauses that
            # merely contain a person name (e.g. 「第七格——顾衡案——…」) as refers=true.
            # Keep only person-name-shaped mentions as proposals.
            if not _is_person_name(str(discovery["mention"])):
                continue
            # Belt-and-suspenders: never emit create_manual_character for known identities.
            if bool(discovery.get("already_extracted_as_character")):
                continue
            proposals.append(_proposal_from_judgment(discovery, judgment, source_text))

    budget_skipped = [
        {
            "mention": item["mention"],
            "source_span": item["source_span"],
            "status": "budget_skipped_unjudged",
            "authority": "non_authoritative_proposal",
            "cost_class": COST_CLASS_PAID,
            "reason": (
                f"Exceeded {INDIRECT_MENTION_LLM_MAX_CALLS_ENV}={budget}; "
                "mention discovered but not LLM-judged."
            ),
            "discovery_method": item.get("discovery_method"),
            "discovery_methods": list(item.get("discovery_methods") or []),
            "already_extracted_as_character": bool(item.get("already_extracted_as_character")),
            "provider_dispatch_count": 0,
            "remote_dispatch_count": 0,
        }
        for item in skipped
    ]
    return {
        "proposals": proposals,
        "budget_skipped": budget_skipped,
        "suppressed_known_identity": suppressed_known,
        "discovered_count": len(discoveries),
        "judged_count": len(to_judge),
        "provider_dispatch_count": dispatch_count,
        "remote_dispatch_count": dispatch_count,
        "cost_class": COST_CLASS_PAID,
        "llm_max_calls": budget,
    }


def parse_judgment(raw_text: str) -> dict[str, Any]:
    text = (raw_text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise
        payload = json.loads(match.group(0))
    if not isinstance(payload, dict):
        raise ValueError("judgment is not an object")
    refers = bool(payload.get("refers_to_real_character"))
    present = bool(payload.get("is_present_in_scene"))
    return {
        "refers_to_real_character": refers,
        "refers_to_real_character_confidence": float(
            payload.get("refers_to_real_character_confidence")
            if payload.get("refers_to_real_character_confidence") is not None
            else 0.0
        ),
        "refers_to_real_character_reason": str(
            payload.get("refers_to_real_character_reason") or ""
        ).strip(),
        "is_present_in_scene": present,
        "is_present_in_scene_confidence": float(
            payload.get("is_present_in_scene_confidence")
            if payload.get("is_present_in_scene_confidence") is not None
            else 0.0
        ),
        "is_present_in_scene_reason": str(payload.get("is_present_in_scene_reason") or "").strip(),
        "is_indirect_mention": bool(refers and not present),
        "raw_text": raw_text,
    }


def build_prompt(text: str, mention: str) -> str:
    return (
        f"{SYSTEM_RULES}\n\n"
        f"疑似提及：{mention}\n\n"
        f"剧本片段：\n---\n{text}\n---\n\n"
        "请只返回 JSON。"
    )


def _default_remote_judge(text: str, mention: str, output_dir: Path) -> dict[str, Any]:
    # Imported lazily so flag-off extract paths never touch provider registry.
    from agentflow_studio.model_gateway.provider_adapter import (
        ProviderDispatchRequest,
        load_provider_registry,
    )

    registry = load_provider_registry()
    result = registry.dispatch(
        "llm",
        DEFAULT_SERVICE_ID,
        ProviderDispatchRequest(
            prompt=build_prompt(text, mention),
            output_dir=output_dir,
            task_type="m3_1_structured_json",
            timeout_sec=60.0,
        ),
    )
    return parse_judgment(str(result.get("text") or ""))


def _proposal_from_judgment(
    discovery: dict[str, Any],
    judgment: dict[str, Any],
    source_text: str,
) -> dict[str, Any]:
    mention = str(discovery["mention"])
    span = dict(discovery["source_span"])
    identity = {
        "schema_version": INDIRECT_MENTION_PROPOSAL_SCHEMA_VERSION,
        "mention": mention,
        "method": "indirect_mention_llm_split_fields",
        "start": span.get("start"),
        "end": span.get("end"),
    }
    return {
        "proposal_id": f"indirectmention_{_sha256_json(identity)[:20]}",
        "schema_version": INDIRECT_MENTION_PROPOSAL_SCHEMA_VERSION,
        "relation_type": "indirect_mention",
        "status": "candidate",
        "authority": "non_authoritative_proposal",
        "mention": mention,
        "refers_to_real_character": True,
        "refers_to_real_character_confidence": float(
            judgment.get("refers_to_real_character_confidence") or 0.0
        ),
        "refers_to_real_character_reason": str(
            judgment.get("refers_to_real_character_reason") or ""
        ),
        "is_present_in_scene": False,
        "is_present_in_scene_confidence": float(
            judgment.get("is_present_in_scene_confidence") or 0.0
        ),
        "is_present_in_scene_reason": str(judgment.get("is_present_in_scene_reason") or ""),
        "is_indirect_mention": True,
        "confidence": float(judgment.get("refers_to_real_character_confidence") or 0.0),
        "evidence_spans": [span],
        "extraction_method": "indirect_mention_llm_split_fields",
        "discovery_method": discovery.get("discovery_method"),
        "review_action": "use_core_asset_command_create_manual_character",
        "cost_class": COST_CLASS_PAID,
        "provider_dispatch_count": 1,
        "remote_dispatch_count": 1,
        "already_extracted_as_character": bool(discovery.get("already_extracted_as_character")),
    }


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


__all__ = (
    "COST_CLASS_PAID",
    "DEFAULT_LLM_MAX_CALLS",
    "INDIRECT_MENTION_LLM_MAX_CALLS_ENV",
    "INDIRECT_MENTION_PROPOSAL_SCHEMA_VERSION",
    "INDIRECT_MENTION_PROPOSALS_ENV",
    "SYSTEM_RULES",
    "build_indirect_mention_proposals",
    "build_prompt",
    "indirect_mention_llm_max_calls",
    "indirect_mention_llm_proposals_enabled",
    "parse_judgment",
)
