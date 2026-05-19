# Workspace Contract

This document defines how NarratoCut should organize product inputs, workflow
runs, generated packages, and local cache artifacts after the local-first CLI
product MVP.

The goal is not to move every historical directory immediately. The goal is to
give humans, agents, and future Web UI code a stable interpretation of the
workspace.

## Current Product Entry

Recommended product workflows:

- `workflows/video_to_finished_package_local_asr.yaml`
- `workflows/video_script_to_finished_package_local_asr.yaml`

Recommended agent skills:

- `skills/short_highlight_package.skill.yaml`
- `skills/video_script_highlight_package.skill.yaml`

Formal product outputs:

- `finished_package_manifest.json`
- `package_report.md`
- `quality_report.json`
- `review_report.json`

## Directory Semantics

Committed directories:

```text
apps/           CLI/API/Web entrypoint shells
configs/        committed example configs and static tool catalog
docs/           product, architecture, acceptance, and contract docs
examples/       committed input examples and fixtures
narratocut/     implementation modules
prompts/        prompt templates
skills/         agent-readable task contracts
tests/          unit, workflow, and contract tests
workflows/      YAML workflow definitions
```

Ignored local directories:

```text
data/raw/                 local source media and scripts
data/models/              local model cache
data/processed/runs/      workflow run directories
data/processed/cache/     reusable ASR/OCR/frame cache
data/processed/packages/  finalized package directories
data/reports/             generated workflow plans and acceptance summaries
```

## Target Local Layout

Future cleanup should converge toward:

```text
data/
  raw/
    product_acceptance/
      video_only/
      video_script/
    user/

  processed/
    inputs/
      acceptance/
    runs/
      acceptance/
      golden_path/
      scratch/
    packages/
      latest/
      acceptance/
    cache/
      asr/
      ocr/
      frames/

  reports/
    acceptance/
    quality/
```

## Run Contract

A product run directory should be self-contained enough for inspection and
review:

```text
run_dir/
  run_manifest.json
  trace.json
  manifest.json
  transcript.json
  candidate_windows.json
  highlight_score_report.json
  highlight_plan.json
  clip_plan.json
  real_slice_manifest.json
  final_video_manifest.json
  subtitle_manifest.json
  audio_mix_manifest.json
  finished_package_manifest.json
  package_report.md
  quality_report.json
  review_report.json
  clips/
  final_video.mp4
  final_video_with_bgm.mp4
  subtitles.srt
```

## Package Contract

Agents and Web UI code should prefer package-level artifacts over ad hoc run
directory scanning.

Minimum package-facing artifacts:

```text
finished_package_manifest.json
package_report.md
quality_report.json
review_report.json
```

`finished_package_manifest.json` is the machine index. `package_report.md` is
the human and agent summary. `quality_report.json` and `review_report.json` are
the trust layer.

Workflow execution writes an initial `package_report.md`. A formal acceptance
run should execute `inspect-run`, then `review-run`, then refresh the Markdown
summary with `ncut package-report --run-dir <run_dir>` so the report captures
the final quality and review status.

## Cleanup Rules

- Do not commit media, generated packages, model cache, or run outputs.
- Do not delete ignored run directories unless their replacement run is known
  and documented.
- Prefer moving future formal acceptance runs under
  `data/processed/runs/acceptance/`.
- Historical `demo_*`, `phase*`, `closeout_*`, and `golden_path_*` runs may
  remain locally, but they should not be treated as current product truth.
- Product docs should point to the latest acceptance run names and distinguish
  verification from product validation.
