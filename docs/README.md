# AgentFlow Studio Docs

Use this page as the current navigation surface. AgentFlow Studio is the
platform repository. NarratoCut is the distribution-side short video highlight
workflow module, NarratoStudio is the production-side structured handoff
module, and `agentflow/` is the platform contract and harness migration layer.
The main documentation goal is to make the product path, quality gates, and
agent contracts obvious without reading every historical phase note.

## Current Product State

- [Current architecture](current_architecture.md)
- [Product roadmap](product_roadmap.md)
- [AgentFlow Phase 15 roadmap](agentflow_phase15_roadmap.md)
- [Company operating model projection](company_operating_model.md)
- [Agent operating roster](agent_operating_roster.md)
- [Agent task brief template](agent_task_brief_template.md)
- [Current task briefs](task_briefs/README.md)
- [Post-v0.1.0 plan](post_v0_1_0_plan.md)
- [NarratoStudio contracts](narratostudio_contracts.md)
- [NarratoCut v0.1.0 delivery checklist](narratocut_delivery_checklist.md)
- [Golden Path](golden_path.md)
- [Golden Sample v0.1.0](golden_sample_v0_1_0.md)
- [Alpha readiness report](alpha_readiness_report.md)
- [Local Alpha 0.2 acceptance package](local_alpha_0_2_acceptance.md)
- [Local Alpha 0.3 validation goals](local_alpha_0_3_validation_goals.md)
- [Phase 14 local ASR product acceptance](product_acceptance_phase14_local_asr.md)
- [Phase 14.4B elastic boundary acceptance](product_acceptance_phase14_4b_elastic_boundaries.md)
- [Phase 14.4E audio boundary refinement acceptance](product_acceptance_phase14_4e_audio_boundary_refinement.md)
- [Phase 14.6 delivery readiness acceptance](product_acceptance_phase14_6_delivery_readiness.md)

## Recommended Product Workflows

- `workflows/video_to_finished_package_local_asr.yaml`
  - Use when the user has only a source video.
  - Local-first; no remote ASR by default.
  - Writes `boundary_signal_manifest.json`, `finished_package_manifest.json`,
    `selection_diagnostics.json`, and `package_report.md`.
- `workflows/video_script_to_finished_package_local_asr.yaml`
  - Use when the user has a source video plus script.
  - Aligns script highlights to ASR transcript timestamps.
  - Writes `script_highlight_alignment.json`, `boundary_signal_manifest.json`,
    `selection_diagnostics.json`, `finished_package_manifest.json`, and
    `package_report.md`.

For final acceptance, run `inspect-run` and `review-run`, then refresh
`package_report.md` with `ncut package-report --run-dir <run_dir>` so the
Markdown report includes the final quality and review status.

For release or handoff readiness across the current video-only and video+script
paths, summarize refreshed product runs with:

```powershell
.venv\Scripts\ncut delivery-readiness --run-dir <video_only_run> --run-dir <video_script_run> --output <report_dir>
```

This writes `delivery_readiness.json` and `delivery_readiness.md`.

For a read-only Alpha smoke/status summary that does not call providers or
write run artifacts, use:

```powershell
python -m apps.cli.main alpha-smoke
python -m apps.cli.main alpha-smoke --json
```

This reports the current NarratoStudio handoff, NarratoCut package, and
PosterFlow provider-readiness state as `pass`, `blocked`, or `fail` and points
back to [`alpha_readiness_report.md`](alpha_readiness_report.md).

Agent-facing task contracts live in [`../skills`](../skills/README.md).
Operational agent guidance lives in
[`agent_usage_guide.md`](agent_usage_guide.md). Development agent roles and
parallel dispatch rules live in
[`agent_operating_roster.md`](agent_operating_roster.md).

NarratoStudio is now represented as a sibling MVP module for the production
side. Its first workflow is a local-first structured production handoff
generator, documented in
[`narratostudio_contracts.md`](narratostudio_contracts.md).

## Contracts

- [AgentFlow Studio architecture](agentflow_studio_architecture.md)
- [Module boundary](module_boundary.md)
- [AgentFlow artifact map](agentflow_artifact_map.md)
- [AgentFlow intermediate asset architecture](agentflow_intermediate_asset_architecture.md)
- [AgentFlow architecture refactor plan](agentflow_architecture_refactor_plan.md)
- [AgentFlow contract registry](agentflow_contract_registry.md)
- [AgentFlow contract validation](agentflow_contract_validation.md)
- [AgentFlow PR review checklist](agentflow_pr_review_checklist.md)
- [AgentFlow runtime readiness](agentflow_runtime_readiness.md)
- [AgentFlow memory contract](agentflow_memory_contract.md)
- [AgentFlow skill contract](agentflow_skill_contract.md)
- [AgentFlow router contract](agentflow_router_contract.md)
- [Run contract](run_contract.md)
- [Workspace contract](workspace_contract.md)
- [Tool contracts](tool_contracts.md)
- [Agent reviewer contract](agent_reviewer_contract.md)
- [Workflow plan contract](workflow_plan_contract.md)
- [Project manifest contract](project_manifest_contract.md)
- [Feedback contract](feedback_contract.md)
- [Platform profile contract](platform_profile_contract.md)
- [NarratoStudio contracts](narratostudio_contracts.md)
- [Asset lifecycle](asset_lifecycle.md)

## Quality And Acceptance

- [Product quality smoke](product_quality_smoke.md)
- [Phase 13 product smoke](product_smoke_phase13.md)
- [Viral clip quality plan](viral_clip_quality_plan.md)

## Design Notes

- [Highlight detection design](highlight_detection_design.md)
- [Real slicing design](real_slicing_design.md)
- [Real video workflow demo](real_video_workflow_demo.md)
- [Video assembly design](video_assembly_design.md)

## Historical Context

Older phase docs remain useful for implementation rationale, but new product,
agent, or UI work should start from the current product state and contract docs
above.
