# AFS-LOULAN-DECISION-WORKSHEET-001

Status: no-call Loulan decision worksheet implemented and real probe run.

## Scope

New command:

```text
loulan-decision-worksheet
```

Input artifact:

```text
agentflow_loulan_decision_review_pack
```

Output artifacts:

```text
loulan_decision_worksheet.json
loulan_decision_worksheet.md
```

## Real Probe

Input source remained the previous ignored Loulan decision review output:

```text
data/processed/runs/loulan_decision_review_pack/real_probe_2026_06_01/
```

Decision worksheet output:

```text
data/processed/runs/loulan_decision_worksheet/real_probe_2026_06_01/
```

Result:

| Check | Result |
|---|---|
| Worksheet status | awaiting_manual_decisions |
| Required decisions | 47 |
| Decision slots | 47 |
| Pending count | 47 |
| Missing slots | 0 |
| Invalid decisions | 0 |
| Ready decisions | 0 |
| Shot rows | 5 |
| Asset rows | 42 |
| Provider calls | not started |
| Human acceptance | not recorded |
| Durable Memory runtime | not implemented |

## Boundary Evidence

- The worksheet is a copy-only manual fill surface.
- It keeps `decision`, `decided_by`, `evidence_refs`, and `review_note` empty
  in each `copy_target_json` row.
- It does not approve, reject, promote, merge, expire, or repair any slot.
- It does not call image/video/LLM/ASR providers.
- It does not write Company memory or durable Memory runtime state.
- Ready rows can be displayed as ready for context projection, but the
  worksheet itself still does not claim human acceptance or business
  validation.
- Negative context-bundle probe rejects the worksheet JSON because its
  `artifact_type` is not `agentflow_loulan_promotion_decisions`.
- Safety scan over the real worksheet JSON/Markdown found no absolute local
  paths, media refs, provider secrets, signed URLs, bearer headers, or API-key
  markers.

## Verification Snapshot

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_decision_worksheet.py -q
# 6 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_decision_worksheet.py tests\test_loulan_decision_review_pack.py tests\test_loulan_decision_template.py tests\test_loulan_context_bundle.py tests\test_contract_examples.py tests\test_agentflow_contract_audit.py tests\test_cli_command_registry_boundaries.py -q
# 53 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain -q
# 722 passed

.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-decision-worksheet --help
# passed

.\.venv\Scripts\python.exe -B -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -B -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-context-bundle --review-pack data\processed\runs\loulan_api_context_probe\real_probe_2026_06_01\03_human_review\loulan_human_review_pack.json --decisions data\processed\runs\loulan_decision_worksheet\real_probe_2026_06_01\loulan_decision_worksheet.json --created-at "2026-06-01T17:35:00+08:00" --output data\processed\runs\loulan_decision_worksheet\context_negative_probe
# failed as expected: Loulan decisions artifact_type must be agentflow_loulan_promotion_decisions

.\.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
# passed

git diff --check
# passed; CRLF normalization warnings only
```

## Next Work

- If useful, render `agentflow_loulan_decision_worksheet` in the Web memory
  workbench as a selected-file copy/fill aid.
- After a human fills a decisions file, run `loulan-context-bundle` with that
  explicit file.
- Keep live provider calls blocked until a separate task explicitly authorizes
  the relevant capability gate and local provider config.
