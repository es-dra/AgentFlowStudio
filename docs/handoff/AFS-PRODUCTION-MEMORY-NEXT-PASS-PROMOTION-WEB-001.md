# AFS-PRODUCTION-MEMORY-NEXT-PASS-PROMOTION-WEB-001

Status: verified locally on
`codex/afs-production-memory-next-pass-promotion-web-001`.

## Scope

Render next-pass promotion decision and overlay artifacts in the existing
read-only generic Web memory workbench.

Recognized selected-file artifact kinds:

- `agentflow_production_memory_next_pass_promotion_decision`
- `agentflow_production_memory_next_pass_promotion_overlay`

The Web view shows:

- explicit operator decision;
- candidate id;
- decision effect;
- follow-up context bundle id;
- no-provider controls;
- non-claim boundaries.

## Implementation Files

- `apps/web/artifact-contracts.js`
- `apps/web/artifact-workspace.js`
- `apps/web/memory-workbench-controller.js`
- `apps/web/memory-workbench-inspector.js`
- `apps/web/memory-workbench-production-next-pass-promotion.js`
- `tests/test_web_static_production_memory_next_pass_promotion.py`

## Boundaries

- No provider call.
- No next-pass execution.
- No Company KB write.
- No durable memory write.
- No ref following.
- No Web scan or persistence.
- No Loulan-specific behavior.
- No human acceptance claim.
- No business validation claim.

## Verification

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_web_static_production_memory_next_pass_promotion.py -q
```

Result: `2 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_web_static_production_memory_next_pass_promotion.py tests/test_web_static_production_memory_next_pass_review.py tests/test_web_static_production_memory_next_task_packet.py tests/test_web_static_production_memory_next_context_handoff.py tests/test_web_static_production_memory_operator_loop.py tests/test_web_static_company_kb_feedback_packet.py tests/test_web_static_production_memory_session_report.py tests/test_web_static_production_memory_loop.py tests/test_web_static_artifact_workspace.py tests/test_web_static_artifact_boundaries.py tests/test_web_memory_static_structure.py tests/test_web_memory_canvas_static.py -q
```

Result: `33 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest
```

Result: `744 passed` on Python 3.12.12.

```powershell
git diff --check
```

Result: exit 0; CRLF normalization warnings only.

## Remaining Risks

- This is a static selected-file render path. It does not follow artifact refs
  or inspect generated output folders.
- It does not add provider validation.
- Browser-level smoke was not completed because no Browser tool was exposed by
  `tool_search`, and common Edge/Chrome executable paths were not found.
