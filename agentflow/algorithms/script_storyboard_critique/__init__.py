from __future__ import annotations

import re
from typing import Any

from agentflow.algorithms.structured_source_output_qa_checklist._safety import (
    dicts as _dicts,
    has_unsafe_payload as _has_unsafe_payload,
    safe_note as _safe_note,
    safe_token as _safe_token,
)


ALGORITHM_ID = "afs.script_storyboard_critique.v0.1"
ARTIFACT_TYPE = "agentflow_script_storyboard_critique"
SCHEMA_VERSION = "0.1.0"
INPUT_CONTRACT = "user intent, script text, structured shots, and candidate asset graph"
OUTPUT_CONTRACT = "deterministic critique packet for script form, primary asset salience, and storyboard grounding"
EVIDENCE_BOUNDARY = "structure critique only; no provider call, runtime action, generated-media QA, memory write, or human acceptance"
FAILURE_MODES = (
    "script_prompt_like_not_script",
    "primary_assets_missing_from_storyboard",
    "secondary_assets_over_selected",
    "shot_missing_source_grounding",
    "shot_missing_primary_asset_refs",
    "unsafe_structured_payload",
)
NON_CLAIMS = [
    "no provider call or provider smoke",
    "no generated media claim",
    "no runtime verification",
    "no human creative acceptance",
    "no business validation",
    "no durable memory promotion",
    "no Company OS or company KB write",
    "repair suggestions require review before promotion",
]

KNOWN_CHARACTER_NAMES = (
    "唐僧",
    "玄奘",
    "孙悟空",
    "悟空",
    "猪八戒",
    "八戒",
    "沙僧",
    "白骨精",
    "牛魔王",
    "红孩儿",
    "观音",
    "如来",
)
PROMPT_MARKERS = (
    "请生成",
    "生成一个",
    "生成一段",
    "提示词",
    "prompt",
    "negative prompt",
    "画面要求",
    "镜头描述",
    "风格",
    "需要包含",
    "要求如下",
)
SCRIPT_MARKERS_RE = re.compile(r"([\u4e00-\u9fffA-Za-z0-9_]{1,12})\s*[：:]|[“”\"']")
RELATION_RE = re.compile(r"([\u4e00-\u9fff]{2,6})(娶了|大战|遇见|追击|救下|对峙|背叛|保护|寻找|和|与|跟)([\u4e00-\u9fff]{2,6})")


def build_script_storyboard_critique(
    *,
    project_id: str,
    node_id: str | None = None,
    user_request: str = "",
    script_text: str = "",
    shots: list[dict[str, Any]] | None = None,
    asset_graph: dict[str, Any] | None = None,
) -> dict[str, Any]:
    shot_items = _dicts(shots)
    graph = asset_graph if isinstance(asset_graph, dict) else {}
    if _has_unsafe_payload({"shots": shot_items, "asset_graph": graph}):
        return _blocked_packet(project_id, node_id)

    salience = _asset_salience(user_request=user_request, script_text=script_text, shots=shot_items, asset_graph=graph)
    primary_assets = _primary_assets(salience)
    present_labels = _present_asset_labels(shot_items, graph)
    missing_primary = [item for item in primary_assets if item["label"] not in present_labels]
    issues = [
        *_script_form_issues(script_text),
        *_asset_salience_issues(primary_assets, missing_primary, present_labels),
        *_shot_grounding_issues(shot_items, primary_assets),
    ]
    suggestions = _repair_suggestions(issues, missing_primary)
    critical_or_major = [item for item in issues if item["severity"] in {"critical", "major"}]
    packet_state = "needs_repair" if critical_or_major else "critique_ready_needs_human_review"
    return {
        "artifact_type": ARTIFACT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "algorithm_id": ALGORITHM_ID,
        "project_id": _safe_token(project_id),
        "node_id": _safe_token(node_id),
        "packet_state": packet_state,
        "summary": {
            "issue_count": len(issues),
            "critical_or_major_issue_count": len(critical_or_major),
            "primary_asset_count": len(primary_assets),
            "missing_primary_asset_count": len(missing_primary),
            "shot_count": len(shot_items),
            "provider_calls_started": False,
            "generated_media_claimed": False,
            "human_review_needed": True,
            "writes_long_term_memory": False,
            "writes_company_kb": False,
        },
        "script_form": _script_form_report(script_text),
        "asset_salience": salience,
        "expected_primary_assets": primary_assets,
        "missing_primary_assets": missing_primary,
        "issues": issues,
        "repair_suggestions": suggestions,
        "safety_boundary": _audit(),
        "provider_calls_started": False,
        "generated_media_claimed": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": NON_CLAIMS,
    }


def _blocked_packet(project_id: str, node_id: str | None) -> dict[str, Any]:
    return {
        "artifact_type": ARTIFACT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "algorithm_id": ALGORITHM_ID,
        "project_id": _safe_token(project_id),
        "node_id": _safe_token(node_id),
        "packet_state": "blocked_unsafe",
        "summary": {
            "issue_count": 1,
            "critical_or_major_issue_count": 1,
            "primary_asset_count": 0,
            "missing_primary_asset_count": 0,
            "shot_count": 0,
            **_audit(),
            "human_review_needed": True,
        },
        "script_form": {},
        "asset_salience": [],
        "expected_primary_assets": [],
        "missing_primary_assets": [],
        "issues": [
            {
                "id": "unsafe_structured_payload",
                "severity": "critical",
                "message": "structured storyboard or asset graph input contains unsafe raw provider, media, secret, URL, or local path fields",
                "evidence": {},
            }
        ],
        "repair_suggestions": [],
        "safety_boundary": _audit(),
        "provider_calls_started": False,
        "generated_media_claimed": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": NON_CLAIMS,
    }


def _script_form_report(script_text: str) -> dict[str, Any]:
    text = str(script_text or "")
    lower = text.lower()
    prompt_hits = [marker for marker in PROMPT_MARKERS if marker in lower or marker in text]
    script_marker_count = len(SCRIPT_MARKERS_RE.findall(text))
    line_count = len([line for line in text.splitlines() if line.strip()])
    prompt_like = len(prompt_hits) >= 2 and script_marker_count < 2 and line_count <= 4
    return {
        "prompt_marker_count": len(prompt_hits),
        "prompt_markers": prompt_hits[:8],
        "script_marker_count": script_marker_count,
        "line_count": line_count,
        "prompt_like_not_script": prompt_like,
    }


def _script_form_issues(script_text: str) -> list[dict[str, Any]]:
    report = _script_form_report(script_text)
    if not report["prompt_like_not_script"]:
        return []
    return [
        {
            "id": "script_prompt_like_not_script",
            "severity": "major",
            "message": "script text reads like generation instructions instead of executable story/script material",
            "evidence": {
                "prompt_markers": report["prompt_markers"],
                "script_marker_count": report["script_marker_count"],
            },
        }
    ]


def _asset_salience(
    *,
    user_request: str,
    script_text: str,
    shots: list[dict[str, Any]],
    asset_graph: dict[str, Any],
) -> list[dict[str, Any]]:
    request = str(user_request or "")
    script = str(script_text or "")
    shot_text = " ".join(_source_text(shot) for shot in shots)
    combined = f"{request}\n{script}\n{shot_text}"
    graph_labels = _graph_asset_labels(asset_graph)
    labels = _candidate_labels(request, script, shot_text, graph_labels)
    ranked: list[dict[str, Any]] = []
    relation_focus = _relation_focus_labels(f"{request}\n{script}")
    speaker_labels = _speaker_labels(script)
    for label in labels:
        frequency = combined.count(label)
        request_frequency = request.count(label)
        script_frequency = script.count(label)
        score = frequency * 2
        if request_frequency:
            score += 8
        if label in script[:80]:
            score += 3
        if label in relation_focus:
            score += 5
        if label in speaker_labels:
            score += 3
        if label in graph_labels:
            score += 1
        if frequency == 0 and label in graph_labels:
            score = 1
        ranked.append(
            {
                "label": label,
                "asset_type": "character",
                "score": score,
                "frequency": frequency,
                "request_frequency": request_frequency,
                "script_frequency": script_frequency,
                "relation_focus": label in relation_focus,
                "dialogue_speaker": label in speaker_labels,
                "present_in_asset_graph": label in graph_labels,
                "evidence_preview": _safe_note(_first_evidence(combined, label)),
            }
        )
    ranked.sort(key=lambda item: (-int(item["score"]), -int(item["request_frequency"]), combined.find(str(item["label"]))))
    return [{**item, "rank": index + 1} for index, item in enumerate(ranked[:12])]


def _candidate_labels(request: str, script: str, shot_text: str, graph_labels: set[str]) -> list[str]:
    text = f"{request}\n{script}\n{shot_text}"
    labels: list[str] = []
    for label in KNOWN_CHARACTER_NAMES:
        if label in text or label in graph_labels:
            _append(labels, label)
    for label in _relation_focus_labels(text):
        _append(labels, label)
    for label in _speaker_labels(script):
        _append(labels, label)
    for label in re.findall(r"@([\u4e00-\u9fffA-Za-z0-9_]{2,16})", text):
        _append(labels, label)
    for label in sorted(graph_labels):
        _append(labels, label)
    return labels


def _relation_focus_labels(text: str) -> set[str]:
    labels: set[str] = set()
    for left, _verb, right in RELATION_RE.findall(text):
        for raw in (left, right):
            label = _trim_relation_label(raw)
            if label:
                labels.add(label)
    return labels


def _speaker_labels(text: str) -> set[str]:
    labels: set[str] = set()
    for match in re.finditer(r"^\s*([\u4e00-\u9fffA-Za-z0-9_]{1,12})\s*[：:]", text, flags=re.M):
        label = _trim_relation_label(match.group(1))
        if label:
            labels.add(label)
    return labels


def _trim_relation_label(value: str) -> str:
    text = re.sub(r"^(把|让|当|和|与|跟|在|由|将)", "", str(value or "")).strip()
    text = re.sub(r"(改成|写成|剧本|短剧|分镜|故事|时候|之后|之前|一起).*$", "", text).strip()
    for label in KNOWN_CHARACTER_NAMES:
        if label in text:
            return label
    return text if 2 <= len(text) <= 6 and not _looks_generic_label(text) else ""


def _looks_generic_label(value: str) -> bool:
    return value in {"故事", "剧本", "分镜", "镜头", "角色", "人物", "场景", "画面", "用户", "主角"}


def _primary_assets(salience: list[dict[str, Any]]) -> list[dict[str, Any]]:
    primary: list[dict[str, Any]] = []
    for item in salience:
        if item["score"] >= 8 or item["relation_focus"] or item["request_frequency"]:
            primary.append(item)
        if len(primary) >= 4:
            break
    return primary


def _asset_salience_issues(
    primary_assets: list[dict[str, Any]],
    missing_primary: list[dict[str, Any]],
    present_labels: set[str],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if missing_primary:
        issues.append(
            {
                "id": "primary_assets_missing_from_storyboard",
                "severity": "critical",
                "message": "high-salience story assets from the request or script are absent from storyboard asset references",
                "evidence": {
                    "missing_labels": [item["label"] for item in missing_primary],
                    "present_labels": sorted(present_labels),
                },
            }
        )
    if primary_assets and present_labels and not any(item["label"] in present_labels for item in primary_assets):
        issues.append(
            {
                "id": "secondary_assets_over_selected",
                "severity": "major",
                "message": "asset graph contains secondary assets while all primary story assets are missing",
                "evidence": {"expected_primary_labels": [item["label"] for item in primary_assets], "present_labels": sorted(present_labels)},
            }
        )
    return issues


def _shot_grounding_issues(shots: list[dict[str, Any]], primary_assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    missing_source_ids = [_shot_id(shot, index) for index, shot in enumerate(shots, start=1) if not _source_text(shot)]
    issues: list[dict[str, Any]] = []
    if missing_source_ids:
        issues.append(
            {
                "id": "shot_missing_source_grounding",
                "severity": "major",
                "message": "one or more storyboard shots lack source_span.text or source_text evidence",
                "evidence": {"shot_ids": missing_source_ids[:24]},
            }
        )
    primary_labels = {str(item["label"]) for item in primary_assets}
    missing_ref_ids: list[str] = []
    for index, shot in enumerate(shots, start=1):
        source = _source_text(shot)
        if not source or not any(label in source for label in primary_labels):
            continue
        ref_labels = {str(ref.get("label") or ref.get("display_name") or "") for ref in _dicts(shot.get("asset_refs"))}
        if not (primary_labels & ref_labels):
            missing_ref_ids.append(_shot_id(shot, index))
    if missing_ref_ids:
        issues.append(
            {
                "id": "shot_missing_primary_asset_refs",
                "severity": "major",
                "message": "shots mentioning primary story assets do not link those assets in asset_refs",
                "evidence": {"shot_ids": missing_ref_ids[:24], "primary_labels": sorted(primary_labels)},
            }
        )
    return issues


def _repair_suggestions(issues: list[dict[str, Any]], missing_primary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    issue_ids = {str(issue.get("id") or "") for issue in issues}
    for asset in missing_primary:
        suggestions.append(
            {
                "action": "add_candidate_asset_ref",
                "target_label": asset["label"],
                "asset_type": asset["asset_type"],
                "reason": "primary story asset is absent from storyboard asset graph",
                "review_required": True,
            }
        )
    if "script_prompt_like_not_script" in issue_ids:
        suggestions.append(
            {
                "action": "rewrite_as_story_script_before_storyboard",
                "reason": "storyboard breakdown needs narrative or dialogue source, not only generation instructions",
                "review_required": True,
            }
        )
    if "shot_missing_source_grounding" in issue_ids:
        suggestions.append(
            {
                "action": "restore_source_span_text",
                "reason": "each shot must point back to script source evidence before media generation",
                "review_required": True,
            }
        )
    if "shot_missing_primary_asset_refs" in issue_ids:
        suggestions.append(
            {
                "action": "link_primary_assets_to_mentioning_shots",
                "reason": "shots that mention primary assets need explicit asset_refs for continuity",
                "review_required": True,
            }
        )
    return suggestions


def _present_asset_labels(shots: list[dict[str, Any]], asset_graph: dict[str, Any]) -> set[str]:
    labels = set(_graph_asset_labels(asset_graph))
    for shot in shots:
        for ref in _dicts(shot.get("asset_refs")):
            label = str(ref.get("label") or ref.get("display_name") or "").strip()
            if label:
                labels.add(label)
    return labels


def _graph_asset_labels(asset_graph: dict[str, Any]) -> set[str]:
    labels: set[str] = set()
    for asset in _dicts(asset_graph.get("assets")):
        label = str(asset.get("label") or asset.get("display_name") or "").strip()
        asset_type = str(asset.get("asset_type") or "").strip()
        if label and asset_type in {"", "character"}:
            labels.add(label)
    return labels


def _first_evidence(text: str, label: str) -> str:
    for sentence in re.split(r"(?<=[。！？!?])\s*", str(text or "")):
        if label and label in sentence:
            return sentence[:160]
    return ""


def _source_text(shot: dict[str, Any]) -> str:
    span = shot.get("source_span") if isinstance(shot.get("source_span"), dict) else {}
    return str(span.get("text") or shot.get("source_text") or "").strip()


def _shot_id(shot: dict[str, Any], index: int) -> str:
    return _safe_token(shot.get("shot_id") or shot.get("index") or f"shot_{index:02d}") or f"shot_{index:02d}"


def _append(labels: list[str], label: str) -> None:
    clean = str(label or "").strip()
    if clean and clean not in labels and not _looks_generic_label(clean):
        labels.append(clean[:24])


def _audit() -> dict[str, bool]:
    return {
        "provider_calls_started": False,
        "generated_media_claimed": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }


__all__ = (
    "ALGORITHM_ID",
    "ARTIFACT_TYPE",
    "EVIDENCE_BOUNDARY",
    "FAILURE_MODES",
    "INPUT_CONTRACT",
    "NON_CLAIMS",
    "OUTPUT_CONTRACT",
    "SCHEMA_VERSION",
    "build_script_storyboard_critique",
)
