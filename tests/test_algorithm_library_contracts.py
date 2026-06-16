from __future__ import annotations

import json


def test_algorithm_library_exports_runtime_algorithm_contracts() -> None:
    from agentflow import algorithms
    from agentflow.algorithms import (
        asset_card_drafting,
        context_resolver,
        creative_intent_control,
        fixed_asset_memory,
        provider_gate_manifest,
        quality_feedback_scoring,
        revision_drift_control,
        skill_action_selection,
    )

    assert algorithms.ALGORITHM_LIBRARY_VERSION.startswith("afs_algorithm_library_")
    for module in (
        asset_card_drafting,
        context_resolver,
        creative_intent_control,
        fixed_asset_memory,
        provider_gate_manifest,
        quality_feedback_scoring,
        revision_drift_control,
        skill_action_selection,
    ):
        assert module.ALGORITHM_ID.startswith("afs.")
        assert module.INPUT_CONTRACT
        assert module.OUTPUT_CONTRACT
        assert module.FAILURE_MODES
        assert module.EVIDENCE_BOUNDARY


def test_fixed_asset_memory_rejects_draft_assets_for_context_candidates() -> None:
    from agentflow.algorithms.fixed_asset_memory import fixed_context_assets

    assets = {
        "draft_1": {"asset_id": "draft_1", "status": "draft", "asset_type": "character", "label": "Draft"},
        "fixed_1": {"asset_id": "fixed_1", "status": "fixed", "asset_type": "character", "label": "Fixed"},
        "rejected_1": {"asset_id": "rejected_1", "status": "rejected", "asset_type": "scene", "label": "Rejected"},
    }

    assert list(fixed_context_assets(assets)) == ["fixed_1"]


def test_provider_safe_manifest_redacts_unsafe_boundaries() -> None:
    from agentflow.algorithms.provider_gate_manifest import blocked_manifest, provider_gate_status

    gate = provider_gate_status("vision", enabled=False)
    manifest = blocked_manifest(
        action="asset_card_draft",
        capability="vision",
        required_gate=gate.required_gate,
        failure_class="remote_vision_gate_closed",
    )
    serialized = json.dumps(manifest, ensure_ascii=False).lower()

    assert gate.status == "blocked"
    assert manifest["provider_raw_response_stored"] is False
    assert manifest["media_bytes_returned_by_api"] is False
    assert "api_key" not in serialized
    assert "signed_url" not in serialized
    assert "c:\\" not in serialized
    assert "d:\\" not in serialized


def test_quality_feedback_scoring_sanitizes_raw_evidence_without_memory_promotion() -> None:
    from agentflow.algorithms.quality_feedback_scoring import sanitize_quality_feedback

    payload = sanitize_quality_feedback(
        {
            "kind": "studio_quality_feedback",
            "node_id": "node-1",
            "node_type": "video",
            "ratings": {"identity_similarity": 5, "unknown_metric": 3},
            "target_change_success": 4,
            "drift_notes": r"bad url https://example.test/signed?token=abc and C:\\secret\\asset.png",
            "safe_preview_ref": "runtime_preview_endpoint",
        }
    )
    serialized = json.dumps(payload, ensure_ascii=False).lower()

    assert payload["ratings"] == {"identity_similarity": 5}
    assert payload["feedback_is_memory"] is False
    assert payload["writes_long_term_memory"] is False
    assert "token=abc" not in serialized
    assert "c:\\secret" not in serialized
