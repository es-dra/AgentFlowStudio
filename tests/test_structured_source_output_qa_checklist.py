from __future__ import annotations

import base64
import json


FORBIDDEN_FIELDS = {
    "accepted_for_local_final_media",
    "human_creative_acceptance",
    "business_readiness",
    "legal_readiness",
    "public_readiness",
    "provider_pass",
    "generated_media_qa",
    "raw_provider_response",
    "signed_url",
    "image_path",
    "output_path",
    "request_path",
    "media_bytes",
    "data_base64",
    "api_key",
    "token",
    "cookie",
    "authorization",
    "provider_key",
}


def test_algorithm_exports_contract_and_all_required_followed_completes() -> None:
    from agentflow import algorithms
    from agentflow.algorithms import structured_source_output_qa_checklist as checklist

    packet = checklist.build_structured_source_output_qa_checklist(
        project_id="proj_qa",
        target_id="video_01",
        source_inventory=[_source("src_script"), _source("src_fixed_asset", category="fixed_asset")],
        observed_outputs=[_output("out_video")],
        checklist_items=[
            _item("identity", "identity", ["src_script"], ["out_video"], outcome="followed", severity="critical"),
            _item("continuity", "continuity", ["src_fixed_asset"], ["out_video"], outcome="followed", severity="critical"),
        ],
    )

    assert "structured_source_output_qa_checklist" in algorithms.CORE_AGENT_ALGORITHM_MODULES
    assert checklist.ALGORITHM_ID == "afs.structured_source_output_qa_checklist.v0.1"
    assert checklist.PACKET_STATES
    assert checklist.ITEM_OUTCOMES
    assert packet["artifact_type"] == "agentflow_structured_source_output_qa_checklist"
    assert packet["schema_version"] == "0.1.0"
    assert packet["packet_state"] == "checklist_completed"
    assert packet["summary_counts"]["required_items_followed_count"] == 2
    assert packet["summary_counts"]["critical_fail_count"] == 0
    _assert_no_acceptance_or_private_surface(packet)


def test_partial_noncritical_requires_waiver_or_evidence_and_valid_waiver_closes_only_that_item() -> None:
    from agentflow.algorithms.structured_source_output_qa_checklist import build_structured_source_output_qa_checklist

    partial = build_structured_source_output_qa_checklist(
        project_id="proj_qa",
        target_id="video_01",
        source_inventory=[_source("src_style")],
        observed_outputs=[_output("out_video")],
        checklist_items=[_item("style", "style", ["src_style"], ["out_video"], outcome="partially_followed", severity="medium")],
    )
    waived = build_structured_source_output_qa_checklist(
        project_id="proj_qa",
        target_id="video_01",
        source_inventory=[_source("src_style"), _source("src_identity")],
        observed_outputs=[_output("out_video")],
        checklist_items=[
            _item("style", "style", ["src_style"], ["out_video"], outcome="partially_followed", severity="medium"),
            _item("identity", "identity", ["src_identity"], ["out_video"], outcome="followed", severity="critical"),
        ],
        waivers=[{"waiver_id": "waiver_style", "item_id": "style", "reviewer_role": "qa_reviewer"}],
    )

    assert partial["packet_state"] == "checklist_ready_for_review"
    assert partial["summary_counts"]["waiver_required_count"] == 1
    assert partial["summary_counts"]["critical_fail_count"] == 0
    assert waived["packet_state"] == "checklist_completed"
    assert waived["summary_counts"]["waiver_applied_count"] == 1
    assert waived["summary_counts"]["waiver_required_count"] == 0
    assert next(item for item in waived["checklist_items"] if item["item_id"] == "style")["closed_by_waiver"] is True
    assert next(item for item in waived["checklist_items"] if item["item_id"] == "identity")["closed_by_waiver"] is False
    _assert_no_acceptance_or_private_surface(waived)


def test_active_runtime_states_never_complete_or_waive_into_completion() -> None:
    from agentflow.algorithms.structured_source_output_qa_checklist import build_structured_source_output_qa_checklist

    for state in ("submitted", "pending", "running", "retrying"):
        followed = build_structured_source_output_qa_checklist(
            **_packet_args(outputs=[{**_output("out_video"), "runtime_state": state}], items=[_item("identity", "identity", ["src_script"], ["out_video"], outcome="followed", severity="critical")])
        )
        waived = build_structured_source_output_qa_checklist(
            **_packet_args(
                outputs=[{**_output("out_video"), "runtime_state": state}],
                items=[_item("style", "style", ["src_script"], ["out_video"], outcome="partially_followed")],
                waivers=[{"waiver_id": f"waiver_{state}", "item_id": "style", "reviewer_role": "qa_reviewer"}],
            )
        )

        assert followed["packet_state"] == "blocked_missing_evidence"
        assert followed["summary_counts"]["required_items_followed_count"] == 1
        assert followed["runtime_state_review"]["reason_code"] == "runtime_state_not_stable_reviewable"
        assert followed["runtime_state_review"]["noncompletion_required"] is True
        assert waived["packet_state"] == "blocked_missing_evidence"
        assert waived["waiver_validation"]["invalid_waiver_count"] == 1
        assert "runtime_state_not_stable_reviewable" in waived["waiver_validation"]["waivers"][0]["invalid_reasons"]
        _assert_no_acceptance_or_private_surface(followed)
        _assert_no_acceptance_or_private_surface(waived)


def test_invalid_waivers_for_critical_safety_scope_project_unsafe_and_missing_output_fail_closed() -> None:
    from agentflow.algorithms.structured_source_output_qa_checklist import build_structured_source_output_qa_checklist

    cases = [
        (
            _packet_args(
                items=[_item("critical_identity", "identity", ["src_identity"], ["out_video"], outcome="partially_followed", severity="critical")],
                waivers=[{"waiver_id": "waiver_critical", "item_id": "critical_identity", "reviewer_role": "qa_reviewer"}],
            ),
            "blocked_missing_evidence",
            "waiver_not_allowed_for_item",
        ),
        (
            _packet_args(
                items=[_item("safety", "safety", ["src_script"], ["out_video"], outcome="blocked_unsafe")],
                waivers=[{"waiver_id": "waiver_safety", "item_id": "safety", "reviewer_role": "qa_reviewer"}],
            ),
            "blocked_unsafe",
            "waiver_not_allowed_for_item",
        ),
        (
            _packet_args(
                items=[_item("scope", "project_scope", ["src_script"], ["out_video"], outcome="blocked_project_scope")],
                waivers=[{"waiver_id": "waiver_scope", "item_id": "scope", "reviewer_role": "qa_reviewer"}],
            ),
            "blocked_project_scope",
            "waiver_not_allowed_for_item",
        ),
        (
            _packet_args(
                outputs=[{**_output("out_video"), "project_id": "other_project"}],
                items=[_item("style", "style", ["src_script"], ["out_video"], outcome="partially_followed")],
                waivers=[{"waiver_id": "waiver_project", "item_id": "style", "project_id": "proj_qa", "reviewer_role": "qa_reviewer"}],
            ),
            "blocked_project_scope",
            "project_or_target_mismatch",
        ),
        (
            _packet_args(
                outputs=[],
                items=[_item("style", "style", ["src_script"], [], outcome="partially_followed")],
                waivers=[{"waiver_id": "waiver_missing_output", "item_id": "style", "reviewer_role": "qa_reviewer"}],
            ),
            "blocked_missing_evidence",
            "missing_target_output",
        ),
        (
            _packet_args(
                items=[{**_item("style", "style", ["src_script"], ["out_video"], outcome="partially_followed"), "provider_raw_response": {"id": "unsafe"}}],
                waivers=[{"waiver_id": "waiver_unsafe", "item_id": "style", "reviewer_role": "qa_reviewer"}],
            ),
            "blocked_unsafe",
            "unsafe_input_payload",
        ),
    ]

    for kwargs, expected_state, expected_reason in cases:
        packet = build_structured_source_output_qa_checklist(**kwargs)
        reasons = {reason for waiver in packet["waiver_validation"]["waivers"] for reason in waiver["invalid_reasons"]}
        assert packet["packet_state"] == expected_state
        assert packet["waiver_validation"]["invalid_waiver_count"] == 1
        assert expected_reason in reasons
        _assert_no_acceptance_or_private_surface(packet)


def test_critical_ignored_missing_evidence_conflict_unverifiable_and_first_frame_are_non_accepting() -> None:
    from agentflow.algorithms.structured_source_output_qa_checklist import build_structured_source_output_qa_checklist

    critical = build_structured_source_output_qa_checklist(
        **_packet_args(items=[_item("fixed_asset", "fixed_asset", ["missing_fixed"], ["out_video"], outcome="ignored", severity="critical")])
    )
    missing = build_structured_source_output_qa_checklist(
        **_packet_args(items=[_item("missing", "source_evidence", ["missing_src"], ["out_video"], severity="critical")])
    )
    conflict = build_structured_source_output_qa_checklist(
        **_packet_args(items=[{**_item("conflict", "continuity", ["src_script"], ["out_video"], outcome="followed"), "conflict": True}])
    )
    unverifiable = build_structured_source_output_qa_checklist(
        **_packet_args(items=[_item("unverifiable_style", "style", ["src_script"], ["out_video"], outcome="unverifiable")])
    )
    first_frame = build_structured_source_output_qa_checklist(
        **_packet_args(items=[_item("first_frame", "video_first_frame_provenance", ["missing_frame_src"], ["out_video"], severity="critical")])
    )

    assert critical["packet_state"] == "blocked_missing_evidence"
    assert critical["summary_counts"]["critical_fail_count"] > 0
    assert missing["packet_state"] == "blocked_missing_evidence"
    assert unverifiable["packet_state"] == "unverifiable"
    assert conflict["packet_state"] == "blocked_conflict"
    assert first_frame["packet_state"] == "blocked_missing_evidence"
    for packet in (critical, missing, conflict, unverifiable, first_frame):
        _assert_no_acceptance_or_private_surface(packet)


def test_unsafe_markers_and_fields_fail_closed_without_echoing_private_values() -> None:
    from agentflow.algorithms.structured_source_output_qa_checklist import build_structured_source_output_qa_checklist

    unsafe_payloads = [
        {"provider_raw_response": {"ok": True}},
        {"signed_url": "https://private.example.test/raw?token=abc"},
        {"image_path": "/home/private/out.png"},
        {"data_base64": "iVBORw0KGgo="},
        {"reviewer_note": "Authorization: Bearer secret-token-value"},
        {"provider_key": "sk-test-secret"},
        {"media_bytes": base64.b64encode(b"\x00" * 800).decode("ascii")},
    ]
    for payload in unsafe_payloads:
        packet = build_structured_source_output_qa_checklist(
            **_packet_args(items=[{**_item("style", "style", ["src_script"], ["out_video"], outcome="followed"), **payload}])
        )
        serialized = json.dumps(packet, ensure_ascii=False).lower()
        assert packet["packet_state"] == "blocked_unsafe"
        assert "private.example" not in serialized
        assert "secret-token-value" not in serialized
        assert "/home/private" not in serialized
        _assert_no_acceptance_or_private_surface(packet)


def test_project_target_mismatch_and_partial_runtime_preserve_reviewable_outputs_but_fail_required_scope() -> None:
    from agentflow.algorithms.structured_source_output_qa_checklist import build_structured_source_output_qa_checklist

    mismatch = build_structured_source_output_qa_checklist(
        **_packet_args(outputs=[{**_output("out_video"), "target_id": "other_target"}], items=[_item("identity", "identity", ["src_script"], ["out_video"])])
    )
    partial_runtime = build_structured_source_output_qa_checklist(
        **_packet_args(
            outputs=[{**_output("out_video"), "runtime_state": "partially_complete", "batch_status": "partial"}],
            items=[
                _item("identity", "identity", ["src_script"], ["out_video"], outcome="followed", severity="critical"),
                _item("continuity", "continuity", ["missing_continuity"], ["out_video"], severity="critical"),
            ],
        )
    )

    assert mismatch["packet_state"] == "blocked_project_scope"
    assert partial_runtime["packet_state"] == "blocked_missing_evidence"
    assert partial_runtime["observed_output_refs"][0]["output_ref_id"] == "out_video"
    assert partial_runtime["observed_output_refs"][0]["runtime_state"] == "partially_complete"
    assert partial_runtime["summary_counts"]["required_items_followed_count"] == 1
    assert partial_runtime["summary_counts"]["critical_fail_count"] == 1
    _assert_no_acceptance_or_private_surface(mismatch)
    _assert_no_acceptance_or_private_surface(partial_runtime)


def _packet_args(*, outputs: list[dict] | None = None, items: list[dict] | None = None, waivers: list[dict] | None = None) -> dict:
    return {
        "project_id": "proj_qa",
        "target_id": "video_01",
        "source_inventory": [_source("src_script"), _source("src_identity")],
        "observed_outputs": [_output("out_video")] if outputs is None else outputs,
        "checklist_items": items or [_item("identity", "identity", ["src_script"], ["out_video"], outcome="followed")],
        "waivers": waivers or [],
    }


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


def _assert_no_acceptance_or_private_surface(packet: dict) -> None:
    serialized = json.dumps(packet, ensure_ascii=False).lower()
    assert "accepted_for_local_final_media" not in serialized
    assert "human_creative_acceptance" not in serialized
    assert "business_readiness" not in serialized
    assert "legal_readiness" not in serialized
    assert "public_readiness" not in serialized
    assert "generated_media_qa" not in serialized
    assert "provider_pass" not in serialized
    assert "writes_long_term_memory\": true" not in serialized
    assert "writes_company_kb\": true" not in serialized
    _assert_forbidden_fields_absent(packet)


def _assert_forbidden_fields_absent(value) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            assert key not in FORBIDDEN_FIELDS
            _assert_forbidden_fields_absent(item)
    elif isinstance(value, list):
        for item in value:
            _assert_forbidden_fields_absent(item)
