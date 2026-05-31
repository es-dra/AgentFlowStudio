# AFS-LOULAN-CONTEXT-BUNDLE-INTAKE-GATE-001

Status: Loulan context bundle decision-intake gate implemented.

## Scope

`loulan-context-bundle` now accepts:

```text
--decision-intake-report <agentflow_loulan_decision_intake_report.json>
```

When supplied, the intake report is a hard pre-context gate:

- must target the same review pack;
- must be `ready_for_context_bundle`;
- must have `context_bundle_command_ready: true`;
- must not record provider calls, human acceptance, or long-term memory writes;
- must match the submitted decisions by decision id, target ref, decision
  value, `decided_by`, and evidence refs.

Ready reports add `decision_intake_gate` to the projection. Blocked or stale
reports raise before context artifacts are written.

## Boundary Evidence

- This is no-call protocol enforcement only.
- No human decisions were filled or approved.
- No context bundle was produced from the real blocked Loulan intake report.
- No provider call, generated media copy, Company memory write, approval
  inference, business validation, or durable Memory runtime was added.

## Real Blocked Probe

```powershell
.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-context-bundle --review-pack data\processed\runs\loulan_human_review_pack\local_probe\loulan_human_review_pack.json --decisions data\processed\runs\loulan_decision_intake\real_probe_2026_06_01\loulan_decisions.unfilled_from_worksheet.json --decision-intake-report data\processed\runs\loulan_decision_intake\real_probe_2026_06_01\loulan_decision_intake_report.json --created-at "2026-06-01T18:30:00+08:00" --output data\processed\runs\loulan_context_bundle\intake_gate_probe_2026_06_01
# exit 1
# Loulan context bundle projection failed: decision intake report must be ready_for_context_bundle
```

No output directory was created for the blocked probe.

## Verification Snapshot

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_context_bundle.py -q
# 9 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_decision_intake.py tests\test_loulan_decision_worksheet.py tests\test_loulan_decision_review_pack.py tests\test_loulan_decision_template.py tests\test_loulan_context_bundle.py tests\test_contract_examples.py tests\test_agentflow_contract_audit.py tests\test_cli_command_registry_boundaries.py -q
# 64 passed

.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-context-bundle --help
# passed; shows --decision-intake-report

.\.venv\Scripts\python.exe -B -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -B -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
# pass

.\.venv\Scripts\python.exe -B -m pytest --assert=plain -q
# 735 passed

git diff --check
# no whitespace errors; CRLF normalization warnings only
```

## Next Work

- A human still needs to fill Loulan decisions before a real
  `ready_for_context_bundle` intake report can exist.
- After that, rerun `loulan-context-bundle` with `--decision-intake-report`,
  then feed the resulting context projection into `loulan-api-workbench-plan`.
- Keep live provider calls blocked until an explicit capability gate and local
  provider config are authorized.
