# AFS-PRODUCTION-MEMORY-NEXT-OPERATOR-BRIEF-001

Status: verified locally on
`codex/afs-production-memory-next-operator-brief-001`.

## Scope

Make the next-operator start brief visible from a selected production-memory
operator-loop manifest without requiring Web to follow artifact refs.

This slice embeds a sanitized prompt excerpt and start requirements in the
manifest's `next_operator_start_packet` summary, then renders the same brief in
the read-only Web operator-loop canvas and operator readiness summary.

## Implementation Files

- `agentflow/memory/production_operator_start_packet_output.py`
- `apps/web/memory-workbench-production-next-operator-brief.js`
- `apps/web/memory-workbench-production-next-operator-start.js`
- `apps/web/memory-workbench-production-operator-loop.js`
- `apps/web/memory-workbench-production-operator-loop-utils.js`
- `apps/web/memory-workbench-demo-summary.js`
- `tests/test_production_memory_operator_loop.py`
- `tests/test_web_static_production_memory_operator_loop.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`

## Behavior

- Operator-loop manifest start-packet summaries now include:
  - `operator_prompt_excerpt`;
  - `start_requirements`.
- Web builds a `next_operator_brief` from either:
  - selected standalone `agentflow_production_memory_next_operator_start_packet`
    JSON; or
  - selected operator-loop manifest embedded start-packet summary.
- The operator readiness summary now shows:
  - recorded next operator action;
  - operator prompt excerpt;
  - start-requirements visibility.
- `memory-workbench-production-operator-loop.js` was split so pure rendering
  helpers live in `memory-workbench-production-operator-loop-utils.js`; the
  operator-loop view file is back under the 300-line project target.

## Boundaries

- Selected local JSON only.
- No Web ref following.
- No directory scan.
- No browser persistence.
- No provider call.
- No workflow execution from Web.
- No Company KB write.
- No durable memory write.
- No human acceptance claim.
- No business validation claim.
- No provider success claim.
- No memory promotion claim.

## Verification

Red tests:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_operator_loop.py::test_operator_loop_manifest_embeds_next_operator_start_brief_summary -q
```

Result before implementation: failed with missing `operator_prompt_excerpt`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_web_static_production_memory_operator_loop.py::test_web_static_operator_loop_renders_post_check_next_operator_start_packet -q
```

Result before implementation: failed with missing `next_operator_brief`.

Focused green tests:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_operator_loop.py::test_operator_loop_manifest_embeds_next_operator_start_brief_summary -q
```

Result: `1 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_web_static_production_memory_operator_loop.py::test_web_static_operator_loop_renders_post_check_next_operator_start_packet -q
```

Result: `1 passed`.

Related regression:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_operator_loop.py tests\test_production_memory_next_operator_start_packet.py -q
```

Result: `14 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_web_static_production_memory_operator_loop.py tests\test_web_static_production_memory_next_operator_start_packet.py tests\test_web_static_production_memory_operator_readiness_cockpit.py -q
```

Result: `7 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_operator_loop.py tests\test_web_static_production_memory_operator_loop.py -q
```

Result: `12 passed`.

JS syntax:

```powershell
node --check apps\web\memory-workbench-production-next-operator-brief.js
node --check apps\web\memory-workbench-production-next-operator-start.js
node --check apps\web\memory-workbench-production-operator-loop.js
node --check apps\web\memory-workbench-production-operator-loop-utils.js
node --check apps\web\memory-workbench-demo-summary.js
```

Result: passed.

Expanded Web/static memory suite:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests -k "web_static or web_memory" -q
```

Result: `83 passed, 800 deselected`.

Full suite:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest
```

Result: `883 passed` on Python 3.12.12.

CLI smoke:

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main production-memory-loop-run-operator-no-provider examples\agentflow\production_memory_loop.example.json --generated-at 2026-06-03T10:00:00+08:00 --source-kb-status restructuring_or_unknown --draft-next-pass-result --write-run-package --write-run-package-check --write-next-operator-start-packet --output data\processed\runs\production_memory_loop\next_operator_brief_smoke
```

Result: wrote ignored runtime artifacts and reported
`Next operator start packet: ready`. The generated operator-loop manifest
contains `operator_prompt_excerpt` and `start_requirements`.

Diff and boundary checks:

```powershell
git diff --check
```

Result: exit 0 with CRLF normalization warnings only.

Added-line sensitive scan, project-specific term scan, ignored-runtime check,
and touched-Web forbidden behavior scan were clean.

## Remaining Risks

- Browser-level smoke is not yet run in this slice.
- This brief is an operator-start projection from checked artifacts. It is not
  human acceptance, business validation, provider success, durable memory,
  Company KB promotion, or automatic memory promotion.
