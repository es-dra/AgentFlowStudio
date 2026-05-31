# AFS-WEB-OPERATOR-002 - Local Alpha 0.4 Web Operator Path

Status: INTEGRATED_WITH_FOLLOWUP_FIX
Date: 2026-05-27
Branch: `codex/afs-web-operator-loop`
Worktree: `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-web-operator-loop`

## Summary

The Web operator path now defaults to the Local Alpha 0.4 scenario:

```text
workflows/video_script_to_finished_package_local_asr.yaml
```

The static UI and bridge profile point to the ignored local input bundle and
expected run directory:

```text
data/processed/local_alpha_0_4/video_script_local_asr_input.json
data/processed/runs/local_alpha_0_4_product_loop
```

The operator UI also surfaces the scenario runbook and local setup blockers
instead of silently falling back to the older example input.

2026-05-27 controller follow-up: after the real runtime package succeeded and
the Web bridge input check passed, a stale-readiness bug was found and fixed in
the main checkout. Production Mode now prefers the bridge `input_check`
summary/next action over static `local_setup_blockers` once plan evidence
exists.

## Local Setup Blockers Surfaced

The Web profile exposes these required local inputs:

```text
data/raw/demo_real_video/input.mp4
data/raw/demo_bgm/bgm.wav
data/models/faster-whisper/
data/processed/local_alpha_0_4/video_script_local_asr_input.json
```

These are setup reminders and bridge preflight signals, not browser-side file
scans. The bridge still performs the actual input check when a plan or run is
created.

## Files Changed

- `apps/web_bridge/workflow_profiles.py`
- `apps/web/production-workflows.js`
- `apps/web/production-mode.js`
- `apps/web/production-render.js`
- `apps/web/index.html`
- `tests/test_web_production_bridge.py`
- `tests/test_web_production_mode_static.py`

## Verification

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests/test_web_static_artifact_viewer.py tests/test_web_production_mode_static.py tests/test_web_production_bridge.py
```

Result: `45 passed`.

```powershell
node --check apps/web/app.js
node --check apps/web/app-elements.js
node --check apps/web/feedback-wiring.js
node --check apps/web/feedback-event.js
node --check apps/web/production-mode.js
node --check apps/web/production-render.js
node --check apps/web/production-workflows.js
node --check apps/web/artifact-values.js
node --check apps/web/video-preview.js
node --check apps/web/artifact-contracts.js
node --check apps/web/artifact-ledgers.js
node --check apps/web/artifact-workspace.js
node --check apps/web/render-helpers.js
node --check apps/web/ui-copy.js
```

Result: passed.

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m compileall apps\web_bridge apps\cli tests
git diff --check
```

Results:

- `compileall`: passed.
- `git diff --check`: passed with Windows LF/CRLF warnings only.

Controller follow-up verification after the stale-readiness fix:

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests/test_web_production_mode_static.py::test_web_readiness_uses_input_check_after_plan_passes tests/test_web_production_mode_static.py::test_web_production_mode_defaults_match_preferred_workflow
```

Result: `2 passed`.

## Browser Smoke

Ran against the branch worktree with the static page on `127.0.0.1:8768` and
the Web bridge on `127.0.0.1:8787`:

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main web-bridge --host 127.0.0.1 --port 8787
python -m http.server 8768 -d apps/web --bind 127.0.0.1
```

Opened:

```text
http://127.0.0.1:8768/index.html
```

Observed checks:

- Production Mode title says `Local Alpha 0.4 operator loop`.
- Product workflow button selects `video_script_to_finished_package_local_asr`.
- Input file defaults to `data/processed/local_alpha_0_4/video_script_local_asr_input.json`.
- Output directory defaults to `data/processed/runs/local_alpha_0_4_product_loop`.
- Workflow profile shows `docs/local_alpha_0_4_scenario_package.md` and the four local setup blockers.
- Bridge status shows `bridge ready`.
- Page console errors from the local app: none. The browser automation runtime
  emitted an unrelated external telemetry timeout while trying to contact
  `ab.chatgpt.com`; this was not from the local page.

Controller follow-up smoke after the stale-readiness fix:

- A fresh tab at `http://127.0.0.1:8768/index.html?fresh=041` showed the
  passed input check and next action instead of stale setup blockers.
- Observed overview: `阻塞项暂无阻塞6 个输入引用可用`.
- Observed readiness: `输入诊断输入引用可用可生成计划并运行。下一步动作运行 workflow可生成计划并运行。`
- Local page console errors: none.
- The already-open tab kept an older ESM module until a fresh URL/server
  response was used. Future Web smokes after JS edits should use a fresh tab or
  cache-busting URL.

## Boundaries Kept

- No remote LLM, ASR, image, or video provider call.
- No generated media or runtime package artifacts committed.
- No browser persistence, upload, SaaS/cloud backend, or automatic directory scan added.
- No `.env`, `.dev.vars`, provider config, local media, model cache, or secrets changed.
