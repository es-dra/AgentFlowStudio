# AFS-LOULAN-DECISION-REVIEW-001

Status: no-call Loulan decision review pack implemented and real probe run.

## Scope

New command:

```text
loulan-decision-review-pack
```

Input artifacts:

```text
agentflow_loulan_human_review_pack
agentflow_loulan_promotion_decisions
```

Output artifacts:

```text
loulan_decision_review_pack.json
loulan_decision_review_pack.md
```

## Real Probe

Input source remained the previous ignored Loulan context probe output:

```text
data/processed/runs/loulan_api_context_probe/real_probe_2026_06_01/
```

Decision review output:

```text
data/processed/runs/loulan_decision_review_pack/real_probe_2026_06_01/
```

Result:

| Check | Result |
|---|---|
| Review status | blocked_pending_human_input |
| Required decisions | 47 |
| Decision slots | 47 |
| Pending count | 47 |
| Missing slots | 0 |
| Invalid decisions | 0 |
| Ready decisions | 0 |
| Shot slots | 5 |
| Asset slots | 42 |
| Provider calls | not started |
| Human acceptance | not recorded |
| Durable Memory runtime | not implemented |

## Boundary Evidence

- The pack is a review gap report only.
- It does not approve, reject, promote, merge, expire, or repair any slot.
- It does not call image/video/LLM/ASR providers.
- It does not write Company memory or durable Memory runtime state.
- It treats real Loulan `asset:*` refs as asset-memory slots with
  `promoted`, `merged`, `rejected`, and `expired` as the allowed decisions.
- Context bundle projection now recognizes both `character:*` and `asset:*`
  refs as asset memory refs when explicit human decisions are eventually
  supplied.

## Verification Snapshot

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_decision_review_pack.py tests\test_loulan_decision_template.py tests\test_loulan_context_bundle.py -q
# 16 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_decision_review_pack.py tests\test_contract_examples.py tests\test_agentflow_contract_audit.py -q
# 34 passed
```

Full verification is recorded in the final task closeout.

## Next Work

- Manually fill a copied Loulan decisions file from the decision review pack.
- Re-run `loulan-context-bundle` with explicit human decisions.
- Re-run `loulan-api-workbench-plan --context-projection` only after the
  context projection is ready.
- Keep live provider calls blocked until a separate task explicitly authorizes
  the relevant capability gate and local provider config.
