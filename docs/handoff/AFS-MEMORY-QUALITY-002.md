# AFS-MEMORY-QUALITY-002 - Evidence Reuse Quality Review

Status: DONE

Date: 2026-05-27

## Outcome

Added a side-effect-free review contract for the Local Alpha 0.4 evidence reuse
path:

```text
runtime evidence
-> operator feedback source
-> memory candidate
-> promotion decision
-> context bundle
-> second-pass prompt
```

This is a structural traceability gate. It does not execute a second pass,
write durable memory, create a database/vector store/RAG layer, call providers,
or claim product quality improvement.

## Changed Surfaces

- `agentflow/memory/promotion.py`
- `examples/agentflow/memory_evidence_reuse_review.example.json`
- `agentflow/contracts/examples.py`
- `examples/agentflow/contract_registry.example.json`
- `tests/test_agentflow_asset_memory_validator.py`
- `tests/test_agentflow_contract_helpers.py`
- `tests/test_contract_examples.py`
- `docs/agentflow_memory_contract.md`
- `docs/local_alpha_0_4_product_loop_goals.md`
- `docs/local_alpha_0_4_scenario_package.md`

## Acceptance

- [x] Review artifact declares `runtime_status: not_implemented`.
- [x] Review artifact declares `does_not_execute: true`.
- [x] Review artifact declares `writes_long_term_memory: false`.
- [x] Runtime evidence refs include run, quality, review, and package reports.
- [x] Feedback source points back to runtime evidence.
- [x] Context bundle references memory candidate, promotion decision, and
      runtime evidence.
- [x] Second-pass prompt references the context bundle, memory candidate, and
      promotion decision.
- [x] Rejected or expired promotion decisions cannot pass context reuse review.
- [x] Human acceptance, business validation, and quality improvement claims are
      separate labels.
- [x] Examples avoid private local paths, generated media paths, provider
      credentials, tokens, cookies, and signed URLs.

## Concerns

- The committed example uses logical refs only. It intentionally does not read
  ignored runtime artifacts under `data/processed/`.
- The sample promotion decision is `promoted`, but the current meaning is
  bounded context reuse only. It still does not write durable project memory.
- No human acceptance or business validation has been recorded for the real
  Local Alpha 0.4 product package.
- No actual second-pass run has been executed from the context bundle.

## Verification

```powershell
python -m pytest tests/test_agentflow_asset_memory_validator.py::test_evidence_reuse_review_accepts_local_alpha_0_4_chain_example tests/test_agentflow_asset_memory_validator.py::test_evidence_reuse_review_fails_when_second_pass_loses_promotion_decision_refs tests/test_agentflow_asset_memory_validator.py::test_evidence_reuse_review_fails_when_context_writes_long_term_memory
```

Result: 3 passed.

Additional verification completed:

```powershell
python -m pytest tests/test_agentflow_asset_memory_validator.py tests/test_agentflow_contract_audit.py tests/test_contract_examples.py tests/test_agentflow_contract_helpers.py
python -m pytest tests/test_agentflow_asset_memory_validator.py tests/test_contract_examples.py tests/test_agentflow_contract_helpers.py tests/test_posterflow_workflow.py tests/test_posterflow_quality.py tests/test_posterflow_provider.py
python -m pytest
python -m apps.cli.main alpha-smoke --json
python -m compileall agentflow\memory agentflow\contracts agentflow\harness narratostudio\posterflow narratocut\harness apps\web_bridge apps\cli
git diff --check
```

Results:

- 52 focused contract/audit tests passed.
- 73 focused memory/contract/PosterFlow tests passed.
- Full test suite passed: 567 passed.
- `alpha-smoke --json` returned expected `blocked` status because image
  provider env is unset.
- Compile checks passed.
- Diff whitespace check passed with Windows line-ending warnings only.

## Next Step

Recommended next lanes:

- `AFS-ALPHA-0-4-ACCEPTANCE`: reconcile 0.4 runtime, Web, and memory-quality
  evidence into an acceptance package.
- `AFS-MEMORY-REVIEW-CLI-001`: expose this validator as a read-only CLI/review
  command.
- `AFS-WEB-EVIDENCE-SUMMARY-001`: show memory reuse review status in Web after
  the contract is stable.

Keep `AFS-POSTER-LIVE-002` blocked unless local image-provider env is
intentionally configured.
