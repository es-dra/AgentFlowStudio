from __future__ import annotations

from pathlib import Path


DOCS_INDEX = Path("docs/README.md")
PHASE15_ROADMAP = Path("docs/agentflow_phase15_roadmap.md")
RUNTIME_READINESS = Path("docs/agentflow_runtime_readiness.md")


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_agentflow_runtime_readiness_doc_is_discoverable() -> None:
    docs_index = _text(DOCS_INDEX)
    phase15 = _text(PHASE15_ROADMAP)

    assert RUNTIME_READINESS.exists()
    assert "agentflow_runtime_readiness.md" in docs_index
    assert "agentflow_runtime_readiness.md" in phase15


def test_agentflow_runtime_readiness_is_a_spike_not_runtime() -> None:
    readiness = _text(RUNTIME_READINESS)

    assert "Phase 15.10" in readiness
    assert "readiness spike" in readiness
    assert "does not implement Router runtime" in readiness
    assert "does not implement skill runtime" in readiness
    assert "does not implement Memory runtime" in readiness
    assert "does not execute workflows" in readiness


def test_agentflow_runtime_readiness_requires_gates_before_runtime() -> None:
    readiness = _text(RUNTIME_READINESS)

    for gate in [
        "contract gate",
        "artifact gate",
        "review gate",
        "feedback and memory gate",
        "cost-quality gate",
        "operations gate",
    ]:
        assert gate in readiness


def test_agentflow_runtime_readiness_defines_no_go_conditions() -> None:
    readiness = _text(RUNTIME_READINESS)

    assert "Do not start runtime work if" in readiness
    assert "schema_version" in readiness
    assert "candidate memory" in readiness
    assert "router decision" in readiness
    assert "feedback_signal_log" in readiness
    assert "cost_quality_trace" in readiness
