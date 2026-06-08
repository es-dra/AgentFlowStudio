from __future__ import annotations

from pathlib import Path


DOCS_INDEX = Path("docs/README.md")
MAIN_ROADMAP = Path("docs/product_roadmap.md")
PHASE15_ROADMAP = Path("docs/agentflow_phase15_roadmap.md")
LOCAL_ALPHA_0_3_GOALS = Path("docs/local_alpha_0_3_validation_goals.md")
LOCAL_ALPHA_0_4_GOALS = Path("docs/local_alpha_0_4_product_loop_goals.md")
LOCAL_ALPHA_0_4_SCENARIO = Path("docs/local_alpha_0_4_scenario_package.md")
LOCAL_ALPHA_0_4_ACCEPTANCE = Path("docs/local_alpha_0_4_acceptance_reconciliation.md")
TASK_BRIEFS_INDEX = Path("docs/task_briefs/README.md")
WORKBENCH_REDESIGN = Path("docs/workbench/AFS-WORKBENCH-REDESIGN-001.md")
WORKBENCH_IMPLEMENTATION = Path("docs/task_briefs/AFS-WORKBENCH-IMPLEMENTATION-001.md")


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


def test_phase15_roadmap_records_asset_reuse_dry_run_planner() -> None:
    phase15 = _text(PHASE15_ROADMAP)

    assert "Phase 15.26" in phase15
    assert "AgentFlow Production Asset Reuse Dry-run Planner" in phase15
    assert "agentflow_production_asset_reuse_dry_run_plan" in phase15
    assert "does not execute asset reuse" in phase15


def test_phase15_roadmap_records_asset_reuse_review_surface() -> None:
    phase15 = _text(PHASE15_ROADMAP)

    assert "Phase 15.27" in phase15
    assert "AgentFlow Production Asset Reuse Review Surface" in phase15
    assert "agentflow_production_asset_reuse_review" in phase15
    assert "reviews existing in-memory review, validation, gate, and dry-run plan" in phase15


def test_phase15_roadmap_records_asset_reuse_chain_fixtures() -> None:
    phase15 = _text(PHASE15_ROADMAP)

    assert "Phase 15.28" in phase15
    assert "AgentFlow Production Asset Reuse Chain Fixtures" in phase15
    assert "build_agentflow_production_asset_reuse_dry_run_chain" in phase15
    assert "does not define a new contract artifact type" in phase15


def test_phase15_roadmap_records_asset_reuse_chain_audit_smoke() -> None:
    phase15 = _text(PHASE15_ROADMAP)

    assert "Phase 15.29" in phase15
    assert "AgentFlow Production Asset Reuse Chain Audit Smoke" in phase15
    assert "audit_agentflow_production_asset_reuse_chain_fixture" in phase15
    assert "does not register a new contract artifact type" in phase15


def test_old_local_alpha_docs_are_retired_from_current_doc_surface() -> None:
    docs_index = _text(DOCS_INDEX)
    task_briefs_index = _text(TASK_BRIEFS_INDEX)

    for path in [
        LOCAL_ALPHA_0_3_GOALS,
        LOCAL_ALPHA_0_4_GOALS,
        LOCAL_ALPHA_0_4_SCENARIO,
        LOCAL_ALPHA_0_4_ACCEPTANCE,
        Path("docs/local_alpha_0_2_acceptance.md"),
    ]:
        assert not path.exists()
        assert path.name not in docs_index
        assert path.name not in task_briefs_index


def test_legacy_web_bridge_briefs_are_retired_from_current_task_surface() -> None:
    task_briefs_index = _text(TASK_BRIEFS_INDEX)

    for brief in [
        "AFS-WEB-UX-001.md",
        "AFS-WEB-REVIEW-001.md",
        "AFS-WEB-OPERATOR-002.md",
    ]:
        assert brief not in task_briefs_index
        assert not (Path("docs/task_briefs") / brief).exists()
    for handoff in [
        "AFS-WEB-UX-001.md",
        "AFS-WEB-REVIEW-001.md",
        "AFS-WEB-OPERATOR-002.md",
        "AFS-WEB-REPLAY.md",
    ]:
        assert not (Path("docs/handoff") / handoff).exists()


def test_memory_workbench_redesign_is_discoverable_and_loop_focused() -> None:
    docs_index = _text(DOCS_INDEX)
    task_briefs_index = _text(TASK_BRIEFS_INDEX)
    design = _text(WORKBENCH_REDESIGN)

    assert WORKBENCH_REDESIGN.exists()
    assert "workbench/AFS-WORKBENCH-REDESIGN-001.md" in docs_index
    assert "../workbench/AFS-WORKBENCH-REDESIGN-001.md" in task_briefs_index
    for label in [
        "Project",
        "Assets",
        "Memory Loaded",
        "Baseline Run",
        "Memory-backed Run",
        "Review",
        "Feedback",
        "Next Pass",
    ]:
        assert label in design
    for state in [
        "no plan",
        "planned",
        "generating",
        "review ready",
        "feedback captured",
        "memory candidate drafted",
        "promotion decision ready",
        "blocked",
    ]:
        assert state in design
    for boundary in [
        "no SaaS",
        "no provider calls",
        "no automatic directory scanning",
        "no durable Memory runtime",
        "no browser persistence",
    ]:
        assert boundary in design
    for provenance in [
        "what memory was loaded",
        "why it was eligible",
        "which prompt/request projection it produced",
        "what feedback will change next time",
    ]:
        assert provenance in design
    assert "generic dashboard" not in design.lower()


def test_memory_workbench_implementation_brief_scopes_static_first_screen() -> None:
    task_briefs_index = _text(TASK_BRIEFS_INDEX)
    brief = _text(WORKBENCH_IMPLEMENTATION)

    assert WORKBENCH_IMPLEMENTATION.exists()
    assert "AFS-WORKBENCH-IMPLEMENTATION-001.md" in task_briefs_index
    for phrase in [
        "agentflow_memory_video_pipeline_package",
        "static first-screen view",
        "Project",
        "Assets",
        "Memory Loaded",
        "Baseline Run",
        "Memory-backed Run",
        "Review",
        "Feedback",
        "Next Pass",
        "no plan",
        "planned",
        "generating",
        "review ready",
        "feedback captured",
        "memory candidate drafted",
        "promotion decision ready",
        "blocked",
        "memory provenance panel",
        "no provider calls",
        "Runtime Service / local artifact only",
        "no automatic directory scanning",
        "no browser persistence",
        "Browser screenshot",
    ]:
        assert phrase in brief
    assert "AFS_ALLOW_REMOTE_IMAGE=true" not in brief
    assert "AFS_ALLOW_REMOTE_VIDEO=true" not in brief
