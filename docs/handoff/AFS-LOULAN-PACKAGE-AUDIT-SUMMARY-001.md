# AFS-LOULAN-PACKAGE-AUDIT-SUMMARY-001

## Scope

Carry safe Loulan project-audit summary counts inside the no-call memory package
and Web Memory Workbench package review path.

## What Changed

- `loulan-memory-package` still reads only explicit `project_manifest.json`
  audit refs, but now follows safe project-relative JSON refs to copy a
  whitelist of scalar summary counts.
- Audit summary extraction lives in `agentflow/memory/loulan_project_audits.py`
  so the package builder remains focused.
- `project_audits.manifest_reference.summary` can expose manifest count,
  registry asset count, error count, missing ref/hash counts, and canonical
  registry failures such as `invalid_asset_types` and `invalid_statuses`.
- `project_audits.text_encoding.summary` can expose checked text files,
  decode errors, marker hits, and total errors.
- `project_audits.phase_gate.summary` can expose phase counts, expected
  blocks, failures, registry context counts, and pending B01 decisions.
- Package Markdown now includes manifest errors, invalid asset/status counts,
  text encoding errors, and phase gate failures.
- Memory Workbench package review shows those counts in the Project audits
  bundle card, protocol controls, and inspector facts.

## Safety Boundary

The package does not copy raw audit bodies. It only copies whitelisted scalar
summary values from safe relative refs, and the existing unsafe-output scan
still rejects absolute local paths, media refs, provider URLs, bearer headers,
signed URLs, API keys, and secret-like values.

## Real Probe State

The current no-call probe over the Loulan asset project produced:

- Manifest reference audit: `pass`
- Manifest audit errors: `0`
- Invalid asset types: `0`
- Invalid statuses: `0`
- Text encoding audit: `pass`
- Text encoding errors: `0`
- Phase gate audit: `blocked_until_b01_human_review`
- Phase gate failures: `0`
- Pending B01 decisions: `5`
- Eligible refs: `3`
- Blocked refs: `90`
- Provider calls: not started
- Durable Memory write: false
- Safety scan: no absolute local paths, provider URLs, tokens, signed URLs,
  media refs, API keys, or secret-like values found

## Verification

```powershell
.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_memory_package.py tests\test_web_memory_loulan_package_static.py -q
.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_memory_package.py tests\test_web_memory_loulan_package_static.py tests\test_web_static_loulan_project_audit_probe.py tests\test_web_static_loulan_governance_audits.py -q
.venv\Scripts\python.exe -B -m pytest --assert=plain -q
.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
git diff --check
```

Results:

- Focused package/Web tests: `5 passed`.
- Related Loulan package/audit tests: `8 passed`.
- Package fixture/API/human-review reuse tests: `19 passed`.
- Contract/example tests: `34 passed`.
- Full suite: `763 passed`.
- Staging preflight: pass.
- `git diff --check`: no whitespace errors; CRLF touch warnings only.

## Boundaries

- No provider calls.
- No media generation or media copy.
- No B01 decision apply.
- No context projection execution.
- No human acceptance recorded.
- No durable Memory write.
- No Company knowledge-base material copied into the repo.
