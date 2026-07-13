from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from agentflow_studio.production.representative_episode import (
    RepresentativeEpisodeError,
    preparation_evidence,
    validate_representative_episode,
    write_preparation_evidence,
)


PACKAGE_PATH = Path("examples/representative_episode/episode_package.json")


def _package() -> dict:
    return json.loads(PACKAGE_PATH.read_text(encoding="utf-8"))


def _candidate(tmp_path: Path, value: dict, name: str = "candidate.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return path


def test_representative_episode_package_is_complete_provider_free_preparation(tmp_path: Path) -> None:
    validated = validate_representative_episode(PACKAGE_PATH)
    evidence = preparation_evidence(validated)
    output = write_preparation_evidence(validated, tmp_path / "preparation_evidence.json")

    assert validated.duration_seconds == 135
    assert evidence["evidence_label"] == "representative_episode_preparation_pass"
    assert evidence["character_count"] == 3
    assert evidence["scene_count"] == 3
    assert evidence["shot_count"] == 15
    assert evidence["provider_calls_started"] == 0
    assert len(evidence["provider_unavoidable_asset_ids"]) == 25
    assert evidence["evidence_layers"]["generated_media"] == "not_started"
    assert evidence["evidence_layers"]["creative_media_quality"] == "not_evaluated"
    assert json.loads(output.read_text(encoding="utf-8")) == evidence


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("provider_call", "provider_calls_started"),
        ("short_duration", "between 120 and 180"),
        ("timeline_gap", "timeline gap or overlap"),
        ("stale_character", "stale version"),
        ("missing_prompt", "prompt lineage missing"),
        ("placeholder", "placeholder asset substitution forbidden"),
        ("metadata_only", "placeholder asset substitution forbidden"),
        ("missing_creator_gate", "creator, QA, or human gate missing"),
        ("missing_reconfirmation", "reconfirmation set is incomplete"),
        ("non_object_message", "structured message must be an object"),
        ("non_object_handoff", "handoff must be an object"),
        ("subtitle_script_drift", "subtitle text does not match"),
        ("assembly_timing_drift", "assembly shot timing drift"),
        ("foreign_propagation_task", "affected task ref invalid"),
        ("task_agent_mismatch", "task role ownership mismatch"),
        ("message_task_owner_mismatch", "source task ownership mismatch"),
        ("duplicate_message_id", "duplicate structured message id"),
        ("duplicate_handoff_id", "duplicate handoff id"),
    ],
)
def test_package_fails_closed_on_incomplete_or_overclaimed_state(
    tmp_path: Path, mutation: str, message: str
) -> None:
    package = copy.deepcopy(_package())
    if mutation == "provider_call":
        package["provider_calls_started"] = 1
    elif mutation == "short_duration":
        package["project"]["duration_seconds"] = 119
    elif mutation == "timeline_gap":
        package["shots"][1]["start_seconds"] = 10
    elif mutation == "stale_character":
        package["characters"][0]["current_version_id"] = "char-lin-yao-v2"
    elif mutation == "missing_prompt":
        package["prompt_lineage"] = package["prompt_lineage"][1:]
    elif mutation == "placeholder":
        package["asset_manifest"][0]["content_class"] = "solid_color"
    elif mutation == "metadata_only":
        package["asset_manifest"][0]["content_class"] = "metadata_only"
    elif mutation == "missing_creator_gate":
        package["quality_rubric"]["gates"] = [
            item for item in package["quality_rubric"]["gates"]
            if item["gate_type"] != "creator_approval"
        ]
    elif mutation == "missing_reconfirmation":
        package["domain_crew_execution_plan"]["downstream_reconfirmations"].pop()
    elif mutation == "non_object_message":
        package["domain_crew_execution_plan"]["structured_messages"] = ["not-an-object"]
    elif mutation == "non_object_handoff":
        package["domain_crew_execution_plan"]["handoffs"] = ["not-an-object"]
    elif mutation == "subtitle_script_drift":
        package["subtitle_plan"]["cues"][0]["text"] = "与剧本无关的字幕"
    elif mutation == "assembly_timing_drift":
        package["assembly_plan"]["shot_timeline"][0]["end_seconds"] = 77
    elif mutation == "foreign_propagation_task":
        plan = package["domain_crew_execution_plan"]
        plan["creator_arbitration"]["authoritative_affected_task_refs"] = ["foreign-task"]
        plan["downstream_reconfirmations"] = [
            {"task_id": "foreign-task", "status": "required_pending", "approved_version_id": "ep-rainlight-001-v1"}
        ]
    elif mutation == "task_agent_mismatch":
        package["domain_crew_execution_plan"]["tasks"][0]["assigned_agent_id"] = "crew-rainlight-art"
    elif mutation == "message_task_owner_mismatch":
        package["domain_crew_execution_plan"]["structured_messages"][0]["from_role"] = "art"
    elif mutation == "duplicate_message_id":
        messages = package["domain_crew_execution_plan"]["structured_messages"]
        messages[1]["message_id"] = messages[0]["message_id"]
    elif mutation == "duplicate_handoff_id":
        handoffs = package["domain_crew_execution_plan"]["handoffs"]
        handoffs[1]["handoff_id"] = handoffs[0]["handoff_id"]

    with pytest.raises(RepresentativeEpisodeError, match=message):
        validate_representative_episode(_candidate(tmp_path, package))


def test_package_maps_every_shot_to_tpc_and_every_role_to_joined_crew() -> None:
    package = _package()
    shot_ids = [item["shot_id"] for item in package["shots"]]
    assembly_ids = [item["shot_id"] for item in package["assembly_plan"]["shot_timeline"]]
    roles = [item["role"] for item in package["domain_crew_execution_plan"]["roles"]]

    assert assembly_ids == shot_ids
    assert roles == [
        "screenwriter", "storyboard", "art", "director", "continuity",
        "qa", "audio", "edit", "export",
    ]
    assert all(item["status"] == "missing" for item in package["asset_manifest"])
    assert all(item["provider_needed"] is True for item in package["asset_manifest"])
    assert all(item["content_class"] not in {"solid_color", "slate", "metadata_only"}
               for item in package["asset_manifest"])


def test_preparation_source_has_no_provider_or_network_dispatch() -> None:
    source = Path("agentflow_studio/production/representative_episode.py").read_text(encoding="utf-8")
    cli = Path("tools/afs_representative_episode_preparation.py").read_text(encoding="utf-8")
    combined = source + "\n" + cli
    assert "provider_calls_started" in combined
    assert "requests." not in combined
    assert "urllib" not in combined
    assert "http://" not in combined and "https://" not in combined
