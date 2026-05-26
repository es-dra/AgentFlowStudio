# AFS-RUN-PACKAGE-001 - Local Product Runtime Package

Status: BLOCKED
Date: 2026-05-27
Branch: `codex/afs-run-package-loop`
Worktree: `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-run-package-loop`

## Summary

The Local Alpha 0.4 runtime package lane could not execute the real product
workflow because required ignored local inputs are missing. This is a local
setup blocker, not a product acceptance failure.

The lane did not call remote providers and did not write runtime package
artifacts.

## Scenario

Shared scenario package:

```text
docs/local_alpha_0_4_scenario_package.md
```

Selected workflow:

```text
workflows/video_script_to_finished_package_local_asr.yaml
```

Expected ignored input bundle:

```text
data/processed/local_alpha_0_4/video_script_local_asr_input.json
```

## Local Input Check

| Item | Status | Meaning |
|---|---|---|
| `data/raw/demo_real_video/input.mp4` | missing | source video is not present |
| `data/raw/demo_bgm/bgm.wav` | missing | BGM audio is not present |
| `data/models/faster-whisper/` | missing | local ASR model cache is not present |
| `data/processed/local_alpha_0_4/video_script_local_asr_input.json` | missing | local operator input bundle is not present |
| FFmpeg | available | `C:\ProgramData\chocolatey\bin\ffmpeg.exe` |
| FFprobe | available | `C:\ProgramData\chocolatey\bin\ffprobe.exe` |

## Commands Run

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main alpha-smoke --json
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests/test_video_to_finished_package_local_asr_workflow.py tests/test_alpha_smoke_cli.py
```

Results:

- `alpha-smoke --json`: `status=blocked`, expected because the remote image
  provider lane is disabled by default. It reported `writes_runtime_artifacts=false`.
- Focused tests: `7 passed`.

The real workflow command was intentionally skipped because the required local
input bundle and local media/model inputs are missing.

## Next Local Setup

Create or place the ignored local inputs:

```text
data/raw/demo_real_video/input.mp4
data/raw/demo_bgm/bgm.wav
data/models/faster-whisper/
data/processed/local_alpha_0_4/video_script_local_asr_input.json
```

Use `examples/demo_asr/video_script_to_finished_package_local_asr_input.example.json`
as the schema reference for the ignored local input bundle, but keep the copied
bundle under `data/processed/local_alpha_0_4/`.

After setup, run:

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main run-workflow --workflow workflows/video_script_to_finished_package_local_asr.yaml --input data/processed/local_alpha_0_4/video_script_local_asr_input.json --output data/processed/runs/local_alpha_0_4_product_loop
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main inspect-run --run-dir data/processed/runs/local_alpha_0_4_product_loop
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main review-run --run-dir data/processed/runs/local_alpha_0_4_product_loop
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main package-report --run-dir data/processed/runs/local_alpha_0_4_product_loop
```

## Boundaries Kept

- No remote LLM, ASR, image, or video provider call.
- No generated media or runtime package artifacts committed.
- No `.env`, `.dev.vars`, `configs/models.yaml`, provider config, local media,
  or model cache changed.
- No Web UI behavior changed in this lane.
- No durable Memory runtime, database, RAG, Router runtime, or skill runtime
  added.

## Result

`AFS-RUN-PACKAGE-001` should remain open as a blocked runtime lane until local
inputs are supplied. `AFS-WEB-OPERATOR-002` may still proceed in parallel to
surface this blocker clearly in the operator path.
