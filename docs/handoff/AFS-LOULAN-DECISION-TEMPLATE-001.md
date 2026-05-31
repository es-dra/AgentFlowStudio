# AFS-LOULAN-DECISION-TEMPLATE-001

Status: no-call Loulan human decision template implemented.

## What Changed

- Added `agentflow.memory.loulan_decision_template` to build a fillable
  `agentflow_loulan_promotion_decisions` template from a human review pack.
- Added `loulan-decision-template` CLI.
- Added sanitized contract example
  `examples/agentflow/loulan_promotion_decisions_template.example.json`.
- Added `docs/loulan_decision_template_contract.md` and registered the contract
  in the AgentFlow registry and audit report.

## Current Capability

The command:

```powershell
.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-decision-template --review-pack data\processed\runs\loulan_human_review_pack\local_probe\loulan_human_review_pack.json --created-at "2026-06-01T12:30:00+08:00" --output data\processed\runs\loulan_decision_template\local_probe
```

writes:

- `loulan_decisions.template.json`
- `loulan_decisions.template.md`

The current real local smoke generated 7 pending decision slots. It records no
provider calls, no human acceptance, and no durable memory writes.

## Template Semantics

- `shot:*` slots allow `approve_anchor`, `reject`, and `request_repair`.
- `character:*` slots allow `promoted`, `merged`, `rejected`, and `expired`.
- All slots start with `decision: pending_human_review`.
- All slots keep `decided_by` and `evidence_refs` empty until a person fills
  the record.
- An unfilled template passed to `loulan-context-bundle` blocks with
  `blocked_invalid_decisions`.

## Safety Boundaries

- No provider calls.
- No generated media committed.
- No Company knowledge-base write.
- No durable Memory runtime, DB, vector store, hosted service, or RAG.
- No automatic approval from review-pack drafts or templates.
- No product acceptance, provider smoke, business validation, or quality claim.

## Verification Snapshot

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_decision_template.py -q
# 4 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_context_bundle.py tests\test_contract_examples.py tests\test_agentflow_contract_audit.py tests\test_cli_command_registry_boundaries.py -q
# 35 passed

.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-decision-template --review-pack data\processed\runs\loulan_human_review_pack\local_probe\loulan_human_review_pack.json --created-at "2026-06-01T12:30:00+08:00" --output data\processed\runs\loulan_decision_template\local_probe
# succeeded; 7 pending decision slots; provider calls not started

.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-context-bundle --review-pack data\processed\runs\loulan_human_review_pack\local_probe\loulan_human_review_pack.json --decisions data\processed\runs\loulan_decision_template\local_probe\loulan_decisions.template.json --created-at "2026-06-01T12:45:00+08:00" --output data\processed\runs\loulan_context_bundle\template_probe
# succeeded; decision audit blocked_invalid_decisions; context bundle blocked
```

Ignored local probe output:

```text
data/processed/runs/loulan_decision_template/local_probe/
data/processed/runs/loulan_context_bundle/template_probe/
```

## Next Work

- Fill a real decision file only after human review.
- Rerun `loulan-context-bundle` with the filled decision file.
- If a character anchor is promoted or merged, rerun the Loulan API workbench
  dry-run to inspect request previews.
