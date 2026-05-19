# NarratoCut Docs

Use this page as the current navigation surface. NarratoCut is now a
local-first CLI product MVP with an agent-readable artifact chain. The main
documentation goal is to make the product path, quality gates, and agent
contracts obvious without reading every historical phase note.

## Current Product State

- [Current architecture](current_architecture.md)
- [Product roadmap](product_roadmap.md)
- [Golden Path](golden_path.md)
- [Phase 14 local ASR product acceptance](product_acceptance_phase14_local_asr.md)

## Recommended Product Workflows

- `workflows/video_to_finished_package_local_asr.yaml`
  - Use when the user has only a source video.
  - Local-first; no remote ASR by default.
  - Writes `finished_package_manifest.json` and `package_report.md`.
- `workflows/video_script_to_finished_package_local_asr.yaml`
  - Use when the user has a source video plus script.
  - Aligns script highlights to ASR transcript timestamps.
  - Writes `script_highlight_alignment.json`, `finished_package_manifest.json`,
    and `package_report.md`.

For final acceptance, run `inspect-run` and `review-run`, then refresh
`package_report.md` with `ncut package-report --run-dir <run_dir>` so the
Markdown report includes the final quality and review status.

Agent-facing task contracts live in [`../skills`](../skills/README.md).

## Contracts

- [Run contract](run_contract.md)
- [Workspace contract](workspace_contract.md)
- [Tool contracts](tool_contracts.md)
- [Agent reviewer contract](agent_reviewer_contract.md)
- [Workflow plan contract](workflow_plan_contract.md)

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
