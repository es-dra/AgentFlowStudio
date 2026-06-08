from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from agentflow_studio.harness.quality_profiles import AGENTFLOW_PRODUCTION_HANDOFF_PROFILE
from agentflow_studio.production import (
    CostQualityTrace,
    CreativeBrief,
    EpisodeOutline,
    FeedbackSignalLog,
    MemoryCandidateStore,
    ProductionHandoff,
    PromptPack,
    ScenePlan,
    ShotPlan,
    StoryBible,
)


REQUIRED_ARTIFACTS = [
    "creative_brief.json",
    "story_bible.json",
    "episode_outline.json",
    "scene_plan.json",
    "shot_plan.json",
    "prompt_pack.json",
    "production_handoff.json",
    "production_report.md",
    "memory_candidates.json",
    "cost_quality_trace.json",
    "feedback_signal_log.json",
    "execution_trace.json",
    "trace.json",
    "manifest.json",
    "run_manifest.json",
]

SCHEMA_MODELS = {
    "creative_brief.json": CreativeBrief,
    "story_bible.json": StoryBible,
    "episode_outline.json": EpisodeOutline,
    "scene_plan.json": ScenePlan,
    "shot_plan.json": ShotPlan,
    "prompt_pack.json": PromptPack,
    "production_handoff.json": ProductionHandoff,
    "memory_candidates.json": MemoryCandidateStore,
    "cost_quality_trace.json": CostQualityTrace,
    "feedback_signal_log.json": FeedbackSignalLog,
}


def agentflow_production_artifacts_to_inspect() -> list[str]:
    return list(REQUIRED_ARTIFACTS)


def build_agentflow_production_quality_report(root: str | Path) -> dict[str, Any]:
    run_dir = Path(root)
    checks: list[dict[str, Any]] = []
    artifacts = {name: _read_json_object(run_dir / name) for name in REQUIRED_ARTIFACTS if name.endswith(".json")}

    for artifact in REQUIRED_ARTIFACTS:
        _add_file_check(run_dir / artifact, f"agentflow_production_{_check_name(artifact)}_exists", checks)

    _add_json_parse_checks(run_dir, checks)
    _add_schema_checks(artifacts, checks)
    _add_reference_checks(artifacts, checks)
    _add_report_checks(run_dir, artifacts, checks)
    _add_auxiliary_checks(artifacts, checks)

    failed = [check for check in checks if check["status"] == "fail"]
    return {
        "status": "fail" if failed else "pass",
        "checks": checks,
        "warnings": [],
        "errors": [_check_error(check) for check in failed],
        "summary": {
            "quality_profile": AGENTFLOW_PRODUCTION_HANDOFF_PROFILE,
            "scenes": _count_items(artifacts.get("scene_plan.json"), "scenes"),
            "shots": _count_items(artifacts.get("shot_plan.json"), "shots"),
            "prompts": _count_items(artifacts.get("prompt_pack.json"), "prompts"),
        },
    }


def _add_json_parse_checks(run_dir: Path, checks: list[dict[str, Any]]) -> None:
    for artifact in REQUIRED_ARTIFACTS:
        if not artifact.endswith(".json"):
            continue
        path = run_dir / artifact
        if not path.is_file():
            continue
        _add_check(
            checks,
            f"agentflow_production_{_check_name(artifact)}_json_valid",
            "pass" if _read_json_object(path) is not None else "fail",
        )


def _add_schema_checks(artifacts: dict[str, dict[str, Any] | None], checks: list[dict[str, Any]]) -> None:
    for name, payload in artifacts.items():
        if payload is None:
            continue
        if name in {"manifest.json", "run_manifest.json", "trace.json"}:
            continue
        _add_model_validation_check(name, payload, checks)
        _add_check(
            checks,
            f"agentflow_production_{_check_name(name)}_schema_version",
            "pass" if payload.get("schema_version") == "0.1.0" else "fail",
            {"schema_version": payload.get("schema_version")},
        )


def _add_model_validation_check(name: str, payload: dict[str, Any], checks: list[dict[str, Any]]) -> None:
    model = SCHEMA_MODELS.get(name)
    if model is None:
        return
    try:
        model.model_validate(payload)
    except ValidationError as exc:
        _add_check(
            checks,
            f"agentflow_production_{_check_name(name)}_schema_valid",
            "fail",
            {"error_count": len(exc.errors())},
        )
        return
    _add_check(checks, f"agentflow_production_{_check_name(name)}_schema_valid", "pass")


def _add_reference_checks(artifacts: dict[str, dict[str, Any] | None], checks: list[dict[str, Any]]) -> None:
    brief = artifacts.get("creative_brief.json") or {}
    bible = artifacts.get("story_bible.json") or {}
    outline = artifacts.get("episode_outline.json") or {}
    scene_plan = artifacts.get("scene_plan.json") or {}
    shot_plan = artifacts.get("shot_plan.json") or {}
    prompt_pack = artifacts.get("prompt_pack.json") or {}
    handoff = artifacts.get("production_handoff.json") or {}

    beat_ids = _ids(outline.get("beats"), "beat_id")
    scene_beat_ids = _ids(scene_plan.get("scenes"), "beat_id")
    scene_ids = _ids(scene_plan.get("scenes"), "scene_id")
    shot_scene_ids = _ids(shot_plan.get("shots"), "scene_id")
    shot_ids = _ids(shot_plan.get("shots"), "shot_id")
    prompt_shot_ids = _ids(prompt_pack.get("prompts"), "shot_id")

    _add_check(checks, "agentflow_production_bible_references_brief", "pass" if bible.get("source_brief_id") == brief.get("brief_id") else "fail")
    _add_check(checks, "agentflow_production_outline_references_bible", "pass" if outline.get("story_bible_id") == bible.get("story_bible_id") else "fail")
    _add_check(checks, "agentflow_production_scene_beats_exist", "pass" if scene_beat_ids <= beat_ids and bool(scene_beat_ids) else "fail")
    _add_check(checks, "agentflow_production_outline_beats_covered_by_scenes", "pass" if beat_ids <= scene_beat_ids and bool(beat_ids) else "fail")
    _add_check(checks, "agentflow_production_shot_scenes_exist", "pass" if shot_scene_ids <= scene_ids and bool(shot_scene_ids) else "fail")
    _add_check(checks, "agentflow_production_scenes_covered_by_shots", "pass" if scene_ids <= shot_scene_ids and bool(scene_ids) else "fail")
    _add_check(checks, "agentflow_production_prompt_shots_exist", "pass" if prompt_shot_ids <= shot_ids and bool(prompt_shot_ids) else "fail")
    _add_check(checks, "agentflow_production_shots_covered_by_prompts", "pass" if shot_ids <= prompt_shot_ids and bool(shot_ids) else "fail")
    _add_check(checks, "agentflow_production_handoff_references_prompt_pack", "pass" if handoff.get("prompt_pack_id") == prompt_pack.get("prompt_pack_id") else "fail")
    _add_check(
        checks,
        "agentflow_production_handoff_core_ids_match",
        "pass" if _handoff_core_ids_match(brief, bible, outline, scene_plan, shot_plan, prompt_pack, handoff) else "fail",
    )
    _add_check(
        checks,
        "agentflow_production_handoff_artifact_refs_complete",
        "pass" if _handoff_artifact_refs_complete(handoff) else "fail",
    )


def _add_report_checks(run_dir: Path, artifacts: dict[str, dict[str, Any] | None], checks: list[dict[str, Any]]) -> None:
    path = run_dir / "production_report.md"
    brief = artifacts.get("creative_brief.json") or {}
    project_title = str(brief.get("project_title") or "")
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    status = "pass" if project_title and project_title in text and "Production Handoff" in text and "AgentFlow Production" in text else "fail"
    _add_check(
        checks,
        "agentflow_production_production_report_identity",
        status,
        {"project_title": project_title, "strong_contract_source": False},
    )


def _add_auxiliary_checks(artifacts: dict[str, dict[str, Any] | None], checks: list[dict[str, Any]]) -> None:
    memory = artifacts.get("memory_candidates.json") or {}
    cost = artifacts.get("cost_quality_trace.json") or {}
    feedback = artifacts.get("feedback_signal_log.json") or {}
    candidates = memory.get("candidates") if isinstance(memory.get("candidates"), list) else []
    statuses = {item.get("promotion_status") for item in candidates if isinstance(item, dict)}
    _add_check(checks, "agentflow_production_memory_candidate_only", "pass" if statuses <= {"candidate"} else "fail")
    _add_check(
        checks,
        "agentflow_production_cost_trace_local_deterministic",
        "pass"
        if cost.get("provider") == "local_deterministic"
        and cost.get("execution_mode") == "local_deterministic"
        and cost.get("estimated_cost") == 0
        else "fail",
    )
    _add_check(
        checks,
        "agentflow_production_feedback_signal_derived",
        "pass"
        if feedback.get("source_of_truth") == "feedback.jsonl"
        and feedback.get("is_primary_feedback_store") is False
        else "fail",
    )


def _handoff_core_ids_match(
    brief: dict[str, Any],
    bible: dict[str, Any],
    outline: dict[str, Any],
    scene_plan: dict[str, Any],
    shot_plan: dict[str, Any],
    prompt_pack: dict[str, Any],
    handoff: dict[str, Any],
) -> bool:
    expected = {
        "source_brief_id": brief.get("brief_id"),
        "story_bible_id": bible.get("story_bible_id"),
        "episode_outline_id": outline.get("episode_outline_id"),
        "scene_plan_id": scene_plan.get("scene_plan_id"),
        "shot_plan_id": shot_plan.get("shot_plan_id"),
        "prompt_pack_id": prompt_pack.get("prompt_pack_id"),
    }
    return all(value and handoff.get(key) == value for key, value in expected.items())


def _handoff_artifact_refs_complete(handoff: dict[str, Any]) -> bool:
    refs = handoff.get("artifact_refs")
    if not isinstance(refs, dict):
        return False
    expected = {
        "creative_brief": "creative_brief.json",
        "story_bible": "story_bible.json",
        "episode_outline": "episode_outline.json",
        "scene_plan": "scene_plan.json",
        "shot_plan": "shot_plan.json",
        "prompt_pack": "prompt_pack.json",
    }
    return all(refs.get(key) == value for key, value in expected.items())


def _read_json_object(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _add_file_check(path: Path, name: str, checks: list[dict[str, Any]]) -> None:
    _add_check(checks, name, "pass" if path.is_file() else "fail")


def _add_check(checks: list[dict[str, Any]], name: str, status: str, details: dict[str, Any] | None = None) -> None:
    check: dict[str, Any] = {"name": name, "status": status}
    if details is not None:
        check["details"] = details
    checks.append(check)


def _ids(items: object, key: str) -> set[str]:
    if not isinstance(items, list):
        return set()
    return {str(item[key]) for item in items if isinstance(item, dict) and item.get(key)}


def _count_items(payload: dict[str, Any] | None, key: str) -> int:
    items = payload.get(key) if isinstance(payload, dict) else None
    return len(items) if isinstance(items, list) else 0


def _check_name(filename: str) -> str:
    base = filename.replace(".json", "").replace(".md", "")
    if base == "production_handoff":
        return "handoff"
    return base


def _check_error(check: dict[str, Any]) -> str:
    return f"{check['name']} failed"
