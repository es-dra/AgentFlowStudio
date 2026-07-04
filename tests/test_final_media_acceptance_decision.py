from __future__ import annotations

import json
from pathlib import Path


def test_final_media_decision_exports_and_requires_explicit_reviewer_action() -> None:
    from agentflow import algorithms
    from agentflow.algorithms import final_media_acceptance_decision as final_decision

    packet = _completed_checklist_packet()
    pending = final_decision.build_final_media_acceptance_decision(
        project_id="proj_qa",
        target_id="video_01",
        checklist_packet_ref=packet,
        decision_requested_at="2026-07-05T00:30:00Z",
    )
    accepted = final_decision.build_final_media_acceptance_decision(
        project_id="proj_qa",
        target_id="video_01",
        checklist_packet_ref=packet,
        decision_requested_at="2026-07-05T00:30:00Z",
        reviewer_action="accept",
        reviewer_role="qa_reviewer",
    )

    assert "final_media_acceptance_decision" in algorithms.CORE_AGENT_ALGORITHM_MODULES
    assert final_decision.ALGORITHM_ID == "afs.final_media_acceptance_decision.v0.1"
    assert pending["artifact_type"] == "agentflow_final_media_acceptance_decision"
    assert pending["qa_passed"] is True
    assert pending["accepted_for_local_final_media"] is False
    assert pending["decision_state"] == "qa_passed_pending_reviewer_action"
    assert pending["reviewer_action_required"] is True
    assert accepted["qa_passed"] is True
    assert accepted["accepted_for_local_final_media"] is True
    assert accepted["decision_state"] == "accepted_for_local_final_media"
    assert accepted["reviewer_action"]["studio_action_id"] == "accept"
    assert accepted["studio_action_wiring"]["acceptance_requires_explicit_reviewer_action"] is True
    _assert_no_checklist_items_or_private_claims(accepted)


def test_decision_consumes_summary_refs_without_recalculating_checklist_items() -> None:
    from agentflow.algorithms.final_media_acceptance_decision import build_final_media_acceptance_decision

    packet = _completed_checklist_packet()
    packet["checklist_items"] = [
        {
            "item_id": "mutable_late_array_item",
            "category": "identity",
            "outcome": "ignored",
            "critical": True,
        }
    ]

    decision = build_final_media_acceptance_decision(
        project_id="proj_qa",
        target_id="video_01",
        checklist_packet_ref=packet,
        decision_requested_at="2026-07-05T00:30:00Z",
        reviewer_action="accept",
        reviewer_role="qa_reviewer",
    )

    assert decision["qa_passed"] is True
    assert decision["packet_policy"]["consumes_checklist_truth_without_recalculation"] is True
    assert decision["packet_policy"]["copies_checklist_item_arrays"] is False
    assert "mutable_late_array_item" not in json.dumps(decision, ensure_ascii=False)
    _assert_no_checklist_items_or_private_claims(decision)


def test_fail_closed_for_runtime_output_scope_safety_critical_and_role_blockers() -> None:
    from agentflow.algorithms.final_media_acceptance_decision import build_final_media_acceptance_decision

    cases = [
        (_with_output_patch({"runtime_state": "running"}), "blocked_missing_evidence", "active_runtime_state"),
        (_with_packet_patch({"observed_output_refs": []}), "blocked_missing_evidence", "missing_output_ref"),
        (_with_output_patch({"safe_preview_ref": ""}), "blocked_missing_evidence", "missing_safe_preview_ref"),
        (_with_packet_patch({"project_id": "other_project"}), "blocked_project_scope", "project_or_target_mismatch"),
        (_with_summary_patch({"critical_fail_count": 1}, blocker_ids=["critical_identity"]), "blocked_missing_evidence", "critical_fail_count_present"),
        (_with_packet_patch({"packet_state": "blocked_unsafe"}, blocker_ids=["safety"]), "blocked_unsafe", "checklist_blocked_unsafe"),
        (_completed_checklist_packet(), "blocked_unsupported_reviewer_role", "unsupported_reviewer_role"),
    ]

    for index, (packet, expected_state, expected_reason) in enumerate(cases):
        role = "unsupported_role" if expected_reason == "unsupported_reviewer_role" else "qa_reviewer"
        decision = build_final_media_acceptance_decision(
            project_id="proj_qa",
            target_id="video_01",
            checklist_packet_ref=packet,
            decision_requested_at="2026-07-05T00:30:00Z",
            reviewer_action="accept",
            reviewer_role=role,
        )
        assert decision["decision_state"] == expected_state, index
        assert decision["accepted_for_local_final_media"] is False
        assert expected_reason in decision["decision_reasons"]
        _assert_no_checklist_items_or_private_claims(decision)


def test_stale_malformed_unsafe_and_checklist_ref_mismatch_are_rejected() -> None:
    from agentflow.algorithms.final_media_acceptance_decision import build_final_media_acceptance_decision

    stale = _with_packet_patch({"created_at": "2026-07-03T00:00:00Z"})
    malformed = _with_packet_patch({"artifact_type": "agentflow_other_packet"})
    unsafe = _with_packet_patch({"raw_provider_response": {"id": "secret-provider-value"}})
    mismatch = _completed_checklist_packet()

    stale_decision = build_final_media_acceptance_decision(
        project_id="proj_qa",
        target_id="video_01",
        checklist_packet_ref=stale,
        decision_requested_at="2026-07-05T00:30:00Z",
        reviewer_action="accept",
        reviewer_role="qa_reviewer",
    )
    malformed_decision = build_final_media_acceptance_decision(
        project_id="proj_qa",
        target_id="video_01",
        checklist_packet_ref=malformed,
        decision_requested_at="2026-07-05T00:30:00Z",
        reviewer_action="accept",
        reviewer_role="qa_reviewer",
    )
    unsafe_decision = build_final_media_acceptance_decision(
        project_id="proj_qa",
        target_id="video_01",
        checklist_packet_ref=unsafe,
        decision_requested_at="2026-07-05T00:30:00Z",
        reviewer_action="accept",
        reviewer_role="qa_reviewer",
    )
    ref_mismatch_decision = build_final_media_acceptance_decision(
        project_id="proj_qa",
        target_id="video_01",
        checklist_packet_ref=mismatch,
        decision_requested_at="2026-07-05T00:30:00Z",
        reviewer_action="accept",
        reviewer_role="qa_reviewer",
        expected_checklist_id="checklist:other",
    )

    assert stale_decision["decision_state"] == "blocked_stale_packet"
    assert malformed_decision["decision_state"] == "blocked_malformed_packet"
    assert unsafe_decision["decision_state"] == "blocked_unsafe"
    assert ref_mismatch_decision["decision_state"] == "blocked_project_scope"
    serialized = json.dumps(unsafe_decision, ensure_ascii=False).lower()
    assert "secret-provider-value" not in serialized
    for decision in (stale_decision, malformed_decision, unsafe_decision, ref_mismatch_decision):
        assert decision["accepted_for_local_final_media"] is False
        _assert_no_checklist_items_or_private_claims(decision)


def test_noncritical_waiver_summary_can_pass_only_when_source_checklist_completed() -> None:
    from agentflow.algorithms.final_media_acceptance_decision import build_final_media_acceptance_decision

    valid_waiver_packet = _noncritical_waived_checklist_packet()
    invalid_waiver_packet = _with_summary_patch({"invalid_waiver_count": 1})

    accepted = build_final_media_acceptance_decision(
        project_id="proj_qa",
        target_id="video_01",
        checklist_packet_ref=valid_waiver_packet,
        decision_requested_at="2026-07-05T00:30:00Z",
        reviewer_action="accept",
        reviewer_role="media_reviewer",
    )
    blocked = build_final_media_acceptance_decision(
        project_id="proj_qa",
        target_id="video_01",
        checklist_packet_ref=invalid_waiver_packet,
        decision_requested_at="2026-07-05T00:30:00Z",
        reviewer_action="accept",
        reviewer_role="media_reviewer",
    )

    assert accepted["accepted_for_local_final_media"] is True
    assert accepted["source_checklist_summary"]["waiver_applied_count"] == 1
    assert blocked["accepted_for_local_final_media"] is False
    assert "invalid_noncritical_waiver_state" in blocked["decision_reasons"]
    _assert_no_checklist_items_or_private_claims(accepted)
    _assert_no_checklist_items_or_private_claims(blocked)


def test_static_action_wiring_uses_existing_studio_action_vocabulary() -> None:
    from agentflow.algorithms.final_media_acceptance_decision import STUDIO_ACTION_WIRING

    vocabulary = Path("apps/studio/src/studio-entity-status-vocabulary.js").read_text(encoding="utf-8")

    assert STUDIO_ACTION_WIRING["uses_existing_action_vocabulary"] is True
    assert 'action("accept"' in vocabulary
    assert 'action("reject"' in vocabulary
    assert 'action("view_evidence"' in vocabulary
    assert '"generation_candidate", "keyframe_version", "video_revision"' in vocabulary


def _completed_checklist_packet() -> dict:
    from agentflow.algorithms.structured_source_output_qa_checklist import build_structured_source_output_qa_checklist

    packet = build_structured_source_output_qa_checklist(
        project_id="proj_qa",
        target_id="video_01",
        source_inventory=[_source("src_script"), _source("src_fixed_asset", category="fixed_asset")],
        observed_outputs=[_output("out_video")],
        checklist_items=[
            _item("identity", "identity", ["src_script"], ["out_video"], outcome="followed", severity="critical"),
            _item("continuity", "continuity", ["src_fixed_asset"], ["out_video"], outcome="followed", severity="critical"),
        ],
        checklist_id="checklist:video_01",
    )
    packet["artifact_id"] = "qa_packet_video_01"
    packet["created_at"] = "2026-07-05T00:00:00Z"
    packet["blocker_ids"] = []
    return packet


def _noncritical_waived_checklist_packet() -> dict:
    from agentflow.algorithms.structured_source_output_qa_checklist import build_structured_source_output_qa_checklist

    packet = build_structured_source_output_qa_checklist(
        project_id="proj_qa",
        target_id="video_01",
        source_inventory=[_source("src_script"), _source("src_style")],
        observed_outputs=[_output("out_video")],
        checklist_items=[
            _item("identity", "identity", ["src_script"], ["out_video"], outcome="followed", severity="critical"),
            _item("style", "style", ["src_style"], ["out_video"], outcome="partially_followed", severity="medium"),
        ],
        waivers=[{"waiver_id": "waiver_style", "item_id": "style", "reviewer_role": "qa_reviewer"}],
        checklist_id="checklist:video_01",
    )
    packet["artifact_id"] = "qa_packet_video_01"
    packet["created_at"] = "2026-07-05T00:00:00Z"
    packet["blocker_ids"] = []
    return packet


def _with_packet_patch(patch: dict, *, blocker_ids: list[str] | None = None) -> dict:
    packet = _completed_checklist_packet()
    packet.update(patch)
    if blocker_ids is not None:
        packet["blocker_ids"] = blocker_ids
    return packet


def _with_summary_patch(summary_patch: dict, *, blocker_ids: list[str] | None = None) -> dict:
    packet = _completed_checklist_packet()
    packet["summary_counts"] = {**packet["summary_counts"], **summary_patch}
    if blocker_ids is not None:
        packet["blocker_ids"] = blocker_ids
    return packet


def _with_output_patch(output_patch: dict) -> dict:
    packet = _completed_checklist_packet()
    packet["observed_output_refs"] = [{**packet["observed_output_refs"][0], **output_patch}]
    return packet


def _source(source_ref_id: str, *, category: str = "source_text") -> dict:
    return {
        "source_ref_id": source_ref_id,
        "project_id": "proj_qa",
        "category": category,
        "artifact_id": f"artifact_{source_ref_id}",
        "safe_preview_ref": f"/projects/proj_qa/sources/{source_ref_id}/preview",
        "sha256": "a" * 64,
        "byte_count": 512,
        "provider_calls_started": False,
    }


def _output(output_ref_id: str) -> dict:
    return {
        "output_ref_id": output_ref_id,
        "project_id": "proj_qa",
        "target_id": "video_01",
        "candidate_id": "candidate_01",
        "artifact_id": f"artifact_{output_ref_id}",
        "safe_preview_ref": f"/projects/proj_qa/targets/video_01/outputs/{output_ref_id}/preview",
        "sha256": "b" * 64,
        "byte_count": 1024,
        "width": 720,
        "height": 1280,
        "aspect_ratio": "9:16",
        "duration_seconds": 8.0,
        "provider_gate": "closed",
        "provider_calls_started": False,
        "runtime_state": "complete",
    }


def _item(item_id: str, category: str, source_refs: list[str], output_refs: list[str], *, outcome: str = "", severity: str = "medium") -> dict:
    item = {
        "item_id": item_id,
        "project_id": "proj_qa",
        "target_id": "video_01",
        "category": category,
        "severity": severity,
        "required": True,
        "expected_source_refs": source_refs,
        "observed_output_refs": output_refs,
        "reviewer_note": "safe bounded note",
        "suggested_local_action": "collect local evidence",
    }
    if outcome:
        item["outcome"] = outcome
    return item


def _assert_no_checklist_items_or_private_claims(decision: dict) -> None:
    serialized = json.dumps(decision, ensure_ascii=False).lower()
    assert "checklist_items" not in serialized
    assert "human_creative_acceptance" not in serialized
    assert "business_readiness" not in serialized
    assert "legal_readiness" not in serialized
    assert "public_readiness" not in serialized
    assert "provider_pass" not in serialized
    assert "raw_provider_response" not in serialized
    assert "signed_url" not in serialized
    assert "image_path" not in serialized
    assert "output_path" not in serialized
    assert "media_bytes" not in serialized
    assert "data_base64" not in serialized
    assert "api_key" not in serialized
    assert "token" not in serialized
    assert "cookie" not in serialized
    assert "authorization" not in serialized
