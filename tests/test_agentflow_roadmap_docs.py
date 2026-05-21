from __future__ import annotations

from pathlib import Path


DOCS_INDEX = Path("docs/README.md")
MAIN_ROADMAP = Path("docs/product_roadmap.md")
PHASE15_ROADMAP = Path("docs/agentflow_phase15_roadmap.md")


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_product_roadmap_stays_short_and_links_phase15_detail() -> None:
    roadmap = _text(MAIN_ROADMAP)

    assert MAIN_ROADMAP.exists()
    assert len(roadmap.splitlines()) <= 300
    assert "agentflow_phase15_roadmap.md" in roadmap
    assert "Phase 15.8: AgentFlow PR Review Checklist" not in roadmap


def test_phase15_roadmap_is_discoverable() -> None:
    docs_index = _text(DOCS_INDEX)

    assert PHASE15_ROADMAP.exists()
    assert "agentflow_phase15_roadmap.md" in docs_index


def test_phase15_roadmap_preserves_completed_phase_history() -> None:
    phase15 = _text(PHASE15_ROADMAP)

    for phase in [
        "Phase 15.1",
        "Phase 15.2",
        "Phase 15.3",
        "Phase 15.4",
        "Phase 15.5",
        "Phase 15.6",
        "Phase 15.7",
        "Phase 15.8",
    ]:
        assert phase in phase15


def test_phase15_roadmap_keeps_mainline_boundaries_explicit() -> None:
    phase15 = _text(PHASE15_ROADMAP)

    assert "contract-first" in phase15
    assert "does not implement AgentFlow runtime" in phase15
    assert "no Router runtime" in phase15
    assert "no skill runtime" in phase15
    assert "no Memory runtime" in phase15
    assert "no Web UI" in phase15
