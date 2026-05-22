from __future__ import annotations

from pathlib import Path


PLAN_DOC = Path("docs/agentflow_architecture_refactor_plan.md")
DOCS_INDEX = Path("docs/README.md")
PHASE15_ROADMAP = Path("docs/agentflow_phase15_roadmap.md")
PRODUCT_ROADMAP = Path("docs/product_roadmap.md")


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_architecture_refactor_plan_defines_target_package_boundaries() -> None:
    text = _text(PLAN_DOC)

    assert "Phase 15.14" in text
    assert "agentflow/" in text
    assert "narratostudio/" in text
    assert "narratocut/" in text
    assert "platform contract layer" in text
    assert "module-owned domain logic" in text


def test_architecture_refactor_plan_lists_migration_order_and_compatibility_strategy() -> None:
    text = _text(PLAN_DOC)

    for phrase in [
        "Step 1: introduce platform package skeleton",
        "Step 2: move pure contract utilities",
        "Step 3: split AgentFlow harness validators",
        "Step 4: expose compatibility imports",
        "Step 5: update docs and examples",
        "Step 6: add memory and asset contract validators",
        "compatibility import",
        "deprecation window",
    ]:
        assert phrase in text


def test_architecture_refactor_plan_contains_regression_matrix() -> None:
    text = _text(PLAN_DOC)

    for phrase in [
        "Contract example tests",
        "Router dry-run validator",
        "Skill replay validator",
        "NarratoStudio workflow smoke",
        "NarratoCut delivery readiness",
        "CLI help/version",
    ]:
        assert phrase in text


def test_architecture_refactor_plan_keeps_planning_only_boundary() -> None:
    text = _text(PLAN_DOC)

    for phrase in [
        "does not move Python modules",
        "does not change workflow execution",
        "does not add Router runtime",
        "does not add skill runtime",
        "does not add Memory runtime",
        "does not rename the CLI",
    ]:
        assert phrase in text


def test_architecture_refactor_plan_is_discoverable_from_roadmaps_and_docs_index() -> None:
    docs_index = _text(DOCS_INDEX)
    phase15 = _text(PHASE15_ROADMAP)
    product = _text(PRODUCT_ROADMAP)

    assert "agentflow_architecture_refactor_plan.md" in docs_index
    assert "Phase 15.14" in phase15
    assert "Architecture Refactor Plan" in phase15
    assert "architecture refactor plan" in product
