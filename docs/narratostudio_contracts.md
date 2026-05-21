# NarratoStudio Contracts

NarratoStudio MVP is a local-first structured production handoff generator.

NarratoCut remains the distribution-side module of AgentFlow Studio.
NarratoStudio is added as a sibling module under this repository for MVP
validation only. The repository is not being renamed.

## Workflow Boundary

First recommended workflow:

```text
narratostudio_brief_to_production_handoff_v0.1
content_mode: episodic_story_production
```

This workflow is for short drama, series, IP content, episode breakdown, and
commercial production handoff. It is not the only future production workflow.

The existing workflow runner is reused:

```powershell
.venv\Scripts\python.exe -m apps.cli.main run-workflow --workflow workflows/narratostudio_brief_to_production_handoff.yaml --input examples/narratostudio/creative_brief.example.json --output data/processed/runs/demo_narratostudio_handoff
```

CLI naming will be revisited when AgentFlow Studio is separated.

## Artifact Chain

| Production concept | MVP artifact | Role |
| --- | --- | --- |
| brief | `creative_brief.json` | Creation request and constraints. |
| script bible / world setting | `story_bible.json` | Characters, style, continuity rules. |
| script / outline | `episode_outline.json` | Episode structure and beats. |
| storyboard / scene design | `scene_plan.json` | Scene-level production plan. |
| shot list | `shot_plan.json` | Shot-level plan. |
| asset / prompt prep | `prompt_pack.json` | Visual generation or shooting prompts. |
| production handoff | `production_handoff.json` | Machine-readable handoff contract. |
| production report | `production_report.md` | Human-readable review surface. |

Auxiliary Agent-native artifacts:

- `memory_candidates.json`: candidate-only memories from this run.
- `cost_quality_trace.json`: local deterministic cost and quality trace.
- `feedback_signal_log.json`: derived interpretation of feedback signals.
- `execution_trace.json`: local workflow execution trace.

The workflow also writes the existing run artifacts:

- `manifest.json`
- `run_manifest.json`
- `trace.json`

`execution_trace.json` is inspired by durable execution logs, but it is not an
Agents tracing system or a durable workflow engine.

## Contract Rules

- `schema_version` must use semver and is currently `0.1.0`.
- Core contracts reject extra fields.
- Each core artifact includes `metadata`, but metadata is for non-contractual
  annotations only.
- Agents and UI must not depend on `metadata` for core behavior.
- `production_handoff.json` is the machine-readable source for downstream
  production tools.
- `production_report.md` is a rendered human review view.

## Feedback And Memory

`feedback.jsonl` remains the source of truth for human or external feedback
events.

`feedback_signal_log.json` must not be used as the primary feedback store. It is
a derived interpretation for the current run.

`memory_candidates.json` only writes:

```text
promotion_status: candidate
```

The first MVP does not auto-promote, merge, reject, expire, or write long-term
memory.

`cost_quality_trace.json` records local deterministic execution strategy and
quality proxy evidence. It helps compare future execution modes, but it is not a
claim that the generated creative content is editorially mature.

## Quality Gate

Use the standard gate sequence after a run:

```powershell
.venv\Scripts\python.exe -m apps.cli.main inspect-run --run-dir <run_dir>
.venv\Scripts\python.exe -m apps.cli.main review-run --run-dir <run_dir>
```

The `narratostudio_production_handoff` quality profile checks:

- required artifact presence
- schema version presence
- brief to bible to outline references
- outline beat to scene references and beat coverage by scenes
- shot to scene references
- scene coverage by shots
- prompt to shot references
- shot coverage by prompts
- handoff references to all core artifact IDs
- handoff artifact reference map completeness
- production report presence and light identity markers
- candidate-only memory status
- local deterministic cost trace
- derived feedback signal boundary

`production_report.md` is intentionally checked only as a human-readable
review surface. The quality profile verifies that it exists and identifies the
project/NarratoStudio handoff, but strong consistency remains in the JSON
artifacts and `production_handoff.json`.
