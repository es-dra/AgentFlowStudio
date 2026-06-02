# AFS-MEMORY-ADVANTAGE-RECORDING-016

Status: prerecording runbook for the repeated-generation I2V demo.

## Purpose

This runbook is for recording a short operator demo where one command prepares
the protocol, calls Kling I2V for the baseline and memory-backed lanes, and
writes a side-by-side comparison video.

The experiment question is narrow:

> Under the same source keyframe, task, model, duration, and storyboard, does
> projected memory context reduce repeated-generation divergence?

## Recording Command

From `D:\Projects\AgentFlowStudio`:

```powershell
.\tools\run_memory_advantage_recording_016.ps1 -DryRun -NoOpen
```

Use this first while recording setup. It writes prompt/protocol notes under
ignored `data/processed/` and does not call a provider.

For the live recording pass, after confirming the local provider config is
present and the Kling quota can be used:

```powershell
.\tools\run_memory_advantage_recording_016.ps1 -ProviderConfig <local_ignored_provider_config.json> -AllowRemoteVideo
```

The `-AllowRemoteVideo` switch is intentional. Without it, the script stops
before provider calls. The same result can also be achieved by setting
`AFS_ALLOW_REMOTE_VIDEO=true` in the current shell. Provider config is
also explicit: pass `-ProviderConfig` or set `AFS_PROVIDER_CONFIG` to a
local ignored provider config file.

## What The Script Does

1. Uses the DEMO-012 memory-assisted neon-rain source keyframe.
2. Writes the shared user task and both prompts into the run's `protocol/`
   folder.
3. Runs Kling I2V once for the baseline lane.
4. Runs Kling I2V once for the memory-backed lane.
5. Uses `ffmpeg` to build
   `comparison_videos/neon_rain_baseline_vs_memory_15s.mp4`.

Default output root:

```text
data/processed/runs/memory_advantage_recording_016/neon_rain_turnback_i2v_<timestamp>/
```

`data/processed/` is ignored by Git.

## Prompt Difference

Baseline receives:

- current task;
- source keyframe;
- five shot checkpoints;
- general camera/rain/reflection/motion instructions.

Memory-backed receives the same items plus:

- character memory card: face family, high ponytail, white top, blue jeans,
  white sneakers;
- scene memory card: neon rain street, wet asphalt reflections, blue-magenta
  signage glow;
- feedback patch: recover the same face and outfit after rain or light
  occlusion, avoid outfit/hair drift, keep foot contact plausible.

## Suggested Recording Flow

1. Start the screen recording with a clean terminal.
2. Run the dry-run command and briefly show the generated protocol folder path.
3. Run the live command with `-AllowRemoteVideo`.
4. Let the terminal show the baseline task, memory-backed task, and final output
   paths.
5. Open the comparison video only after both lanes have completed.
6. In narration, keep the claim precise: this is bounded demo evidence that the
   memory-backed lane is more stable in this repeated-generation setting.

## Boundaries

- This is provider/runtime evidence and operator visual evidence.
- It is not final human acceptance.
- It is not business validation.
- It is not durable Memory runtime, DB, vector store, or RAG behavior.
- It does not write provider secrets or generated media into Git.

## Known Follow-Up

The competition Slidev deck currently presents this evidence as:

- baseline repeat instability;
- memory-backed repeat stability;
- bounded observation result.

Speaker notes for the same material are in
`docs/handoff/AFS-COMPETITION-DEMO-TALK-TRACK.md`.

The competition-day execution sheet is
`docs/handoff/AFS-COMPETITION-DEMO-RUN-SHEET.md`.

The later product direction is to replace this prerecording script with a
protocol-driven workbench action that runs the same lane contract, captures
review evidence, and keeps provider execution behind explicit capability gates.
