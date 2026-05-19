# Project Manifest Contract

`project_manifest.json` is a future-facing project index for agents, Web UI
viewers, and local handoff scripts. It does not replace workflow run artifacts.
It points to source assets, runs, packages, and user preferences for one
content-distribution project.

## Scope

This contract is intentionally small for `v0.1.0`.

It may be created by a human, an agent, or a future console. NarratoCut does not
yet require it to run the CLI product workflows.

## Required Fields

- `schema_version`: contract version, currently `"0.1"`.
- `project_id`: stable local project id.
- `project_type`: for NarratoCut, use `short_video_distribution`.
- `goal`: human-readable project goal.
- `source_assets`: raw or user-provided inputs.
- `workflows`: workflow entries that are planned or recommended.
- `runs`: completed or in-progress run directories.
- `packages`: finished package manifest references.
- `user_preferences`: platform and style preferences.
- `status`: `draft`, `in_progress`, `ready_for_review`, or `archived`.

## Example

See [`../examples/contracts/project_manifest.example.json`](../examples/contracts/project_manifest.example.json).

## Agent Notes

Agents should use this file as a project-level index only. For run details,
read `run_manifest.json`; for finished package details, read
`finished_package_manifest.json`, `package_report.md`, `quality_report.json`,
and `review_report.json`.
