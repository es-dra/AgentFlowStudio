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


def test_local_alpha_0_3_validation_goals_are_discoverable() -> None:
    docs_index = _text(DOCS_INDEX)
    task_briefs_index = _text(TASK_BRIEFS_INDEX)
    goals = _text(LOCAL_ALPHA_0_3_GOALS)

    assert LOCAL_ALPHA_0_3_GOALS.exists()
    assert "local_alpha_0_3_validation_goals.md" in docs_index
    assert "local_alpha_0_3_validation_goals.md" in task_briefs_index
    assert "repeatable\nlocal operator loop" in goals
    assert "AFS-WEB-REVIEW-001" in goals
    assert "AFS-MEMORY-RUNTIME-001" in goals


def test_local_alpha_0_3_task_briefs_exist() -> None:
    for brief in [
        "AFS-PROD-NEXT-001.md",
        "AFS-WEB-REVIEW-001.md",
        "AFS-MEMORY-RUNTIME-001.md",
        "AFS-POSTER-LIVE-002.md",
    ]:
        assert (Path("docs/task_briefs") / brief).exists()


def test_local_alpha_0_4_product_loop_goals_are_discoverable() -> None:
    docs_index = _text(DOCS_INDEX)
    task_briefs_index = _text(TASK_BRIEFS_INDEX)
    goals = _text(LOCAL_ALPHA_0_4_GOALS)

    assert LOCAL_ALPHA_0_4_GOALS.exists()
    assert "local_alpha_0_4_product_loop_goals.md" in docs_index
    assert "local_alpha_0_4_product_loop_goals.md" in task_briefs_index
    assert "one real local product loop" in goals
    assert "local_alpha_0_4_scenario_package.md" in goals
    assert "AFS-PROD-LOOP-001" in goals
    assert "AFS-WEB-OPERATOR-002" in goals
    assert "AFS-MEMORY-QUALITY-002" in goals


def test_local_alpha_0_4_scenario_package_is_discoverable() -> None:
    docs_index = _text(DOCS_INDEX)
    task_briefs_index = _text(TASK_BRIEFS_INDEX)
    scenario = _text(LOCAL_ALPHA_0_4_SCENARIO)

    assert LOCAL_ALPHA_0_4_SCENARIO.exists()
    assert "local_alpha_0_4_scenario_package.md" in docs_index
    assert "local_alpha_0_4_scenario_package.md" in task_briefs_index
    assert "video_script_to_finished_package_local_asr.yaml" in scenario
    assert "data/processed/local_alpha_0_4/video_script_local_asr_input.json" in scenario
    assert "AFS-RUN-PACKAGE-001 and AFS-WEB-OPERATOR-002 may run in parallel" in scenario


def test_local_alpha_0_4_acceptance_reconciliation_is_discoverable() -> None:
    docs_index = _text(DOCS_INDEX)
    task_briefs_index = _text(TASK_BRIEFS_INDEX)
    acceptance = _text(LOCAL_ALPHA_0_4_ACCEPTANCE)

    assert LOCAL_ALPHA_0_4_ACCEPTANCE.exists()
    assert "local_alpha_0_4_acceptance_reconciliation.md" in docs_index
    assert "local_alpha_0_4_acceptance_reconciliation.md" in task_briefs_index
    for label in [
        "Structure verification",
        "runtime verification",
        "human acceptance",
        "business validation",
        "provider smoke",
        "durable Memory runtime",
        "Real second-pass run",
    ]:
        assert label in acceptance
    assert "not human-accepted and\nnot business-validated" in acceptance


def test_local_alpha_0_4_task_briefs_exist() -> None:
    for brief in [
        "AFS-PROD-LOOP-001.md",
        "AFS-RUN-PACKAGE-001.md",
        "AFS-WEB-OPERATOR-002.md",
        "AFS-MEMORY-QUALITY-002.md",
        "AFS-POSTER-LIVE-002.md",
    ]:
        assert (Path("docs/task_briefs") / brief).exists()


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
        "no apps/web_bridge",
        "no automatic directory scanning",
        "no browser persistence",
        "Browser screenshot",
    ]:
        assert phrase in brief
    assert "AFS_ALLOW_REMOTE_IMAGE=true" not in brief
    assert "AFS_ALLOW_REMOTE_VIDEO=true" not in brief
