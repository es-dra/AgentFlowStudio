# AFS-WEB-REVIEW-001 - Operator Web Review Loop

## Task

Make the local Web workbench support a repeatable Local Alpha 0.3 operator
loop.

## Goal

Let one local operator move through workflow selection, plan generation,
supervised run, artifact inspection, review refresh, and feedback capture with
clear state and no browser persistence.

## Non-goals

- Do not add SaaS, authentication, cloud sync, uploads, or account state.
- Do not store provider keys, local secrets, cookies, signed URLs, or browser
  persistence.
- Do not add automatic directory scanning.
- Do not add durable Memory runtime, RAG, database, or cloud backend.
- Do not call remote providers.

## Owner Role

Web UI Agent + QA Reviewer

## Branch / Worktree

```text
Branch: codex/afs-web-review-loop
Worktree: C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-web-review-loop
Base branch: master
```

## Write Scope

Files or directories this task may edit:

- `apps/web/`
- `apps/web_bridge/`
- `apps/cli/` only if the Web bridge entrypoint is broken
- `tests/test_web_static_artifact_viewer.py`
- `tests/test_web_production_mode_static.py`
- `tests/test_web_production_bridge.py`
- Web-related docs under `docs/`
- `apps/web/README.md`
- `TASK_TRACKER.md`
- `DEVLOG.md`
- `docs/handoff/AFS-WEB-REVIEW-001.md`

## Do Not Touch

Files, directories, branches, artifacts, or local state this task must not
modify:

- `narratostudio/posterflow/` implementation
- `agentflow/memory/` promotion logic
- provider configuration files
- `.env`, `.dev.vars`, or `configs/models.yaml`
- generated runtime artifacts under `data/processed/`
- private Company knowledge base

## Input Docs

- `AGENTS.md`
- `docs/company_operating_model.md`
- `TASK_TRACKER.md`
- `docs/agent_operating_roster.md`
- `docs/local_alpha_0_3_validation_goals.md`
- `apps/web/README.md`
- `docs/handoff/AFS-WEB-UX-001.md`

## Acceptance Criteria

- [ ] The Web workbench exposes a clear Local Alpha 0.3 operator path from
      workflow selection through review refresh and feedback capture.
- [ ] The selected mock or local workflow can generate a plan, run to terminal
      status, list artifacts, and refresh review.
- [ ] Review Mode remains explicit-file-only and local-only.
- [ ] Production Mode still connects only to the local bridge at `127.0.0.1`.
- [ ] Browser state remains non-persistent: no `localStorage`, IndexedDB,
      cookies, uploads, provider config, SaaS, or cloud backend.
- [ ] Desktop and narrow-viewport browser smokes pass with no unexpected
      console errors.
- [ ] A handoff records what is verified by tests, what is verified by browser
      smoke, and what still requires human/product validation.

## Verification Commands

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests/test_web_static_artifact_viewer.py tests/test_web_production_mode_static.py tests/test_web_production_bridge.py
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
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m compileall apps\web_bridge apps\cli tests
git diff --check
```

Browser smoke:

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main web-bridge --host 127.0.0.1 --port 8787
python -m http.server 8769 -d apps/web --bind 127.0.0.1
```

Open `http://127.0.0.1:8769/index.html`, run a mock/local workflow, refresh
review, test desktop and narrow viewport, and record the result in the handoff.

## Expected Artifacts

- Web diff and focused tests.
- Browser-smoke notes or screenshot path outside the repository.
- `docs/handoff/AFS-WEB-REVIEW-001.md`.
- Tracker and DEVLOG updates.

## Remote Provider Policy

Mark every capability explicitly.

- [x] No remote provider needed.
- [ ] Remote LLM needed. Requires `NARRATOCUT_ALLOW_REMOTE_LLM=true`.
- [ ] Remote ASR needed. Requires `NARRATOCUT_ALLOW_REMOTE_ASR=true`.
- [ ] Remote image needed. Requires `NARRATOCUT_ALLOW_REMOTE_IMAGE=true`.
- [ ] Remote video generation needed. Requires an explicit task-specific gate.
- [ ] External download needed. Requires explicit source and artifact policy.

Secrets, keys, signed URLs, cookies, and private credentials must stay local and
must not be committed.

## Evidence Path

Where the worker should write or reference evidence:

```text
docs/handoff/AFS-WEB-REVIEW-001.md
```

## Return Format

1. Status: `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`.
2. Changed files.
3. Verification commands and results.
4. Evidence or artifact paths.
5. Risks and unfinished work.
6. Memory candidates for `Company/` or project docs.
7. Whether the subagent or worktree should be closed, preserved, or continued.
