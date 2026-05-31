# AFS-LOULAN-HUMAN-REVIEW-001

Status: no-call Loulan B01 human review pack implemented.

## What Changed

- Added `agentflow.memory.loulan_human_review_pack` to prepare
  `agentflow_loulan_human_review_pack` artifacts from a Loulan memory package,
  API workbench plan, and explicit B01 review manifests.
- Added `loulan-human-review-pack` CLI.
- Added sanitized contract example
  `examples/agentflow/loulan_human_review_pack.example.json`.
- Added `docs/loulan_human_review_pack_contract.md` and registered the contract
  in the AgentFlow registry and audit report.
- Extended the Web memory workbench to recognize selected Loulan human review
  packs and reflect review status in bundle, inspector, feedback, timeline, and
  next-pass panels.

## Current Capability

The command:

```powershell
.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-human-review-pack --package data\processed\runs\loulan_memory_package\local_probe\loulan_memory_package.json --api-plan data\processed\runs\loulan_api_workbench\local_probe\loulan_api_workbench_plan.json --project-root "D:\Projects\LoulanSceneAssets" --block-id B01 --created-at "2026-06-01T11:00:00+08:00" --output data\processed\runs\loulan_human_review_pack\local_probe
```

writes:

- `loulan_human_review_pack.json`
- `shot_review_cards.json`
- `promotion_decision_drafts.json`
- `feedback_event_draft.json`
- `loulan_human_review_pack.md`

On the current real Loulan probe, B01 has 5 shot review cards. B01-S03 remains
blocked because it records rejected previous evidence, and
`character:zhou_tong_school_v1` plus `character:zhou_tong_qipao_front_v1`
remain candidate memory refs pending human review. No next-pass context reuse is
opened by this artifact.

## Safety Boundaries

- No provider calls.
- No Loulan source restructuring.
- No generated media committed.
- No Company knowledge-base write.
- No durable Memory runtime, DB, vector store, hosted service, or RAG.
- No human acceptance, provider smoke, business validation, or quality claim.
- Promotion decision drafts are templates only; decisions stay
  `pending_human_review`.

## Verification Snapshot

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_human_review_pack.py tests\test_web_memory_loulan_human_review_static.py tests\test_loulan_api_workbench.py tests\test_loulan_memory_package.py tests\test_web_memory_loulan_package_static.py tests\test_contract_examples.py tests\test_agentflow_contract_audit.py tests\test_cli_command_registry_boundaries.py -q
# 47 passed

.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-human-review-pack --package data\processed\runs\loulan_memory_package\local_probe\loulan_memory_package.json --api-plan data\processed\runs\loulan_api_workbench\local_probe\loulan_api_workbench_plan.json --project-root "D:\Projects\LoulanSceneAssets" --block-id B01 --created-at "2026-06-01T11:00:00+08:00" --output data\processed\runs\loulan_human_review_pack\local_probe
# succeeded; 5 shot cards; next pass blocked; provider calls not started

.\.venv\Scripts\python.exe -B -m pytest --assert=plain -p no:cacheprovider --basetemp data\processed\pytest-basetemp\loulan-human-review-pack
# 693 passed

.\.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
# passed

git diff --check
# passed; CRLF normalization warnings only
```

Ignored local probe output:

```text
data/processed/runs/loulan_human_review_pack/local_probe/
```

Web verification used static Node tests. The in-app browser control tool was
not exposed in this session, so no browser-console run was performed for this
node.

## Next Work

- Human review B01 shot cards and the two candidate Zhou Tong character anchors.
- Convert human decisions into explicit promotion/rejection records.
- Rerun `loulan-memory-package`, `loulan-api-workbench-plan`, and
  `loulan-human-review-pack` after at least one anchor is promoted.
- Only after promoted anchors exist, inspect whether the API workbench produces
  request previews suitable for a separate gated image-provider task.
