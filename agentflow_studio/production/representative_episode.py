from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "afs.representative_episode_preparation.v0.1"
EVIDENCE_LABEL = "representative_episode_preparation_pass"
REQUIRED_ROLES = (
    "screenwriter",
    "storyboard",
    "art",
    "director",
    "continuity",
    "qa",
    "audio",
    "edit",
    "export",
)
PLACEHOLDER_CLASSES = {"solid_color", "metadata_only", "slate", "placeholder"}


class RepresentativeEpisodeError(ValueError):
    pass


@dataclass(frozen=True)
class ValidatedRepresentativeEpisode:
    package: dict[str, Any]
    package_path: Path
    duration_seconds: Decimal
    package_sha256: str


def validate_representative_episode(package_path: str | Path) -> ValidatedRepresentativeEpisode:
    path = Path(package_path).resolve()
    package = _read_json(path)
    if package.get("schema_version") != SCHEMA_VERSION:
        raise RepresentativeEpisodeError("unsupported schema_version")
    if package.get("evidence_label") != EVIDENCE_LABEL:
        raise RepresentativeEpisodeError("invalid evidence label")
    if package.get("provider_calls_started") != 0:
        raise RepresentativeEpisodeError("provider_calls_started must remain zero")
    if package.get("media_generation_status") != "not_started":
        raise RepresentativeEpisodeError("media generation must remain not_started")

    project = _object(package.get("project"), "project")
    for field in ("project_id", "episode_id", "title", "current_version_id"):
        _required_text(project.get(field), f"project.{field}")
    duration = _decimal(project.get("duration_seconds"), "project.duration_seconds")
    if not Decimal("120") <= duration <= Decimal("180"):
        raise RepresentativeEpisodeError("episode duration must be between 120 and 180 seconds")

    brief = _object(package.get("creative_brief"), "creative_brief")
    for field in ("premise", "audience", "hook", "emotional_arc", "commercial_format"):
        _required_text(brief.get(field), f"creative_brief.{field}")

    characters = _indexed(package.get("characters"), "character_id", "characters")
    scenes = _indexed(package.get("scenes"), "scene_id", "scenes")
    shots = _indexed(package.get("shots"), "shot_id", "shots")
    assets = _indexed(package.get("asset_manifest"), "asset_id", "asset_manifest")
    prompts = _indexed(package.get("prompt_lineage"), "prompt_id", "prompt_lineage")
    _validate_versions(characters, "characters")
    _validate_versions(scenes, "scenes")
    _validate_versions(shots, "shots")
    _validate_assets(assets, prompts)
    _validate_timeline(shots, scenes, characters, assets, prompts, duration)
    _validate_subtitles(package.get("subtitle_plan"), shots, duration)
    _validate_audio(package.get("audio_plan"), shots, assets)
    _validate_assembly(package.get("assembly_plan"), shots, assets, duration)
    _validate_quality(package.get("quality_rubric"))
    _validate_crew(package.get("domain_crew_execution_plan"), project, characters, scenes, shots)
    _validate_nonclaims(package.get("non_claims"))
    return ValidatedRepresentativeEpisode(
        package=package,
        package_path=path,
        duration_seconds=duration,
        package_sha256=_sha256(path),
    )


def preparation_evidence(validated: ValidatedRepresentativeEpisode) -> dict[str, Any]:
    package = validated.package
    assets = package["asset_manifest"]
    unavoidable = sorted(
        item["asset_id"] for item in assets
        if item["provider_needed"] and item["status"] == "missing"
    )
    return {
        "schema_version": "afs.representative_episode_preparation_evidence.v0.1",
        "status": "pass",
        "evidence_label": EVIDENCE_LABEL,
        "package_ref": validated.package_path.name,
        "package_sha256": validated.package_sha256,
        "project_id": package["project"]["project_id"],
        "episode_id": package["project"]["episode_id"],
        "duration_seconds": _number(validated.duration_seconds),
        "character_count": len(package["characters"]),
        "scene_count": len(package["scenes"]),
        "shot_count": len(package["shots"]),
        "provider_calls_started": 0,
        "provider_unavoidable_asset_ids": unavoidable,
        "evidence_layers": {
            "episode_preparation_structure": "pass",
            "generated_media": "not_started",
            "creative_media_quality": "not_evaluated",
            "human_acceptance": "not_evaluated",
            "business_validation": "not_evaluated",
            "deploy_release": "not_authorized",
        },
        "non_claims": package["non_claims"],
    }


def write_preparation_evidence(validated: ValidatedRepresentativeEpisode, output_path: str | Path) -> Path:
    destination = Path(output_path).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(preparation_evidence(validated), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return destination


def _validate_versions(records: dict[str, dict[str, Any]], label: str) -> None:
    for ref, record in records.items():
        version = _required_text(record.get("version_id"), f"{ref}.version_id")
        current = _required_text(record.get("current_version_id"), f"{ref}.current_version_id")
        if version != current:
            raise RepresentativeEpisodeError(f"{label} contains stale version: {ref}")


def _validate_assets(assets: dict[str, dict[str, Any]], prompts: dict[str, dict[str, Any]]) -> None:
    if not assets:
        raise RepresentativeEpisodeError("asset_manifest must not be empty")
    for asset_id, asset in assets.items():
        if asset.get("status") not in {"missing", "ready"}:
            raise RepresentativeEpisodeError(f"invalid asset status: {asset_id}")
        if not isinstance(asset.get("provider_needed"), bool):
            raise RepresentativeEpisodeError(f"provider_needed must be boolean: {asset_id}")
        missing = asset["status"] == "missing"
        if bool(asset.get("missing")) != missing:
            raise RepresentativeEpisodeError(f"asset missing flag drift: {asset_id}")
        content_class = _required_text(asset.get("content_class"), f"{asset_id}.content_class")
        if content_class in PLACEHOLDER_CLASSES:
            raise RepresentativeEpisodeError(f"placeholder asset substitution forbidden: {asset_id}")
        if asset.get("substitution_policy") != "reject_solid_color_or_metadata_only":
            raise RepresentativeEpisodeError(f"asset substitution policy missing: {asset_id}")
        revision = _required_text(asset.get("revision_id"), f"{asset_id}.revision_id")
        if revision != _required_text(asset.get("current_revision_id"), f"{asset_id}.current_revision_id"):
            raise RepresentativeEpisodeError(f"stale asset revision: {asset_id}")
        if missing and not asset["provider_needed"]:
            raise RepresentativeEpisodeError(f"missing asset lacks provider-needed gate: {asset_id}")
        if asset["provider_needed"]:
            prompt_id = _required_text(asset.get("prompt_id"), f"{asset_id}.prompt_id")
            prompt = prompts.get(prompt_id)
            if not prompt or prompt.get("asset_id") != asset_id:
                raise RepresentativeEpisodeError(f"asset prompt lineage missing: {asset_id}")
            if prompt.get("version_id") != prompt.get("current_version_id"):
                raise RepresentativeEpisodeError(f"stale prompt version: {prompt_id}")
            if not prompt.get("source_refs") or not _required_text(prompt.get("prompt"), f"{prompt_id}.prompt"):
                raise RepresentativeEpisodeError(f"incomplete prompt lineage: {prompt_id}")


def _validate_timeline(
    shots: dict[str, dict[str, Any]],
    scenes: dict[str, dict[str, Any]],
    characters: dict[str, dict[str, Any]],
    assets: dict[str, dict[str, Any]],
    prompts: dict[str, dict[str, Any]],
    duration: Decimal,
) -> None:
    if not shots:
        raise RepresentativeEpisodeError("shots must not be empty")
    cursor = Decimal("0")
    for shot_id, shot in shots.items():
        start = _decimal(shot.get("start_seconds"), f"{shot_id}.start_seconds")
        end = _decimal(shot.get("end_seconds"), f"{shot_id}.end_seconds")
        if start != cursor or end <= start:
            raise RepresentativeEpisodeError(f"timeline gap or overlap before {shot_id}")
        cursor = end
        if shot.get("scene_id") not in scenes:
            raise RepresentativeEpisodeError(f"unknown scene ref: {shot_id}")
        if any(ref not in characters for ref in shot.get("character_refs", [])):
            raise RepresentativeEpisodeError(f"unknown character ref: {shot_id}")
        required_assets = shot.get("required_asset_ids")
        if not isinstance(required_assets, list) or not required_assets or any(ref not in assets for ref in required_assets):
            raise RepresentativeEpisodeError(f"missing or foreign asset ref: {shot_id}")
        prompt_ids = shot.get("prompt_refs")
        if not isinstance(prompt_ids, list) or not prompt_ids or any(ref not in prompts for ref in prompt_ids):
            raise RepresentativeEpisodeError(f"missing prompt lineage ref: {shot_id}")
        script = _object(shot.get("script"), f"{shot_id}.script")
        _required_text(script.get("visual_action"), f"{shot_id}.script.visual_action")
        dialogue = script.get("dialogue")
        if not isinstance(dialogue, list) or not dialogue:
            raise RepresentativeEpisodeError(f"timed dialogue or narration missing: {shot_id}")
        for line in dialogue:
            if not isinstance(line, dict) or not _required_text(line.get("text"), f"{shot_id}.dialogue.text"):
                raise RepresentativeEpisodeError(f"invalid dialogue: {shot_id}")
            speaker = line.get("speaker_ref")
            if speaker != "narrator" and speaker not in characters:
                raise RepresentativeEpisodeError(f"foreign dialogue speaker: {shot_id}")
        for field in ("camera", "motion", "continuity_note", "quality_target"):
            _required_text(shot.get(field), f"{shot_id}.{field}")
    if cursor != duration:
        raise RepresentativeEpisodeError("shot timeline does not match declared duration")


def _validate_subtitles(value: Any, shots: dict[str, dict[str, Any]], duration: Decimal) -> None:
    plan = _object(value, "subtitle_plan")
    cues = plan.get("cues")
    if not isinstance(cues, list) or len(cues) != len(shots):
        raise RepresentativeEpisodeError("subtitle cues must cover every shot")
    cursor = Decimal("0")
    shot_ids = list(shots)
    for index, cue in enumerate(cues):
        if not isinstance(cue, dict) or cue.get("shot_id") != shot_ids[index]:
            raise RepresentativeEpisodeError("subtitle cue shot order drift")
        start = _decimal(cue.get("start_seconds"), "subtitle.start_seconds")
        end = _decimal(cue.get("end_seconds"), "subtitle.end_seconds")
        if start != cursor or end != _decimal(shots[shot_ids[index]]["end_seconds"], "shot.end_seconds"):
            raise RepresentativeEpisodeError("subtitle timeline gap or mismatch")
        text = _required_text(cue.get("text"), "subtitle.text")
        expected_text = "\n".join(
            _required_text(line.get("text"), "shot.dialogue.text")
            for line in shots[shot_ids[index]]["script"]["dialogue"]
        )
        if text != expected_text:
            raise RepresentativeEpisodeError("subtitle text does not match timed shot dialogue")
        cursor = end
    if cursor != duration:
        raise RepresentativeEpisodeError("subtitle plan duration mismatch")


def _validate_audio(value: Any, shots: dict[str, dict[str, Any]], assets: dict[str, dict[str, Any]]) -> None:
    plan = _object(value, "audio_plan")
    if set(plan.get("coverage_shot_refs", [])) != set(shots):
        raise RepresentativeEpisodeError("audio plan does not cover every shot")
    for key in ("dialogue_asset_id", "music_asset_id", "sfx_asset_id", "master_asset_id"):
        if plan.get(key) not in assets:
            raise RepresentativeEpisodeError(f"audio plan has unknown {key}")
    for key in ("dialogue_direction", "music_direction", "sfx_direction", "mix_requirements"):
        if not plan.get(key):
            raise RepresentativeEpisodeError(f"audio plan missing {key}")


def _validate_assembly(value: Any, shots: dict[str, dict[str, Any]], assets: dict[str, dict[str, Any]], duration: Decimal) -> None:
    plan = _object(value, "assembly_plan")
    if plan.get("contract") != "agentflow_studio.production.episode_delivery.v0.1":
        raise RepresentativeEpisodeError("TP-C assembly contract mapping missing")
    if _decimal(plan.get("duration_seconds"), "assembly.duration_seconds") != duration:
        raise RepresentativeEpisodeError("assembly duration mismatch")
    mappings = plan.get("shot_timeline")
    if not isinstance(mappings, list) or [item.get("shot_id") for item in mappings if isinstance(item, dict)] != list(shots):
        raise RepresentativeEpisodeError("assembly shot mapping incomplete")
    for mapping in mappings:
        shot = shots[mapping["shot_id"]]
        if mapping.get("visual_asset_id") not in assets:
            raise RepresentativeEpisodeError("assembly visual asset ref missing")
        if mapping.get("scene_id") != shot["scene_id"]:
            raise RepresentativeEpisodeError("assembly scene lineage drift")
        if _decimal(mapping.get("start_seconds"), "assembly.start_seconds") != _decimal(
            shot["start_seconds"], "shot.start_seconds"
        ) or _decimal(mapping.get("end_seconds"), "assembly.end_seconds") != _decimal(
            shot["end_seconds"], "shot.end_seconds"
        ):
            raise RepresentativeEpisodeError("assembly shot timing drift")
    if plan.get("precondition") != "all_controlled_assets_ready_and_current":
        raise RepresentativeEpisodeError("assembly must fail closed before assets are current")


def _validate_quality(value: Any) -> None:
    rubric = _object(value, "quality_rubric")
    criteria = rubric.get("criteria")
    if not isinstance(criteria, list) or len(criteria) < 6:
        raise RepresentativeEpisodeError("quality rubric is incomplete")
    gates = rubric.get("gates")
    if not isinstance(gates, list):
        raise RepresentativeEpisodeError("quality gates are missing")
    gate_types = {gate.get("gate_type") for gate in gates if isinstance(gate, dict)}
    required = {"creator_approval", "continuity_review", "technical_qa", "creative_media_qa", "human_acceptance"}
    if not required.issubset(gate_types):
        raise RepresentativeEpisodeError("creator, QA, or human gate missing")
    if any(gate.get("status") not in {"approved", "pending"} for gate in gates if isinstance(gate, dict)):
        raise RepresentativeEpisodeError("invalid quality gate status")


def _validate_crew(value: Any, project: dict[str, Any], characters: dict[str, Any], scenes: dict[str, Any], shots: dict[str, Any]) -> None:
    plan = _object(value, "domain_crew_execution_plan")
    roles = plan.get("roles")
    if not isinstance(roles, list) or tuple(item.get("role") for item in roles if isinstance(item, dict)) != REQUIRED_ROLES:
        raise RepresentativeEpisodeError("domain crew roles are incomplete or unordered")
    if any(not isinstance(item, dict) for item in roles):
        raise RepresentativeEpisodeError("domain crew role must be an object")
    role_agents = {
        item["role"]: _required_text(item.get("agent_id"), f"crew.roles.{item['role']}.agent_id")
        for item in roles
    }
    if len(set(role_agents.values())) != len(REQUIRED_ROLES):
        raise RepresentativeEpisodeError("domain crew agent identity must be unique per role")
    tasks = _indexed(plan.get("tasks"), "task_id", "crew.tasks")
    task_role_list = [item.get("role") for item in tasks.values()]
    if len(tasks) != len(REQUIRED_ROLES) or set(task_role_list) != set(REQUIRED_ROLES):
        raise RepresentativeEpisodeError("domain crew tasks do not cover every role")
    allowed_refs = {
        project["project_id"], project["episode_id"], project["current_version_id"],
        *characters.keys(), *scenes.keys(), *shots.keys(),
    }
    for task_id, task in tasks.items():
        role = task.get("role")
        if task.get("assigned_agent_id") != role_agents.get(role):
            raise RepresentativeEpisodeError(f"crew task role ownership mismatch: {task_id}")
        refs = task.get("entity_refs")
        if not isinstance(refs, list) or not refs or any(ref not in allowed_refs for ref in refs):
            raise RepresentativeEpisodeError(f"crew task entity refs invalid: {task_id}")
        _required_text(task.get("expected_version_id"), f"{task_id}.expected_version_id")
    messages = plan.get("structured_messages")
    handoffs = plan.get("handoffs")
    if not isinstance(messages, list) or not messages or not isinstance(handoffs, list) or not handoffs:
        raise RepresentativeEpisodeError("structured messages or handoffs missing")
    message_ids: set[str] = set()
    for item in messages:
        if not isinstance(item, dict):
            raise RepresentativeEpisodeError("structured message must be an object")
        message_id = _required_text(item.get("message_id"), "structured_message.message_id")
        if message_id in message_ids:
            raise RepresentativeEpisodeError("duplicate structured message id")
        message_ids.add(message_id)
        _required_text(item.get("payload_type"), "structured_message.payload_type")
        if item.get("task_id") not in tasks:
            raise RepresentativeEpisodeError("structured message task ref invalid")
        if item.get("from_role") not in REQUIRED_ROLES or item.get("to_role") not in REQUIRED_ROLES:
            raise RepresentativeEpisodeError("structured message role ref invalid")
        if item.get("from_role") != tasks[item["task_id"]].get("role"):
            raise RepresentativeEpisodeError("structured message source task ownership mismatch")
        if item.get("entity_version_ref") != project["current_version_id"]:
            raise RepresentativeEpisodeError("structured message version ref invalid")
    handoff_ids: set[str] = set()
    for item in handoffs:
        if not isinstance(item, dict):
            raise RepresentativeEpisodeError("handoff must be an object")
        handoff_id = _required_text(item.get("handoff_id"), "handoff.handoff_id")
        if handoff_id in handoff_ids:
            raise RepresentativeEpisodeError("duplicate handoff id")
        handoff_ids.add(handoff_id)
        if item.get("from_task_id") not in tasks or item.get("to_task_id") not in tasks:
            raise RepresentativeEpisodeError("handoff task ref invalid")
        if item.get("from_task_id") == item.get("to_task_id"):
            raise RepresentativeEpisodeError("handoff must cross task ownership")
        if item.get("status") != "planned":
            raise RepresentativeEpisodeError("handoff preparation status invalid")
    arbitration = _object(plan.get("creator_arbitration"), "creator_arbitration")
    for key in ("conflict_id", "from_version_id", "approved_version_id", "creator_decision_ref"):
        _required_text(arbitration.get(key), f"creator_arbitration.{key}")
    affected = arbitration.get("authoritative_affected_task_refs")
    reconfirm = plan.get("downstream_reconfirmations")
    if not isinstance(affected, list) or not affected or not isinstance(reconfirm, list):
        raise RepresentativeEpisodeError("arbitration propagation set missing")
    if arbitration.get("approved_version_id") != project["current_version_id"]:
        raise RepresentativeEpisodeError("creator arbitration approved version drift")
    if len(affected) != len(set(affected)) or any(task_id not in tasks for task_id in affected):
        raise RepresentativeEpisodeError("authoritative affected task ref invalid")
    if any(not isinstance(item, dict) for item in reconfirm):
        raise RepresentativeEpisodeError("downstream reconfirmation must be an object")
    reconfirm_task_ids = [item.get("task_id") for item in reconfirm]
    if len(reconfirm_task_ids) != len(set(reconfirm_task_ids)) or any(task_id not in tasks for task_id in reconfirm_task_ids):
        raise RepresentativeEpisodeError("downstream reconfirmation task ref invalid")
    if set(affected) != set(reconfirm_task_ids):
        raise RepresentativeEpisodeError("downstream reconfirmation set is incomplete")
    if any(item.get("status") != "required_pending" for item in reconfirm):
        raise RepresentativeEpisodeError("preparation reconfirmations must remain pending")
    if any(item.get("approved_version_id") != arbitration["approved_version_id"] for item in reconfirm):
        raise RepresentativeEpisodeError("downstream reconfirmation version drift")


def _validate_nonclaims(value: Any) -> None:
    required = {
        "no_generated_media",
        "no_creative_media_quality_pass",
        "no_human_acceptance",
        "no_business_validation",
        "no_deploy_or_release",
    }
    if not isinstance(value, list) or not required.issubset(set(value)):
        raise RepresentativeEpisodeError("evidence nonclaims are incomplete")


def _indexed(value: Any, key: str, label: str) -> dict[str, dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise RepresentativeEpisodeError(f"{label} must be a non-empty array")
    result: dict[str, dict[str, Any]] = {}
    for item in value:
        if not isinstance(item, dict):
            raise RepresentativeEpisodeError(f"{label} item must be an object")
        ref = _required_text(item.get(key), f"{label}.{key}")
        if ref in result:
            raise RepresentativeEpisodeError(f"duplicate {key}: {ref}")
        result[ref] = item
    return result


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RepresentativeEpisodeError(f"{label} must be an object")
    return value


def _required_text(value: Any, label: str) -> str:
    text = str(value).strip() if value is not None else ""
    if not text:
        raise RepresentativeEpisodeError(f"missing {label}")
    return text


def _decimal(value: Any, label: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise RepresentativeEpisodeError(f"invalid decimal for {label}") from exc


def _number(value: Decimal) -> int | float:
    return int(value) if value == value.to_integral() else float(value)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RepresentativeEpisodeError(f"invalid representative episode package: {exc}") from exc
    if not isinstance(value, dict):
        raise RepresentativeEpisodeError("representative episode package must be an object")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


__all__ = (
    "EVIDENCE_LABEL",
    "RepresentativeEpisodeError",
    "ValidatedRepresentativeEpisode",
    "preparation_evidence",
    "validate_representative_episode",
    "write_preparation_evidence",
)
