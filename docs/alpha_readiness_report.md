# AgentFlow Studio Alpha Readiness Report

Date: 2026-05-24

Replay update: 2026-05-26

## Scope

This report records the current Alpha demo readiness for three local-first
chains:

- PosterFlow visual memory demo
- AgentFlow Production production handoff chain
- AgentFlow Studio short-video finished package chain

It is an engineering readiness report. It does not certify creative quality,
durable Memory runtime, Web UI readiness, hosted service readiness, or provider
cost-quality optimization.

## Read-Only Status Entry

Use the Alpha smoke/status command when you need a quick local summary without
running remote providers or heavy media workflows:

```powershell
python -m apps.cli.main alpha-smoke
python -m apps.cli.main alpha-smoke --json
```

The command reads repository-local evidence and image-provider environment
presence only. It does not write run artifacts, does not call LLM/ASR/image/video
providers, and does not claim human acceptance or business validation.

## Repository And Branch State

- Original evidence branch: `codex/alpha-readiness-evidence`
- Original base evidence branch: `codex/posterflow-minimax-provider-tests`
- Clean replay branch: `codex/alpha-readiness-rebase`
- Current replay base: `eb98801` on `master`
- MiniMax provider replacement is already integrated on current `master` at
  `649d736`.
- The stale old provider branch was not merged; this report only replays the
  alpha evidence/documentation and demo-input fixes.

Implication: this report is no longer stacked on old provider code. It should
be treated as an evidence/documentation slice on top of the current
AgentFlow Studio mainline.

## PosterFlow Demo Live Smoke

Status: blocked.

Reason: the local shell did not have remote-image environment variables set.
The real MiniMax call was intentionally not run, and no API key from chat was
used.

Environment check:

```text
AFS_ALLOW_REMOTE_IMAGE=unset
AFS_IMAGE_PROVIDER=unset
AFS_IMAGE_BASE_URL=unset
AFS_IMAGE_API_KEY=unset
AFS_IMAGE_MODEL=unset
```

Safety gate command:

```powershell
.venv\Scripts\python.exe -m apps.cli.main run-workflow --workflow workflows/posterflow_memory_demo.yaml --input examples/posterflow/poster_brief.example.json --output data/processed/poster_runs/cyber_xianxia_001/blocked_env_check
```

Observed result:

- workflow status: failed
- run dir: `data/processed/poster_runs/cyber_xianxia_001/blocked_env_check`
- successful pre-provider artifacts:
  - `poster_brief.json`
  - `poster_plan.json`
  - `poster_prompt_pack.json`
- failed step: `generate_poster_candidates`
- failure message: `OpenAI-compatible image provider requires base_url`

To run the live MiniMax smoke later, set local environment variables only:

```powershell
$env:AFS_ALLOW_REMOTE_IMAGE="true"
$env:AFS_IMAGE_PROVIDER="minimax"
$env:AFS_IMAGE_API_KEY="<local-provider-key>"
$env:AFS_IMAGE_MODEL="image-01"
.venv\Scripts\python.exe -m apps.cli.main run-workflow --workflow workflows/posterflow_memory_demo.yaml --input examples/posterflow/poster_brief.example.json --output data/processed/poster_runs/cyber_xianxia_001/live_001
.venv\Scripts\python.exe -m apps.cli.main inspect-run --run-dir data/processed/poster_runs/cyber_xianxia_001/live_001
.venv\Scripts\python.exe -m apps.cli.main review-run --run-dir data/processed/poster_runs/cyber_xianxia_001/live_001
```

Expected live smoke artifacts:

- `image_candidates/candidate_001.png` through `candidate_003.png`
- `poster_candidates_manifest.json`
- `poster_model_invocations.json`
- `poster_feedback.jsonl`
- `poster_feedback_signal_log.json`
- `poster_memory_candidates.jsonl`
- `poster_memory_candidates.json`
- `poster_memory_review.jsonl`
- `poster_preference_profile.json`
- `context_bundle.json`
- `context_assembly_trace.json`
- `next_round_prompt.json`
- `round_2/poster_prompt_pack.json`
- `round_2/poster_candidates_manifest.json`
- `round_2/poster_model_invocations.json`
- `round_2/image_candidates/candidate_001.png` through
  `round_2/image_candidates/candidate_003.png`
- `poster_round_comparison.json`
- `poster_two_round_report.md`
- `poster_preview.html`

Boundary: PosterFlow memory artifacts are demo-only memory candidates and
profiles, not durable Memory runtime writes.

## AgentFlow Production Handoff Chain

Status: passed.

Commands:

```powershell
.venv\Scripts\python.exe -m apps.cli.main run-workflow --workflow workflows/agentflow_production_handoff.yaml --input examples/agentflow_production/creative_brief.example.json --output data/processed/runs/demo_agentflow_production_handoff_alpha
.venv\Scripts\python.exe -m apps.cli.main inspect-run --run-dir data/processed/runs/demo_agentflow_production_handoff_alpha
.venv\Scripts\python.exe -m apps.cli.main review-run --run-dir data/processed/runs/demo_agentflow_production_handoff_alpha
```

Observed result:

- workflow: success
- inspect: `65 passed / 0 failed / 0 warnings`
- review: `83 passed / 0 failed / 0 warnings`
- run dir: `data/processed/runs/demo_agentflow_production_handoff_alpha`

Key artifacts:

- `creative_brief.json`
- `story_bible.json`
- `episode_outline.json`
- `scene_plan.json`
- `shot_plan.json`
- `prompt_pack.json`
- `production_handoff.json`
- `production_report.md`
- `memory_candidates.json`
- `feedback_signal_log.json`
- `cost_quality_trace.json`
- `execution_trace.json`
- `quality_report.json`
- `review_report.json`

Readiness judgment: the production-side artifact handoff contract and review
gate are Alpha-ready as a deterministic local skeleton.

Boundary: this does not prove mature creative quality, real prompt/model
selection, provider cost optimization, I2V/T2V readiness, or durable reusable
asset promotion.

## AgentFlow Studio Package Chain

Status: passed after committed example input alignment.

Initial failure reproduced:

- The committed ASR demo inputs pointed to `data/raw/demo_bgm/bgm.mp3` and
  `data/raw/demo_bgm/bgm.metadata.json`.
- Current local acceptance media contains `data/raw/demo_bgm/bgm.wav`.
- `data/raw/demo_bgm/bgm.metadata.json` was missing.
- The full chain reached `mix_bgm` and failed with:
  `BGM metadata not found: data\raw\demo_bgm\bgm.metadata.json`.

Fix applied in this branch:

- ASR demo example inputs now reference `data/raw/demo_bgm/bgm.wav`.
- ASR demo example inputs now reference committed metadata template
  `examples/demo_bgm/bgm.metadata.example.json`.
- `examples/demo_bgm/final_video_with_bgm_input.example.json` now also
  references `data/raw/demo_bgm/bgm.wav`.
- A focused regression test covers these demo example references.

Commands after alignment:

```powershell
.venv\Scripts\python.exe -m apps.cli.main run-workflow --workflow workflows/video_to_finished_package_local_asr.yaml --input examples/demo_asr/video_to_finished_package_local_asr_input.example.json --output data/processed/runs/demo_agentflow_studio_package_alpha
.venv\Scripts\python.exe -m apps.cli.main inspect-run --run-dir data/processed/runs/demo_agentflow_studio_package_alpha
.venv\Scripts\python.exe -m apps.cli.main review-run --run-dir data/processed/runs/demo_agentflow_studio_package_alpha
.venv\Scripts\python.exe -m apps.cli.main package-report --run-dir data/processed/runs/demo_agentflow_studio_package_alpha
```

Observed result:

- workflow: success
- inspect: `8 passed / 0 failed / 0 warnings`
- review: `41 passed / 0 failed / 0 warnings`
- package report refreshed
- run dir: `data/processed/runs/demo_agentflow_studio_package_alpha`

Key artifacts:

- `audio_manifest.json`
- `boundary_signal_manifest.json`
- `transcript.json`
- `candidate_windows.json`
- `highlight_score_report.json`
- `selection_diagnostics.json`
- `highlight_plan.json`
- `clip_plan.json`
- `real_slice_manifest.json`
- `final_video_manifest.json`
- `subtitles.srt`
- `subtitle_manifest.json`
- `audio_mix_manifest.json`
- `final_video_with_bgm.mp4`
- `finished_package_manifest.json`
- `package_report.md`
- `quality_report.json`
- `review_report.json`

Package evidence:

- `finished_package_manifest.json` status: `succeeded`
- primary video: `final_video_with_bgm.mp4`
- final duration from report: `18.79s`
- `audio_mix_manifest.json` status: `succeeded`
- BGM path: `data/raw/demo_bgm/bgm.wav`
- BGM metadata source: committed example metadata

Readiness judgment: the distribution-side local product chain is Alpha-demo
ready on this machine when local ignored media and FFmpeg are available.

Boundary: current highlight selection remains deterministic and transcript
driven. This is not a claim of mature viral/editorial judgment.

## Current Demoable Capabilities

- AgentFlow Studio can show an artifact-first platform repository with three
  bounded modules: `agentflow/`, `agentflow_production/`, and `agentflow_studio/`.
- AgentFlow Production can generate a structured production handoff and report from a
  creative brief through local deterministic SOPs.
- AgentFlow Studio can run a local video-only short-video package chain through ASR,
  candidate scoring, slicing, assembly, subtitles, BGM mix, package manifest,
  inspect, review, and package report.
- PosterFlow can build pre-provider poster planning artifacts, Memory OS
  candidate/review artifacts, context bundle/trace artifacts, and a two-round
  comparison path. Live image generation still requires a local MiniMax or
  OpenAI-compatible key.

## Current Non-Claims

- No Web UI is ready for merge into mainline.
- No AgentFlow Router runtime, skill runtime, or Memory runtime exists.
- No database, vector store, hosted API, publishing integration, or durable
  memory store exists.
- No long-term memory write is performed by PosterFlow or AgentFlow Production.
- No real creative quality loop has been validated across multiple customer
  cases.
- No provider cost-quality optimization loop is implemented.
- No I2V/T2V execution path is ready.

## Submission Boundaries

- Do not commit `data/processed/...` run outputs.
- Do not commit `data/raw/...` media.
- Do not commit API keys, Token Plan keys, base URLs, signed image URLs,
  cookies, or provider response bodies that may contain private URLs.
- Keep provider secrets in local environment variables only.
- Treat generated images, videos, and run artifacts as local evidence, not
  formal deliverables.

## Next Required Work

1. Run the PosterFlow live MiniMax smoke with local environment variables set,
   then inspect `poster_model_invocations.json` for secret and URL hygiene.
2. Add a docs or CLI note explaining that `.venv\Scripts\python.exe -m
   apps.cli.main ...` is the preferred reliable Windows invocation when the
   console script wrapper is unavailable or silent.
3. Decide whether `examples/demo_bgm/bgm.metadata.example.json` should remain
   acceptable for local demo smoke, or whether a local ignored metadata file
   should be required for product acceptance.
4. After the three Alpha chains are live/green, move to an Alpha acceptance
   package that separates demo evidence from public deliverables.
