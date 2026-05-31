# AFS-MEMORY-PIPELINE-MVP-001

Status: no-call protocol runner, explicit-artifact review, bounded human
observation, presentation package, feedback-event draft, and one-command
package slices complete.

## What Changed

- Added `agentflow.memory.video_pipeline` as a generic no-call planner for a
  baseline versus memory-backed video experiment.
- Added `memory-video-pipeline-plan` CLI.
- Added `agentflow.memory.video_pipeline_review` for side-effect-free review
  artifacts from explicit I2V manifest references.
- Added `memory-video-pipeline-review` CLI.
- Added `agentflow.memory.video_pipeline_observation` for bounded human visual
  observation artifacts on top of review JSON.
- Added `memory-video-pipeline-observe` CLI.
- Added `agentflow.memory.video_pipeline_presentation` for presentation-facing
  summaries from protocol, review, and observation JSON.
- Added `memory-video-pipeline-present` CLI.
- Added `agentflow.memory.video_pipeline_feedback` for an
  `agentflow_feedback_event` draft derived from bounded observation evidence.
- Added `agentflow.memory.video_pipeline_workflow` as the no-call package
  orchestrator that links plan, review, observation, presentation, and feedback
  draft artifacts.
- Added `memory-video-pipeline-package` CLI.
- Added a sanitized protocol example at
  `examples/agentflow/memory_video_pipeline_protocol.example.json`.
- Registered the protocol example in AgentFlow contract examples and registry.

## Current Capability

The command:

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main memory-video-pipeline-plan --protocol examples\agentflow\memory_video_pipeline_protocol.example.json --output data\processed\runs\memory_video_pipeline\no_call_plan
```

writes:

- `protocol_summary.json`
- `request_plan.json`
- `review_plan.json`
- `run_plan.json`
- `memory_video_pipeline_report.md`

Provider calls are not started. Outputs are written under ignored
`data/processed/`.

The review command:

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main memory-video-pipeline-review --protocol examples\agentflow\memory_video_pipeline_protocol.example.json --artifacts data\processed\runs\memory_video_pipeline\recording_016_review\artifact_manifest.json --output data\processed\runs\memory_video_pipeline\recording_016_review
```

writes:

- `memory_video_pipeline_review.json`
- `memory_video_pipeline_review.md`

The artifact manifest must list concrete I2V manifest paths explicitly. The
review command does not scan directories and does not start provider calls.

The observation command:

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main memory-video-pipeline-observe --review data\processed\runs\memory_video_pipeline\recording_016_review\memory_video_pipeline_review.json --notes data\processed\runs\memory_video_pipeline\recording_016_observation\human_observation_notes.json --output data\processed\runs\memory_video_pipeline\recording_016_observation
```

writes:

- `memory_video_pipeline_human_observation.json`
- `memory_video_pipeline_human_observation.md`

This records the current human visual observation that the baseline repeats
varied more while memory-backed repeats stayed more stable. It is a bounded
visual signal, not human product acceptance or business validation.

The presentation command:

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main memory-video-pipeline-present --protocol examples\agentflow\memory_video_pipeline_protocol.example.json --review data\processed\runs\memory_video_pipeline\recording_016_review\memory_video_pipeline_review.json --observation data\processed\runs\memory_video_pipeline\recording_016_observation\memory_video_pipeline_human_observation.json --output data\processed\runs\memory_video_pipeline\recording_016_presentation
```

writes:

- `memory_video_pipeline_presentation_package.json`
- `memory_video_pipeline_presentation_brief.md`
- `slidev_insert.md`

This package is for competition/Slidev material. It summarizes the evidence but
does not copy generated videos or claim final proof.

The package command:

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main memory-video-pipeline-package --protocol examples\agentflow\memory_video_pipeline_protocol.example.json --artifacts data\processed\runs\memory_video_pipeline\recording_016_review\artifact_manifest.json --notes data\processed\runs\memory_video_pipeline\recording_016_observation\human_observation_notes.json --created-at 2026-05-30T09:00:00+08:00 --output data\processed\runs\memory_video_pipeline\package_example_build
```

writes one end-to-end no-call package:

- `plan/`
- `review/`
- `observation/`
- `presentation/`
- `feedback/memory_video_pipeline_feedback_event_draft.json`
- `feedback/memory_video_pipeline_feedback_event_draft.jsonl`
- `feedback/memory_video_pipeline_feedback_event_draft.md`
- `memory_video_pipeline_package_summary.json`

The feedback event is a draft only. It does not write to durable Memory runtime
and does not replace `feedback.jsonl` as the feedback source of truth.

## Safety Boundaries

- No provider calls.
- No generated media committed.
- No provider credentials, bearer headers, signed URLs, data URLs, or absolute
  local media paths persisted.
- No durable Memory runtime, DB, vector store, hosted service, or RAG.
- No human acceptance, business validation, or quality-improvement claim.
- Feedback-event draft is not persisted as durable company memory.

## Implemented Checks

- Protocol must be `agentflow_memory_video_pipeline_protocol` with schema
  version `0.1.0`.
- Baseline and memory-backed lanes must share the same user task, source
  assets, provider route, duration, and script.
- Only memory cards with `promotion_status` `promoted` or `merged` can enter
  context.
- Memory cards must keep `writes_long_term_memory: false`.
- Protocol text is rejected when it contains obvious local paths, provider
  credentials, bearer tokens, signed URL fragments, or data URLs.
- Review plan includes cross-run stability fields for repeated-run evidence.
- Review artifacts require every expected lane for each listed run.
- Review artifacts reject provider URLs, signed URLs, data URLs, absolute local
  video paths, bearer headers, and obvious provider key fragments.
- Review artifacts record source-image hash parity, lane repeat counts, output
  hashes, storyboard checkpoints, and the review rubric without copying media.
- Observation artifacts require all review fields to be covered and support
  only bounded verdict labels: `memory_backed_stronger`, `baseline_stronger`,
  `mixed`, or `no_clear_difference`.
- Observation artifacts reject provider URLs, generated media paths, local
  absolute paths, bearer headers, signed URLs, and obvious provider key
  fragments.
- The CLI accepts PowerShell UTF-8 BOM JSON inputs.
- Presentation artifacts reject provider URLs, generated media paths, local
  absolute paths, bearer headers, signed URLs, and obvious provider key
  fragments.
- Presentation tests validate the real UTF-8 content of generated Chinese
  Slidev insert text. PowerShell console output can display Chinese as
  mojibake, so file-level UTF-8 checks are the authority.
- Package artifacts link the no-call chain and include an explicit feedback
  event draft with `writes_long_term_memory: false`.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_memory_video_pipeline_protocol.py tests/test_contract_examples.py -q
# 31 passed

.\.venv\Scripts\python.exe -m apps.cli.main memory-video-pipeline-plan --protocol examples\agentflow\memory_video_pipeline_protocol.example.json --output data\processed\runs\memory_video_pipeline\no_call_plan
# succeeded; provider calls not started

.\.venv\Scripts\python.exe -m compileall agentflow\memory apps\cli
# passed

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed; lists memory-video-pipeline-plan

.\.venv\Scripts\python.exe -m pytest tests/test_memory_video_pipeline_review.py -q
# 6 passed

.\.venv\Scripts\python.exe -m apps.cli.main memory-video-pipeline-review --protocol examples\agentflow\memory_video_pipeline_protocol.example.json --artifacts data\processed\runs\memory_video_pipeline\recording_016_review\artifact_manifest.json --output data\processed\runs\memory_video_pipeline\recording_016_review
# succeeded; reviewed 2 repeated runs; provider calls not started

.\.venv\Scripts\python.exe -m pytest tests/test_memory_video_pipeline_observation.py tests/test_contract_examples.py tests/test_agentflow_contract_audit.py -q
# 36 passed

.\.venv\Scripts\python.exe -m apps.cli.main memory-video-pipeline-observe --review data\processed\runs\memory_video_pipeline\recording_016_review\memory_video_pipeline_review.json --notes data\processed\runs\memory_video_pipeline\recording_016_observation\human_observation_notes.json --output data\processed\runs\memory_video_pipeline\recording_016_observation
# succeeded; provider calls not started

.\.venv\Scripts\python.exe -m pytest tests/test_memory_video_pipeline_presentation.py -q
# 3 passed

.\.venv\Scripts\python.exe -m apps.cli.main memory-video-pipeline-present --protocol examples\agentflow\memory_video_pipeline_protocol.example.json --review data\processed\runs\memory_video_pipeline\recording_016_review\memory_video_pipeline_review.json --observation data\processed\runs\memory_video_pipeline\recording_016_observation\memory_video_pipeline_human_observation.json --output data\processed\runs\memory_video_pipeline\recording_016_presentation
# succeeded; provider calls not started

.\.venv\Scripts\python.exe -m pytest tests/test_memory_video_pipeline_workflow.py tests/test_contract_examples.py tests/test_agentflow_contract_helpers.py -q
# 35 passed

.\.venv\Scripts\python.exe -m apps.cli.main memory-video-pipeline-package --protocol examples\agentflow\memory_video_pipeline_protocol.example.json --artifacts data\processed\runs\memory_video_pipeline\recording_016_review\artifact_manifest.json --notes data\processed\runs\memory_video_pipeline\recording_016_observation\human_observation_notes.json --created-at 2026-05-30T09:00:00+08:00 --output data\processed\runs\memory_video_pipeline\package_example_build
# succeeded; provider calls not started; feedback event draft written
```

## Next Work

The next slice should design the workbench surface around this package contract
or wire optional live image/I2V execution through the existing MiniMax/Kling
gates. Do not create another `memory_advantage_demo_XXX` module.
