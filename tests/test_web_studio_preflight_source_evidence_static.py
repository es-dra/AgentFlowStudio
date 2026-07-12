from __future__ import annotations

from pathlib import Path


STUDIO_ROOT = Path("apps/studio")


def test_studio_preflight_modal_surfaces_source_evidence_without_runtime_calls() -> None:
    helper = (STUDIO_ROOT / "src" / "generation-preflight-source-evidence.js").read_text(encoding="utf-8")
    guards = (STUDIO_ROOT / "src" / "node-generation-guards.js").read_text(encoding="utf-8")

    assert "included_asset_source_evidence_refs" in helper
    assert "source_human_gate_id" in helper
    assert "source_asset_card_candidate_id" in helper
    assert "preflightSourceEvidenceSummaryText(preflight)" in guards
    assert "carry-muted" in guards
    assert "from \"./asset-reference-summary.js\"" in guards + helper
    assert "fetch(" not in helper
    assert "requestJson" not in helper
    assert "data_base64" not in helper
    assert "signed_url" not in helper
