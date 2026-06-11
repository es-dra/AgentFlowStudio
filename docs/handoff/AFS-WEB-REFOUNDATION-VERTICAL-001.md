# AFS-WEB-REFOUNDATION-VERTICAL-001

Status: first script-to-storyboard Web vertical landed in isolated worktree.

Worktree:

```text
C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-web-refoundation-vertical-001
```

Branch:

```text
codex/afs-web-refoundation-vertical-001
```

## Goal

Stop expanding horizontal LibTV-style placeholder surfaces and land the first
usable production flow for the Web Workbench:

```text
script / creative goal
-> Runtime Service /provider/script-draft-plan
-> script_storyboard_safe_artifact
-> feedback and previous artifact reuse
-> browser-visible safe result
```

## Product Surface

The Create starter area now exposes a concrete script production flow:

- script / creative goal textarea;
- target duration input;
- tone selector;
- visible LLM gate boundary;
- generate storyboard plan action;
- storyboard result node with `script_storyboard_safe_artifact`;
- feedback note textarea;
- previous script artifact id input;
- review feedback artifact id input.

Image, character turnaround, keyframe, I2V, and video generation remain future
provider-gated flows. This slice intentionally starts with LLM/script because it
is the lowest-risk provider vertical.

## Changed Code

- `apps/workbench/src/runtime-client.js`: added same-origin Runtime Service base
  URL behavior and `providerScriptDraftPlan()`.
- `apps/workbench/src/state.js`: added script draft form and feedback state.
- `apps/workbench/src/input-sync.js`: wired script draft inputs.
- `apps/workbench/src/app-actions.js`: added `runScriptDraftPlan()` and action
  registration.
- `apps/workbench/src/render-studio-workspace.js`: passes state into starter
  flow rendering.
- `apps/workbench/src/render-studio-starter-flows.js`: replaces static script
  demo with executable script-to-storyboard controls.
- `apps/workbench/src/render-artifact.js`: adds
  `agentflow_script_storyboard_safe_artifact` view.
- `apps/workbench/index.html`: loads the script vertical stylesheet.
- `apps/workbench/styles-studio-script-vertical.css`: script vertical-specific
  layout.
- `apps/workbench/styles-studio-starters.css` and
  `apps/workbench/styles-studio-canvas-v2.css`: line-count and responsive
  refinements.
- `tests/test_web_workbench_foundation.py` and
  `tests/test_web_workbench_studio.py`: contract and UI coverage for the new
  vertical.

## Documentation Added

- `docs/maintenance/AFS-WEB-REFOUNDATION-CLEANUP-001.zh-CN.md`
- `docs/superpowers/specs/2026-06-11-afs-web-refoundation-design.md`
- `docs/superpowers/plans/2026-06-11-afs-web-refoundation-vertical.md`

## Verification Evidence

TDD red was confirmed before implementation for:

- missing `/provider/script-draft-plan` frontend call;
- missing `providerScriptDraftPlan()`;
- missing script storyboard artifact view.

Focused tests after implementation:

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_workbench_state.py tests\test_api_runtime_workbench_actions.py tests\test_api_runtime_llm_script_vertical.py tests\test_web_workbench_foundation.py tests\test_web_workbench_studio.py tests\test_web_workbench_libtv_add_node_flows.py -q
```

Result:

```text
26 passed, 1 warning
```

Focused Web foundation/studio rerun after CSS split and same-origin Runtime
client fix:

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_web_workbench_foundation.py tests\test_web_workbench_studio.py -q
```

Result:

```text
10 passed
```

Full regression:

```text
871 passed, 1 warning
```

Browser QA:

```text
data/processed/runs/workbench_script_vertical_browser_qa/workbench_script_vertical_browser_qa.json
```

Result summary:

```json
{"qa_status":"passed","cases":2,"runtime_provider_requests":2,"external_provider_requests":0}
```

Maintenance and diff checks:

```text
maintenance_audit: failed=0, passed=6, warning=0
git diff --check: passed with Windows line-ending warnings only
```

Screenshots:

```text
data/processed/runs/workbench_script_vertical_browser_qa/screenshots/desktop-script-vertical.png
data/processed/runs/workbench_script_vertical_browser_qa/screenshots/mobile-script-vertical.png
```

## Boundaries

- No live LLM, image, video, ASR, or I2V provider was started.
- Provider calls in browser QA hit only the local Runtime Service.
- No secret, provider key, signed URL, cookie, private local media byte,
  provider raw response, or generated media byte was written.
- Browser QA / pytest / maintenance audit are runtime verification only. They
  are not human acceptance or business validation.
- This does not promote any COS / `10-Startup` active rule.

## Next Recommended Slice

1. Human-test this script-to-storyboard flow in the browser and judge whether the
   first screen feels like a real creative tool.
2. After explicit LLM gate authorization, run a real provider smoke only for
   `/provider/script-draft-plan`.
3. Add the next vertical as a separate gate: character turnaround or keyframe,
   but do not mix image/video provider work into this script slice.
