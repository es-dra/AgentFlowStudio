# AFS-POSTER-LIVE-001 Handoff

## Status

`BLOCKED`: local image-provider environment is not configured.

This branch does not run a live provider call. It records the safe checklist for
running the PosterFlow live smoke later.

## Environment Readiness

Checked without printing secrets:

```text
AFS_ALLOW_REMOTE_IMAGE=unset
AFS_IMAGE_PROVIDER=unset
AFS_IMAGE_BASE_URL=unset
AFS_IMAGE_API_KEY=unset
AFS_IMAGE_MODEL=unset
```

## Local-Only Setup Checklist

Set variables only in the local shell or local ignored config. Do not paste keys
into chat and do not commit config files.

```powershell
$env:AFS_ALLOW_REMOTE_IMAGE="true"
$env:AFS_IMAGE_PROVIDER="minimax"
$env:AFS_IMAGE_BASE_URL="<local-provider-base-url>"
$env:AFS_IMAGE_API_KEY="<set-in-local-shell-only>"
$env:AFS_IMAGE_MODEL="image-01"
```

Then run:

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main run-workflow --workflow workflows/posterflow_memory_demo.yaml --input examples/posterflow/poster_brief.example.json --output data/processed/poster_runs/cyber_xianxia_001/live_001
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main inspect-run --run-dir data/processed/poster_runs/cyber_xianxia_001/live_001
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main review-run --run-dir data/processed/poster_runs/cyber_xianxia_001/live_001
```

Expected local-only evidence:

- `poster_model_invocations.json`
- `poster_candidates_manifest.json`
- `round_2/poster_candidates_manifest.json`
- `poster_round_comparison.json`
- `poster_two_round_report.md`
- `quality_report.json`
- `review_report.json`

Do not stage generated images, provider responses that contain private URLs, or
the run directory.

## No-Secret Review

Before committing any later live-smoke note:

```powershell
git status --short
git diff --cached --name-only
rg -n "API_KEY|SECRET|TOKEN|COOKIE|Authorization|Bearer|signed_url|https?://.*(token|signature|expires)" docs TASK_TRACKER.md DEVLOG.md
```

The expected commit should include only docs, tracker, or DEVLOG updates.

## Product Boundary

A live smoke proves the configured provider path can return artifacts. It does
not prove:

- mature creative quality;
- provider cost-quality optimization;
- durable Memory runtime;
- business validation.
