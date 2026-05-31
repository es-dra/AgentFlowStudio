# AFS-LOULAN-CONTEXT-BUNDLE-001

Status: no-call Loulan context bundle projection implemented.

## What Changed

- Added `agentflow.memory.loulan_context_bundle` to build
  `agentflow_loulan_context_bundle_projection`.
- Added `loulan-context-bundle` CLI.
- Added sanitized contract example
  `examples/agentflow/loulan_context_bundle_projection.example.json`.
- Added `docs/loulan_context_bundle_contract.md` and registered the contract in
  the AgentFlow registry and audit report.

## Current Capability

The command:

```powershell
.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-context-bundle --review-pack data\processed\runs\loulan_human_review_pack\local_probe\loulan_human_review_pack.json --decisions data\processed\runs\loulan_context_bundle\local_probe\loulan_decisions.empty.json --created-at "2026-06-01T12:00:00+08:00" --output data\processed\runs\loulan_context_bundle\local_probe
```

writes:

- `loulan_context_bundle_projection.json`
- `context_bundle.json`
- `next_prompt_draft.json`
- `decision_audit.json`
- `loulan_context_bundle_projection.md`

The current real local smoke used an empty decision file on purpose. The
projection stayed blocked with `blocked_missing_decisions`, 7 missing required
decisions, no provider calls, and no durable memory writes.

## Decision Mapping

- `shot:*` + `approve_anchor` enters `shot_anchor_refs`.
- `shot:*` + `reject` or `request_repair` enters `blocked_refs`.
- `character:*` + `promoted` or `merged` enters `memory_refs`.
- `character:*` + `rejected` or `expired` enters `blocked_refs`.

Every decision must use `decided_by: human` and include `evidence_refs`.

## Safety Boundaries

- No provider calls.
- No generated media committed.
- No Company knowledge-base write.
- No durable Memory runtime, DB, vector store, hosted service, or RAG.
- No automatic approval from review-pack drafts.
- No product acceptance, provider smoke, business validation, or quality claim.

## Verification Snapshot

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_context_bundle.py tests\test_loulan_human_review_pack.py tests\test_contract_examples.py tests\test_agentflow_contract_audit.py tests\test_cli_command_registry_boundaries.py -q
# 39 passed

.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-context-bundle --review-pack data\processed\runs\loulan_human_review_pack\local_probe\loulan_human_review_pack.json --decisions data\processed\runs\loulan_context_bundle\local_probe\loulan_decisions.empty.json --created-at "2026-06-01T12:00:00+08:00" --output data\processed\runs\loulan_context_bundle\local_probe
# succeeded; decision audit blocked_missing_decisions; provider calls not started
```

Ignored local probe output:

```text
data/processed/runs/loulan_context_bundle/local_probe/
```

## Next Work

- Wait for real human B01 decisions.
- Rerun this command with the real decision file.
- If at least one character anchor is promoted or merged, rerun the API
  workbench plan and inspect request previews.
