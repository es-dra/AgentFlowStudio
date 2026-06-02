# AFS-PRODUCTION-MEMORY-NEXT-PASS-REVIEW-WEB-001

Status: verified locally on `codex/afs-production-memory-next-pass-review-web-001`.

## Scope

Render `agentflow_production_memory_next_pass_review` artifacts in the generic
read-only Web memory workbench when the operator explicitly selects a local
`next_pass_review.json` file.

Implementation files:

- `apps/web/artifact-contracts.js`
- `apps/web/artifact-workspace.js`
- `apps/web/memory-workbench-controller.js`
- `apps/web/memory-workbench-inspector.js`
- `apps/web/memory-workbench-production-next-pass-review.js`
- `tests/test_web_static_production_memory_next_pass_review.py`

## Boundaries

- No provider call.
- No next-pass execution.
- No ref following.
- No directory scan.
- No browser persistence.
- No Company KB write.
- No durable memory write.
- No Loulan-specific behavior.
- No human acceptance claim.
- No business validation claim.

## Verification

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_web_static_production_memory_next_pass_review.py -q
```

Result: `2 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_web_static_production_memory_next_pass_review.py tests/test_web_static_production_memory_next_task_packet.py tests/test_web_static_production_memory_next_context_handoff.py tests/test_web_static_production_memory_operator_loop.py tests/test_web_static_company_kb_feedback_packet.py tests/test_web_static_production_memory_session_report.py tests/test_web_static_production_memory_loop.py tests/test_web_static_artifact_workspace.py tests/test_web_static_artifact_boundaries.py tests/test_web_memory_static_structure.py tests/test_web_memory_canvas_static.py -q
```

Result: `31 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_next_pass_review.py tests/test_production_memory_next_task_packet.py tests/test_production_memory_next_context_handoff.py tests/test_production_memory_operator_loop.py tests/test_contract_examples.py tests/test_cli_command_registry_boundaries.py tests/test_web_static_production_memory_next_pass_review.py -q
```

Result: `42 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest
```

Result: `735 passed` on Python 3.12.12.

```powershell
git diff --check
```

Result: exit 0; CRLF normalization warnings only.

## Remaining Risks

- Browser-level smoke was not run for this slice; machine static tests covered
  the selected-file render path.
- The Web view is read-only and does not execute or validate provider output.
- Next-pass feedback candidates still require explicit promotion decisions
  before reuse.
