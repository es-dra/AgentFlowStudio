# AFS Web RC Draft PR Handoff 001

Status: draft PR ready, GitHub creation pending.

Branch:

```text
codex/afs-landing-prep-web-plan-001
```

Remote branch:

```text
origin/codex/afs-landing-prep-web-plan-001
```

Base branch:

```text
master
```

Current branch head:

```text
Run `git log -1 --oneline` before creating the PR.
```

## Draft PR Title

```text
feat(workbench): add Chinese release candidate workspace
```

## Draft PR Body

```markdown
## Summary

- Adds a Runtime Service-backed Chinese Web Workbench release candidate for the content production / project memory path.
- Splits the frontend into product workspaces: Projects, Create, Assets, Storyboard, Review, Style Memory, Jobs, and Settings/Diagnostics.
- Adds user-facing Chinese display mappings, safe Runtime error messages, no-store Workbench static serving, Stage 7 browser QA ledger, acceptance packet, and visual demo index.
- Localizes the acceptance first screen so the project list no longer exposes raw project ids, mojibake titles, old English demo text, or internal Stage 7 project names as primary user-facing labels.
- Keeps provider execution gated; this PR does not start provider calls and does not claim human acceptance, business validation, or durable memory promotion.

## Evidence

- Browser QA project: `proj_stage7_rc_1781016167554`
- Demo index: `docs/frontend_integration/AFS_WEB_RC_DEMO_INDEX.zh-CN.html`
- Acceptance packet: `docs/frontend_integration/AFS_WEB_RELEASE_CANDIDATE_ACCEPTANCE_PACKET.zh-CN.md`
- QA ledger: `docs/frontend_integration/AFS_WEB_UX_QA_LEDGER.zh-CN.md`
- Latest browser vertical smoke project: `proj_browser_vertical_1781026731`

## Verification

- `.\.venv\Scripts\python.exe -m apps.cli.main version`
- `.\.venv\Scripts\python.exe -m pytest`
- `.\.venv\Scripts\python.exe tools\maintenance_audit.py`
- `git diff --check`

Latest local results:

- full pytest: `844 passed, 1 warning`
- maintenance audit: `failed=0, passed=6, warning=0`
- browser vertical flow smoke: `ready_for_next_round`, `provider_calls_started=false`
- acceptance first-screen smoke assertions: no raw project ids, mojibake title runs, internal Stage 7 labels, legacy English projection copy, or error toasts
- Runtime HTTP smoke: `/workbench/`, `app.js`, and `render.js` return `Cache-Control: no-store`

## Human Acceptance Gate

This PR should remain draft until the user has manually accepted the Workbench experience using:

- `docs/frontend_integration/AFS_WEB_RELEASE_CANDIDATE_ACCEPTANCE_PACKET.zh-CN.md`
- `docs/frontend_integration/AFS_WEB_RC_DEMO_INDEX.zh-CN.html`

Do not treat browser QA as human acceptance.

## Provider Gate

Do not run real provider smoke from this PR unless the user explicitly authorizes the relevant capability gate.

Provider smoke, if later authorized, must be recorded separately and must not be presented as business validation.
```

## Current PR Creation State

- Branch has been pushed.
- `gh` CLI is not available in this local shell.
- GitHub connector PR lookup failed with expired authentication token in this session.
- Manual PR URL:

```text
https://github.com/es-dra/AgentFlowStudio/pull/new/codex/afs-landing-prep-web-plan-001
```

## Boundaries

- No live provider call.
- No secret, signed URL, private media byte, provider raw response, or COS active rule written.
- Runtime verification is not human acceptance.
- Provider smoke is not business validation.
- Feedback and candidate memory are not durable memory promotion.
