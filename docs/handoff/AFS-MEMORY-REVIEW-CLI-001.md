# AFS-MEMORY-REVIEW-CLI-001

Status: implemented as a read-only structural review command.

## Scope

Expose the existing `agentflow_memory_evidence_reuse_review` validator through
a CLI command:

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main memory-evidence-reuse-review `
  --review examples\agentflow\memory_evidence_reuse_review.example.json `
  --candidate examples\agentflow\memory_candidate.example.json `
  --decision examples\agentflow\memory_promotion_decision.example.json
```

The command validates this chain:

```text
runtime evidence
-> feedback source
-> memory candidate
-> promotion decision
-> context bundle
-> second-pass prompt
```

## Boundary

- Reads only explicitly provided JSON files.
- Writes no file by default.
- Writes only validation JSON when `--output` is explicitly supplied.
- Does not scan directories.
- Does not call providers.
- Does not write durable memory.
- Does not execute a real second pass.
- Does not claim human acceptance or business validation.

## Failure Cases Covered

- Broken second-pass prompt promotion-decision refs fail.
- `rejected` promotion decisions fail context reuse.
- UTF-8 BOM JSON inputs are accepted for PowerShell-created files.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_memory_review_cli.py -q
```

Result: 5 passed.

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_memory_review_cli.py tests\test_agentflow_asset_memory_validator.py tests\test_contract_examples.py tests\test_agentflow_contract_helpers.py -q
```

Result: 57 passed.

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main memory-evidence-reuse-review --help
```

Result: command help rendered.

## Next

The natural next lane is `AFS-WEB-EVIDENCE-SUMMARY-001`: let the Web Memory
Workbench display this validation summary from an explicit selected validation
JSON, without scanning, promotion, provider calls, or persistence.
