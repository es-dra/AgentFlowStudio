from __future__ import annotations

from studio_static_helpers import STUDIO_ROOT


def test_studio_visual_asset_promotion_sends_accepted_human_gate_provenance() -> None:
    panel = (STUDIO_ROOT / "src" / "panels" / "visual-asset-panel.js").read_text(encoding="utf-8")
    provenance = (STUDIO_ROOT / "src" / "human-gate-provenance.js").read_text(encoding="utf-8")

    assert "promotionGateProvenance(node)" in panel
    assert "source_human_gate_id" in provenance
    assert "source_asset_card_candidate_id" in provenance
    assert "accepted_for_next_step" in provenance
    assert "asset_card_candidate" in provenance
    assert "provider" not in provenance.lower()
