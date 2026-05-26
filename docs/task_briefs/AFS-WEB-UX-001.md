# AFS-WEB-UX-001 Task Brief

## Task

Productize the local Web workbench for repeated real use.

## Goal

Make Review Mode and Production Mode easier to use as the main Local Alpha 0.2
acceptance surface while preserving the local-only security boundary.

## Non-goals

- Do not add SaaS, authentication, cloud sync, uploads, or browser persistence.
- Do not store provider keys, local secrets, cookies, or signed URLs.
- Do not change workflow engine contracts unless a bug blocks the Web surface.
- Do not call remote providers.

## Owner Role

Web UI Agent + QA Reviewer.

## Branch / Worktree

```text
Branch: codex/afs-web-ux-pass
Worktree: C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-web-ux-pass
Base branch: master
```

## Write Scope

- `apps/web/`
- `apps/web_bridge/`
- `tests/test_web_static_artifact_viewer.py`
- `tests/test_web_production_mode_static.py`
- `tests/test_web_production_bridge.py`
- `apps/web/README.md`
- Web-related handoff docs if needed

## Do Not Touch

- `narratostudio/posterflow/` implementation.
- `agentflow/memory/` promotion logic.
- Provider configuration files.
- Generated runtime artifacts.
- Company knowledge base.

## Input Docs

- `AGENTS.md`
- `docs/company_operating_model.md`
- `TASK_TRACKER.md`
- `apps/web/README.md`
- `docs/handoff/AFS-WEB-REPLAY.md`

## Acceptance Criteria

- [ ] Production Mode has a clearer next-action path after health, plan, run,
      and review states.
- [ ] Review Mode remains explicit-file-only and local-only.
- [ ] Human-facing copy avoids mojibake and is usable in Chinese-first mode.
- [ ] Layout remains usable at desktop and narrow viewport sizes.
- [ ] Browser smoke evidence covers bridge health, demo workflow run, review
      refresh, and no unexpected console errors.
- [ ] No browser persistence or provider-secret surface is introduced.

## Verification Commands

```powershell
python -m pytest tests/test_web_static_artifact_viewer.py tests/test_web_production_mode_static.py tests/test_web_production_bridge.py
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
python -m compileall apps/web_bridge apps/cli tests
git diff --check
```

Browser smoke:

```powershell
python -m apps.cli.main web-bridge --host 127.0.0.1 --port 8787
python -m http.server 8769 -d apps/web --bind 127.0.0.1
```

Open `http://127.0.0.1:8769/index.html`, run `mock_text_to_slices`, refresh
review, and capture the result in the handoff.

## Expected Artifacts

- Web diff and tests.
- Browser smoke notes or screenshots.
- Updated `apps/web/README.md` if behavior changes.

## Remote Provider Policy

- [x] No remote provider needed.
- [ ] Remote LLM needed. Requires `NARRATOCUT_ALLOW_REMOTE_LLM=true`.
- [ ] Remote ASR needed. Requires `NARRATOCUT_ALLOW_REMOTE_ASR=true`.
- [ ] Remote image needed. Requires `NARRATOCUT_ALLOW_REMOTE_IMAGE=true`.
- [ ] Remote video generation needed. Requires an explicit task-specific gate.
- [ ] External download needed. Requires explicit source and artifact policy.

## Evidence Path

```text
docs/handoff/AFS-WEB-UX-001.md
```

## Return Format

1. Status: `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`.
2. Changed files.
3. Verification commands and results.
4. Evidence or artifact paths.
5. Risks and unfinished work.
6. Memory candidates for `Company/` or project docs.
7. Whether the subagent or worktree should be closed, preserved, or continued.
