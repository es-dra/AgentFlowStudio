# AFS-WEB-OPERATOR-002 - Local Alpha 0.4 Web Operator Path

## Task

Adapt the local Web workbench to guide the Local Alpha 0.4 product-loop
scenario.

## Goal

Let one local operator review the 0.4 scenario state, run or inspect the local
package evidence through the bridge, refresh review evidence, and capture
acceptance feedback without persistence or remote services.

## Non-goals

- Do not add SaaS, authentication, cloud sync, uploads, accounts, cookies, or
  browser persistence.
- Do not store provider keys, local secrets, signed URLs, or local media paths
  in browser persistence.
- Do not add automatic directory scanning.
- Do not add durable Memory runtime, RAG, database, Router runtime, or hosted
  backend.
- Do not call remote providers.

## Owner Role

Web UI Agent + QA Reviewer

## Branch / Worktree

```text
Branch: codex/afs-web-operator-loop
Worktree: C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-web-operator-loop
Base branch: master
```

## Write Scope

Files or directories this task may edit:

- `apps/web/`
- `apps/web_bridge/`
- `apps/cli/` only if the Web bridge entrypoint or workflow profile is broken
- `tests/test_web_static_artifact_viewer.py`
- `tests/test_web_production_mode_static.py`
- `tests/test_web_production_bridge.py`
- `apps/web/README.md`
- Web-related docs under `docs/`
- `docs/handoff/AFS-WEB-OPERATOR-002.md`
- `TASK_TRACKER.md`
- `DEVLOG.md`

## Do Not Touch

Files, directories, branches, artifacts, or local state this task must not
modify:

- `agentflow/memory/`
- `agentflow_production/posterflow/`
- provider configuration files
- `.env`, `.dev.vars`, or `configs/models.yaml`
- generated runtime artifacts under `data/processed/`
- local media under `data/raw/`
- private Company knowledge base

## Input Docs

- `AGENTS.md`
- `docs/company_operating_model.md`
- `TASK_TRACKER.md`
- `docs/agent_operating_roster.md`
- `docs/local_alpha_0_4_product_loop_goals.md`
- `docs/local_alpha_0_4_scenario_package.md`
- `apps/web/README.md`
- `docs/handoff/AFS-WEB-REVIEW-001.md`

## Acceptance Criteria

- [ ] The Web workbench names the Local Alpha 0.4 scenario path and next
      operator action.
- [ ] Production Mode can expose or run the selected local scenario workflow
      through the local bridge, or show an actionable local-input blocker.
- [ ] Review Mode remains explicit-file-only and local-only.
- [ ] Feedback capture can reference review/package evidence when available.
- [ ] Production Mode still connects only to the local bridge at `127.0.0.1`.
- [ ] Browser state remains non-persistent: no `localStorage`, IndexedDB,
      cookies, uploads, provider config, SaaS, or cloud backend.
- [ ] Desktop and narrow-viewport browser smokes pass with no unexpected
      console errors.

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

Open `http://127.0.0.1:8769/index.html`, walk the 0.4 scenario path, test
desktop and narrow viewport, and record the result in the handoff.

## Expected Artifacts

- Web diff and focused tests.
- Browser-smoke notes or screenshot path outside the repository.
- `docs/handoff/AFS-WEB-OPERATOR-002.md`.
- Tracker and DEVLOG updates.

## Remote Provider Policy

Mark every capability explicitly.

- [x] No remote provider needed.
- [ ] Remote LLM needed. Requires `AFS_ALLOW_REMOTE_LLM=true`.
- [ ] Remote ASR needed. Requires `AFS_ALLOW_REMOTE_ASR=true`.
- [ ] Remote image needed. Requires `AFS_ALLOW_REMOTE_IMAGE=true`.
- [ ] Remote video generation needed. Requires an explicit task-specific gate.
- [ ] External download needed. Requires explicit source and artifact policy.

Secrets, keys, signed URLs, cookies, and private credentials must stay local and
must not be committed.

## Evidence Path

Where the worker should write or reference evidence:

```text
docs/handoff/AFS-WEB-OPERATOR-002.md
```

## Return Format

1. Status: `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`.
2. Changed files.
3. Verification commands and results.
4. Evidence or artifact paths.
5. Risks and unfinished work.
6. Memory candidates for `Company/` or project docs.
7. Whether the subagent or worktree should be closed, preserved, or continued.
