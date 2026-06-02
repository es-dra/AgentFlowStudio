# AFS-WEB-REPLAY Handoff

## Status

In progress on `codex/afs-web-ui-replay`.

## Scope

This branch replays only the Web UI workbench surface from
`codex/agentflow_studio-web-ui` onto the current AgentFlow Studio mainline.

Included:

- `apps/web/`
- `apps/web_bridge/`
- Web UI tests and static artifact fixtures

Excluded:

- stale backend/module deletes from the old Web UI branch
- provider behavior
- AgentFlow runtime, memory, or harness changes
- Company knowledge base changes

## Replay Notes

The old Web UI branch expected a `web-bridge` CLI command and a
`WorkflowRunner(progress_callback=...)` constructor. Current mainline has
neither. This replay keeps the bridge as a standalone local server entrypoint
and adapts progress/status writing inside `apps/web_bridge` without changing the
shared workflow runner.

## Verification

Run before integration:

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
python -m compileall apps/web_bridge apps/cli tests
git diff --check
```
