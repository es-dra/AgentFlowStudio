from __future__ import annotations

from pathlib import Path


ARCHITECTURE_DOC = Path("docs/agentflow_intermediate_asset_architecture.md")
PHASE15_ROADMAP = Path("docs/agentflow_phase15_roadmap.md")
PRODUCT_ROADMAP = Path("docs/product_roadmap.md")


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_intermediate_asset_architecture_doc_defines_core_chain() -> None:
    text = _text(ARCHITECTURE_DOC)

    assert "Agent action -> artifact -> feedback signal -> memory candidate -> promotion decision -> reusable asset" in text
    assert "intermediate_asset" in text
    assert "reusable_asset_profile" in text
    assert "asset_reuse_decision" in text


def test_intermediate_asset_architecture_doc_keeps_non_runtime_boundary() -> None:
    text = _text(ARCHITECTURE_DOC)

    assert "does not implement Memory runtime" in text
    assert "does not implement Router runtime" in text
    assert "does not implement skill runtime" in text
    assert "does not implement a database" in text
    assert "does not execute workflows" in text


def test_intermediate_asset_architecture_doc_anchors_narratostudio_assets() -> None:
    text = _text(ARCHITECTURE_DOC)

    for phrase in [
        "character reference",
        "style constraint",
        "prompt attempt",
        "generation result summary",
        "acceptance or rejection reason",
        "cost-quality evidence",
    ]:
        assert phrase in text


def test_phase15_and_product_roadmaps_include_phase_15_13() -> None:
    phase15 = _text(PHASE15_ROADMAP)
    product = _text(PRODUCT_ROADMAP)

    assert "Phase 15.13" in phase15
    assert "Intermediate Asset & Memory Architecture Plan" in phase15
    assert "intermediate asset architecture" in product
