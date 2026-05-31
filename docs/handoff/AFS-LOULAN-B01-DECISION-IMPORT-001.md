# AFS-LOULAN-B01-DECISION-IMPORT-001

Status: no-call Loulan B01 decision import bridge implemented.

## Scope

New command:

```text
loulan-b01-decision-import
```

Input artifacts:

```text
agentflow_loulan_human_review_pack
loulan_b01_human_review_decision_template
```

Output artifacts:

```text
loulan_b01_decisions.imported.json
loulan_b01_decisions.imported.md
```

## Real Probe

Inputs:

```text
data/processed/runs/loulan_human_review_pack/local_probe/loulan_human_review_pack.json
D:\Projects\LoulanSceneAssets\manifests\b01_human_review_decision_template.json
```

Output was written under ignored local run artifacts:

```text
data/processed/runs/loulan_b01_decision_import/real_probe_2026_06_01/
```

Result:

| Check | Result |
|---|---|
| Imported ready decisions | 0 |
| Pending decisions | 7 |
| Skipped local items | 0 |
| Loulan local B01 validator | blocked_pending_human_review |
| Loulan local pending shot decisions | 5 |
| Human acceptance | not recorded |
| Provider calls | not started |
| Durable Memory runtime | not implemented |

The real Loulan B01 file is still all pending, so this bridge correctly does
not unlock context projection.

## Boundary Evidence

- The command imports only explicit `approve_anchor`, `request_repair`, or
  `reject` decisions from the local B01 file.
- Empty or `pending_human_review` decisions stay pending.
- It does not approve shots, promote assets, infer acceptance, run context
  projection, call providers, copy media, or write Company memory.
- Partial imports remain blocked by the existing decision-intake gate until all
  required AFS decision slots are complete.

## Verification Snapshot

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_b01_decision_import.py -q
# 5 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_b01_decision_import.py tests\test_loulan_decision_intake.py tests\test_loulan_decision_review_pack.py tests\test_loulan_decision_worksheet.py tests\test_loulan_decision_template.py tests\test_loulan_context_bundle.py tests\test_cli_command_registry_boundaries.py tests\test_contract_examples.py tests\test_agentflow_contract_audit.py -q
# 69 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain -q
# 741 passed

.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-b01-decision-import --help
# passed

.\.venv\Scripts\python.exe -B -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -B -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
# passed

git diff --check
# passed; CRLF normalization warnings only

python tools\validate_b01_decisions.py --project-root . --decisions manifests\b01_human_review_decision_template.json
# status: blocked_pending_human_review; pending: 5
```

## Next Work

- After the operator fills B01 decisions in Loulan, rerun
  `loulan-b01-decision-import`, then run decision review, worksheet/intake, and
  context bundle projection.
- Keep B02 generation and provider calls blocked until the validated decision
  chain reports ready refs.
