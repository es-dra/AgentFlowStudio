# Agent Reviewer Contract

Phase 7.6 adds a read-only review layer for workflow run directories.

The reviewer turns an existing run into an agent-readable report:

```text
run directory -> review_report.json
```

It does not execute workflows, call FFmpeg, call remote LLMs, modify original
run artifacts, retry failed steps, auto-fix files, or control an autonomous
agent.

## Inputs

The reviewer reads an existing run directory. For the full mock workflow, the
expected inputs are:

```text
run_manifest.json
trace.json
quality_report.json
hooks.json
scripts.json
clip_plans.json
slice_manifest.json
clips/
```

`run_manifest.json` is used as the source of artifact references when available.
This keeps the reviewer aligned with the run contract instead of hard-coding a
separate artifact list.

## Output

The reviewer writes:

```text
review_report.json
```

The report is intended for future agent or external-system consumption. Paths
use `/` separators so the report remains stable across platforms.

Example shape:

```json
{
  "schema_version": "0.1",
  "run_id": "demo_full_mock",
  "status": "passed",
  "quality_level": "engineering_pass",
  "delivery_status": "pass",
  "summary": {
    "total_checks": 12,
    "passed": 12,
    "failed": 0,
    "warnings": 0
  },
  "inputs": {
    "run_dir": "data/processed/runs/demo_full_mock",
    "manifest": "run_manifest.json",
    "trace": "trace.json",
    "quality_report": "quality_report.json"
  },
  "sections": [
    {
      "name": "run_contract",
      "status": "passed",
      "checks": []
    },
    {
      "name": "workflow_outputs",
      "status": "passed",
      "checks": []
    }
  ],
  "recommendations": []
}
```

## Status Rules

Report status values:

- `passed`
- `warning`
- `failed`

Aggregation rule:

```text
any failed check -> failed
no failed checks but at least one warning -> warning
all checks passed -> passed
```

`quality_level` values:

- `engineering_pass`: checks passed for an engineering workflow run.
- `product_mvp`: checks passed for a finished-package product run.
- `needs_review`: failed or warning state requires human or agent review.

`delivery_status` values:

- `pass`
- `warning`
- `failed`

CLI exit behavior:

- `passed`: exit code 0
- `warning`: exit code 0
- `failed`: exit code 1

## Checks

The first version keeps checks intentionally small.

Run contract checks:

- `run_manifest.json` exists
- `trace.json` exists
- `quality_report.json` exists
- `trace.json` contains at least one step
- `quality_report.json` has no failed checks

Workflow output checks:

- artifact references declared in `run_manifest.json` exist in the run directory

Video artifact checks are added when `run_manifest.json` declares a Phase 11
video quality profile such as `mock_asr_transcript`, `real_asr_transcript`,
`video_highlight_clip_plan`, or `real_asr_highlight_clip_plan`.

The `video_artifacts` section checks:

- `audio_manifest.json` exists and its mock/FFmpeg execution status is explicit
- `audio/audio.wav` exists when declared by the audio manifest
- `transcript.json` validates against the `Transcript` schema
- transcript segments are non-empty, timestamped, monotonic, and text-bearing
- transcript metadata identifies the ASR provider
- explicit real-ASR runs do not record obvious API secret values in run artifacts
- video-to-highlight runs keep highlight and clip source segment IDs aligned
  with transcript segment IDs

Video-to-highlight runs still include the existing `highlight_artifacts` section
for HighlightPlan and ClipPlan checks. The reviewer does not call ASR, FFmpeg,
remote LLMs, slicing, or assembly.

## CLI

Generate a review report:

```powershell
.venv\Scripts\ncut review-run --run-dir data/processed/runs/demo_full_mock
```

Expected output shape:

```text
Review report: data/processed/runs/demo_full_mock/review_report.json
Status: passed
Checks: 12 passed / 0 failed / 0 warnings
```

## Relationship To `inspect-run`

`inspect-run` is the human and CI-facing inspection command. It reads run
artifacts, performs harness quality checks, and writes `quality_report.json`.

`review-run` is the agent-readable reporting command. It reads the run contract
and quality artifacts, then writes `review_report.json`.

`review-run` does not generate `quality_report.json`. If that file is missing,
the run contract section fails with an explicit instruction to run
`inspect-run` first.

In normal usage:

```text
run-workflow -> inspect-run -> review-run
```

`run-workflow` already calls `inspect-run` for the default CLI workflow path, so
a freshly generated mock workflow run can usually be reviewed directly.
