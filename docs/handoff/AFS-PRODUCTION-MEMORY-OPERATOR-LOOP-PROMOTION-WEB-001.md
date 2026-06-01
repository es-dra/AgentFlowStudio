# AFS-PRODUCTION-MEMORY-OPERATOR-LOOP-PROMOTION-WEB-001

Status: verified locally on
`codex/afs-production-memory-operator-loop-promotion-web-001`.

## Scope

Render embedded next-pass promotion decision/effect fields from a selected
`agentflow_production_memory_operator_loop_run` manifest in the existing
read-only generic Web memory workbench.

This complements the standalone next-pass promotion decision/overlay artifact
view. It lets an operator inspect the full loop manifest and still see the
explicit promotion decision and derived follow-up context effect without
opening referenced files.

## Implementation Files

- `apps/web/memory-workbench-production-operator-loop.js`
- `apps/web/memory-workbench-inspector.js`
- `tests/test_web_static_production_memory_operator_loop.py`

## Rendered Surfaces

When `next_pass_promotion` is present in the operator-loop manifest, the Web
view shows:

- a Next pass promotion workflow action;
- a Next pass promotion summary card;
- a Next pass promotion lane;
- next-pass promotion no-provider / write-disabled controls;
- `next_pass_promotion_decision` and `next_pass_promotion_effect` inspector
  facts;
- a next-pass action pointing operators to inspect the overlay before follow-up
  context use.

## Boundaries

- No provider call.
- No next-pass execution.
- No Company KB write.
- No durable memory write.
- No ref following.
- No directory scan.
- No browser persistence.
- No Loulan-specific behavior.
- No human acceptance claim.
- No business validation claim.

## Verification So Far

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_web_static_production_memory_operator_loop.py -q
```

Result: `3 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_web_static_production_memory_operator_loop.py tests/test_web_static_production_memory_next_pass_promotion.py tests/test_web_static_production_memory_next_pass_review.py tests/test_web_static_production_memory_next_task_packet.py tests/test_web_static_production_memory_next_context_handoff.py tests/test_web_static_company_kb_feedback_packet.py tests/test_web_static_production_memory_session_report.py tests/test_web_static_production_memory_loop.py tests/test_web_static_artifact_workspace.py tests/test_web_static_artifact_boundaries.py tests/test_web_memory_static_structure.py tests/test_web_memory_canvas_static.py -q
```

Result: `34 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest
```

Result: `748 passed` on Python 3.12.12.

## Remaining Verification

- `git diff --check`
- staged sensitive scan before commit

## Remaining Risks

- Browser-level smoke was not completed because `tool_search` did not expose
  Browser control tools in this turn.
- This slice does not execute the next pass, follow artifact refs, call
  providers, write durable memory, or write Company KB.
