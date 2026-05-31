# AFS-LOULAN-WEB-DECISION-INTAKE-001

Status: Loulan decision intake selected-file rendering implemented.

## Scope

The Web memory workbench now recognizes:

```text
agentflow_loulan_decision_intake_report
```

Selected-file projection adds:

- `workspace.loulanDecisionIntakeReport`
- "Decision intake report" bundle card
- "decision intake" protocol control
- next-pass status/action from `intake_status`
- selected-file inspector facts for context-bundle readiness, ready count,
  pending count, invalid count, and human acceptance flag
- "Decision Intake" timeline node

## Boundary Evidence

- Rendering is read-only.
- The browser still requires explicit selected files.
- No directory scanning, browser persistence, workflow execution, context
  projection, artifact write, provider call, Company memory write, or approval
  inference was added.
- `blocked_pending_manual_decisions` remains blocked and is not treated as
  human acceptance.

## Verification Snapshot

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_memory_loulan_decision_context_static.py -q
# 4 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_memory_static_structure.py tests\test_web_memory_canvas_static.py tests\test_web_memory_interaction_static.py tests\test_web_memory_sample_static.py tests\test_web_memory_feedback_static.py tests\test_web_memory_loulan_package_static.py tests\test_web_memory_loulan_human_review_static.py tests\test_web_memory_loulan_decision_context_static.py tests\test_web_static_artifact_viewer.py tests\test_web_static_artifact_boundaries.py -q
# 37 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_decision_intake.py tests\test_loulan_decision_worksheet.py tests\test_contract_examples.py tests\test_agentflow_contract_audit.py tests\test_cli_command_registry_boundaries.py -q
# 44 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain -q
# 731 passed

.\.venv\Scripts\python.exe -B -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -B -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
# pass

git diff --check
# no whitespace errors; CRLF normalization warnings only
```

Real selected-file static probe loaded the current ignored Loulan package, API
plan, human review pack, decision review pack, worksheet, and intake report.
The view reported `blocked_pending_manual_decisions`,
`context_bundle_ready=false`, 47 pending decisions, and no human acceptance.

## Next Work

- After a human fills a decisions file and intake reports
  `ready_for_context_bundle`, run `loulan-context-bundle`.
- Keep live provider calls blocked until an explicit capability gate and local
  provider config are authorized.
