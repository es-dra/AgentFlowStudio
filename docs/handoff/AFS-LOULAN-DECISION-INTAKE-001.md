# AFS-LOULAN-DECISION-INTAKE-001

Status: no-call Loulan decision intake report implemented and real blocked
probe run.

## Scope

New command:

```text
loulan-decision-intake
```

Input artifacts:

```text
agentflow_loulan_decision_worksheet
agentflow_loulan_promotion_decisions
```

Output artifacts:

```text
loulan_decision_intake_report.json
loulan_decision_intake_report.md
```

## Real Probe

Input worksheet remained the previous ignored Loulan decision worksheet output:

```text
data/processed/runs/loulan_decision_worksheet/real_probe_2026_06_01/
```

The unfilled decisions file was extracted from the worksheet's
`manual_transfer_template` into the ignored intake run directory:

```text
data/processed/runs/loulan_decision_intake/real_probe_2026_06_01/
```

Result:

| Check | Result |
|---|---|
| Intake status | blocked_pending_manual_decisions |
| Context bundle ready | false |
| Required decisions | 47 |
| Submitted decisions | 47 |
| Ready count | 0 |
| Pending count | 47 |
| Missing decisions | 0 |
| Invalid decisions | 0 |
| Unexpected decisions | 0 |
| Reusable count | 0 |
| Blocked count | 0 |
| Provider calls | not started |
| Human acceptance | not recorded |
| Durable Memory runtime | not implemented |

## Boundary Evidence

- The report validates a manually filled decisions file before context
  projection.
- It does not approve, reject, promote, merge, expire, repair, or infer any
  decision.
- It rejects worksheet JSON as a decisions input because the artifact type is
  not `agentflow_loulan_promotion_decisions`.
- It does not run `loulan-context-bundle`.
- It does not call image/video/LLM/ASR providers.
- It does not write Company memory or durable Memory runtime state.
- A ready intake report means only that the decisions file is structurally fit
  for context projection. It is not product acceptance or business validation.

## Verification Snapshot

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_decision_intake.py -q
# 7 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_decision_intake.py tests\test_loulan_decision_worksheet.py tests\test_loulan_decision_review_pack.py tests\test_loulan_decision_template.py tests\test_loulan_context_bundle.py tests\test_contract_examples.py tests\test_agentflow_contract_audit.py tests\test_cli_command_registry_boundaries.py -q
# 60 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain -q
# 730 passed

.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-decision-intake --help
# passed

.\.venv\Scripts\python.exe -B -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -B -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
# passed

git diff --check
# passed; CRLF normalization warnings only
```

## Next Work

- Render `agentflow_loulan_decision_intake_report` in the Web memory workbench
  if the operator needs the readiness gate visible beside worksheet and context
  bundle artifacts.
- After a human fills a decisions file and intake reports
  `ready_for_context_bundle`, run `loulan-context-bundle`.
- Keep live provider calls blocked until a separate task explicitly authorizes
  the relevant capability gate and local provider config.
