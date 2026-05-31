# AFS-LOULAN-WEB-DECISION-WORKSHEET-001

Status: Loulan decision worksheet selected-file rendering implemented.

## Scope

The Web memory workbench now recognizes:

```text
agentflow_loulan_decision_worksheet
```

Selected-file projection adds:

- `workspace.loulanDecisionWorksheet`
- "Decision worksheet" bundle card
- "decision worksheet" protocol control
- next-pass status/action from `worksheet_status`
- selected-file inspector facts for rows, manual template rows, provider flag,
  and human acceptance flag
- "Decision Worksheet" timeline node
- a focused `memory-workbench-loulan-artifacts.js` module for Loulan inspector
  and timeline helpers

## Boundary Evidence

- Rendering is read-only.
- The browser still requires explicit selected files.
- No directory scanning, browser persistence, workflow execution, artifact
  write, provider call, Company memory write, or approval inference was added.
- `awaiting_manual_decisions` stays blocked and is not treated as human
  acceptance.
- Worksheet `manual_transfer_template` rows are displayed as review context
  only; browser editing and persistence remain out of scope.

## Verification Snapshot

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_memory_loulan_decision_context_static.py -q
# 3 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_memory_loulan_decision_context_static.py tests\test_web_memory_loulan_package_static.py tests\test_web_memory_loulan_human_review_static.py -q
# 6 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_memory_static_structure.py tests\test_web_memory_canvas_static.py tests\test_web_memory_interaction_static.py tests\test_web_memory_sample_static.py tests\test_web_memory_feedback_static.py tests\test_web_memory_loulan_package_static.py tests\test_web_memory_loulan_human_review_static.py tests\test_web_memory_loulan_decision_context_static.py tests\test_web_static_artifact_viewer.py tests\test_web_static_artifact_boundaries.py -q
# 36 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_decision_worksheet.py tests\test_loulan_decision_review_pack.py tests\test_loulan_decision_template.py tests\test_loulan_context_bundle.py tests\test_contract_examples.py tests\test_agentflow_contract_audit.py tests\test_cli_command_registry_boundaries.py -q
# 53 passed

.\.venv\Scripts\python.exe -B -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -B -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
# passed

git diff --check
# passed; CRLF normalization warnings only

.\.venv\Scripts\python.exe -B -m pytest --assert=plain -q
# 723 passed
```

In-app Browser tooling was not exposed in this session, so verification used
static Node-backed Web tests rather than a browser-console pass.

## Next Work

- After a human fills a decisions file, run `loulan-context-bundle` and load
  the ready projection into the workbench.
- Keep live provider calls blocked until an explicit capability gate and local
  provider config are authorized.
