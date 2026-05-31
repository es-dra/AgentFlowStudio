# AFS-LOULAN-API-INTAKE-GATE-001

Status: Loulan API workbench context intake gate validation implemented.

## Scope

`loulan-api-workbench-plan` now validates the `decision_intake_gate` embedded
in a supplied `agentflow_loulan_context_bundle_projection`.

Accepted gate states:

- omitted legacy gate
- `not_supplied`
- `ready_for_context_bundle` with `context_bundle_command_ready: true`

Rejected gate states:

- blocked supplied gates such as `blocked_pending_manual_decisions`
- any supplied ready status without `context_bundle_command_ready: true`

The no-call API plan now records `context_projection.decision_intake_gate` when
a projection is supplied, so request previews keep the pre-context gate visible.

## Boundary Evidence

- No provider call was added or run.
- No generated media, provider config, credentials, signed URLs, Company memory
  write, durable Memory runtime, or approval inference was added.
- `not_supplied` remains compatible evidence, not approval.

## Verification Snapshot

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_api_workbench.py -q
# 11 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_api_workbench.py tests\test_loulan_context_bundle.py tests\test_loulan_decision_intake.py tests\test_web_memory_loulan_decision_context_static.py tests\test_contract_examples.py tests\test_agentflow_contract_audit.py tests\test_cli_command_registry_boundaries.py -q
# 62 passed

.\.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
# pass

.\.venv\Scripts\python.exe -B -m pytest --assert=plain -q
# 736 passed
```

## Next Work

- Keep the real Loulan chain blocked until B01 human decisions are filled.
- After a ready intake report and context projection exist, rerun
  `loulan-api-workbench-plan --context-projection` and inspect the recorded
  gate before authorizing any live image capability.
