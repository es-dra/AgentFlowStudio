from __future__ import annotations

from studio_static_helpers import STUDIO_ROOT, _styles


def test_studio_human_gate_hook_uses_runtime_contract_without_promotion() -> None:
    human_gate = STUDIO_ROOT / "src" / "human-gate.js"
    node_menu = (STUDIO_ROOT / "src" / "panels" / "node-menu.js").read_text(encoding="utf-8")
    main = (STUDIO_ROOT / "src" / "main.js").read_text(encoding="utf-8")
    script_breakdown = (STUDIO_ROOT / "src" / "script-breakdown.js").read_text(encoding="utf-8")
    keyframe_response = (STUDIO_ROOT / "src" / "node-keyframe-response.js").read_text(encoding="utf-8")
    runtime_client = (STUDIO_ROOT / "src" / "runtime-client.js").read_text(encoding="utf-8")
    styles = _styles()

    assert human_gate.is_file()
    human_gate_source = human_gate.read_text(encoding="utf-8")
    assert "HUMAN_GATE_DECISION_EVENT" in human_gate_source
    assert "accepted_for_next_step" in human_gate_source
    assert "needs_revision" in human_gate_source
    assert "asset_card_candidate" in human_gate_source
    assert "keyframe_generation_bridge" in human_gate_source
    assert "promoteVisualAsset" not in human_gate_source
    assert "AFS_ALLOW_REMOTE" not in human_gate_source

    assert "openHumanGateMenu" in node_menu
    assert "记录人工 Gate" in node_menu
    assert "humanGateTargets" in node_menu
    assert "bindHumanGateDecisionEvents" in main
    assert "runtime.recordHumanGateDecision(payload)" in main
    assert "assetCardCandidates" in script_breakdown
    assert "lastGenerationBridge" in keyframe_response
    assert "recordHumanGateDecision(payload)" in runtime_client
    assert "human-gate-popover" in styles
