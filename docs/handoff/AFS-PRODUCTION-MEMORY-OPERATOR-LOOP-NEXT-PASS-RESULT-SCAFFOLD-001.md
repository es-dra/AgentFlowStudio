# AFS-PRODUCTION-MEMORY-OPERATOR-LOOP-NEXT-PASS-RESULT-SCAFFOLD-001

Status: verified locally on
`codex/afs-production-memory-operator-loop-next-pass-result-scaffold-001`.

## Scope

Let the generic no-provider operator-loop command optionally draft a local
`agentflow_production_memory_next_pass_result` scaffold from the generated
next-task packet and render that scaffold in the read-only generic Web
operator-loop canvas.

This connects the operator-loop manifest to the existing standalone
`production-memory-loop-draft-next-pass-result-no-provider` behavior without
executing providers or creating feedback.

## Implementation Files

- `agentflow/memory/production_operator_loop.py`
- `agentflow/memory/production_operator_manifest.py`
- `agentflow/memory/production_operator_outputs.py`
- `apps/cli/production_memory_operator_command.py`
- `apps/web/memory-workbench-production-operator-loop.js`
- `apps/web/memory-workbench-production-inspector-facts.js`
- `tests/test_production_memory_operator_loop.py`
- `tests/test_web_static_production_memory_operator_loop_result_scaffold.py`

## CLI Behavior

```powershell
python -m apps.cli.main production-memory-loop-run-operator-no-provider examples/agentflow/production_memory_loop.example.json --generated-at 2026-06-02T12:00:00+08:00 --source-kb-status restructuring_or_unknown --draft-next-pass-result --output data/processed/runs/production_memory_loop/operator_loop_next_pass_result_scaffold_smoke
```

When `--draft-next-pass-result` is supplied, the operator-loop output includes:

- `next_pass_result/next_pass_result.json`
- `next_pass_result/next_pass_result.md`
- `production_memory_operator_loop_run.json` with a `next_pass_result` summary
  and output artifact refs.

The flag cannot be combined with `--next-pass-result`. The first option drafts
an operator-completion scaffold; the second consumes an explicit result for
review.

## Web Behavior

The read-only generic Web operator-loop canvas now surfaces embedded
`next_pass_result` summaries as:

- a Next pass result workflow action;
- a Next pass result summary card;
- a Next pass result lane;
- output artifact refs for the JSON and Markdown scaffold;
- a next-pass action:
  `inspect_next_pass_result_scaffold_before_review`;
- inspector facts for scaffold status and output artifact count.

## Contract Boundaries

- no provider call
- no generated-content claim
- no next-pass execution
- no next-pass review unless an explicit result is supplied
- no feedback auto-capture
- no Company KB write
- no durable memory write
- no Web scan or browser persistence
- no Loulan-specific behavior
- no human acceptance or business validation claim

## Verification

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_operator_loop.py -q
```

Initial red result: `draft_next_pass_result` and `--draft-next-pass-result` did
not exist.

Green result: `7 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_web_static_production_memory_operator_loop_result_scaffold.py -q
```

Initial red result: the operator-loop Web canvas did not include a Next pass
result lane.

Green result: `2 passed`.

```powershell
node --check apps\web\memory-workbench-production-operator-loop.js
node --check apps\web\memory-workbench-production-inspector-facts.js
```

Result: passed.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_operator_loop.py tests/test_production_memory_operator_loop_promotion.py tests/test_production_memory_next_pass_result.py tests/test_production_memory_next_pass_review.py tests/test_production_memory_next_pass_promotion.py tests/test_contract_examples.py tests/test_cli_command_registry_boundaries.py tests/test_web_static_production_memory_operator_loop.py tests/test_web_static_production_memory_operator_loop_result_scaffold.py tests/test_web_static_production_memory_next_pass_result.py tests/test_web_static_production_memory_next_pass_review.py tests/test_web_static_production_memory_next_pass_promotion.py -q
```

Result: `61 passed`.

CLI smoke result: wrote ignored runtime artifacts under
`data/processed/runs/production_memory_loop/operator_loop_next_pass_result_scaffold_smoke/`
and reported `Next pass result scaffold:
scaffolded_for_operator_completion`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest
```

Result: `790 passed` on Python 3.12.12.

## Remaining Risks

- Browser-level verification has not been run for this slice.
- The scaffold is still an empty operator-completion envelope. It does not
  create or validate generated content.
- `agentflow/memory/production_operator_manifest.py` is exactly 300 lines after
  this slice. Split helper logic before adding more manifest behavior.
- Machine verification is not human acceptance or business validation.
