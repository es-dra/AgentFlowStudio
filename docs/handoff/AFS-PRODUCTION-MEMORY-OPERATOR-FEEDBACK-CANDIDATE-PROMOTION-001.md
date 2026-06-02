# AFS-PRODUCTION-MEMORY-OPERATOR-FEEDBACK-CANDIDATE-PROMOTION-001

Status: verified locally on
`codex/afs-production-memory-operator-feedback-candidate-promotion-001`.

## Scope

Convert a selected
`agentflow_production_memory_operator_feedback_candidate_packet` into an
explicit no-provider operator decision artifact.

This closes the backend review gap after candidate-only operator feedback
drafting. It does not write durable memory, write Company KB, execute the next
pass, render in Web, or claim human acceptance.

## Implementation Files

- `agentflow/memory/production_operator_feedback_candidate_promotion.py`
- `apps/cli/production_memory_operator_feedback_candidate_promotion_command.py`
- `apps/cli/command_registry.py`
- `tests/test_production_memory_operator_feedback_candidate_promotion.py`

## CLI

```powershell
python -m apps.cli.main production-memory-loop-review-operator-feedback-candidate data/processed/runs/production_memory_loop/operator_feedback_candidate/operator_feedback_candidate_packet.json --decision promoted --rationale "Traceable operator feedback selected for the next context overlay." --decided-at 2026-06-02T08:30:00+08:00 --output data/processed/runs/production_memory_loop/operator_feedback_candidate_promotion
```

The command writes:

- `operator_feedback_candidate_promotion_decision.json`
- `operator_feedback_candidate_promotion_decision.md`

## Contract Boundaries

- accepted candidate packets still require an explicit operator decision before
  reuse.
- pending promotion templates cannot be used as reviewed decisions.
- promoted and merged decisions set `candidate_reuse_allowed: true`.
- rejected, expired, and blocked decisions keep candidate reuse blocked.
- blocked candidates cannot be promoted or merged.
- the decision records source packet, source feedback event, source pending
  template id, candidate id, reviewer role, rationale, and decision effect.
- `provider_calls_started: false`
- `writes_long_term_memory: false`
- `writes_company_kb: false`
- `decision_is_durable_memory_write: false`
- `decision_writes_company_kb: false`
- `human_acceptance: not_claimed`

## Verification

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_operator_feedback_candidate_promotion.py -q
```

Initial red result: CLI invocation failed because
`production-memory-loop-review-operator-feedback-candidate` was not registered.
A later red contract check failed because the decision artifact did not yet
record the source pending template id.

Green result after implementation: `7 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m py_compile agentflow/memory/production_operator_feedback_candidate_promotion.py apps/cli/production_memory_operator_feedback_candidate_promotion_command.py apps/cli/command_registry.py
```

Result: passed.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_operator_feedback_candidate_promotion.py tests/test_production_memory_operator_feedback_candidate.py tests/test_production_memory_operator_feedback.py tests/test_production_memory_operator_loop.py tests/test_production_memory_operator_loop_promotion.py tests/test_production_memory_next_pass_promotion.py tests/test_contract_examples.py tests/test_cli_command_registry_boundaries.py -q
```

Result: `54 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main --help
```

Result: passed; the new
`production-memory-loop-review-operator-feedback-candidate` command is
registered.

CLI smoke generated an ignored operator-loop manifest, captured evidence-only
operator feedback, drafted a candidate-only packet, then wrote an explicit
promoted decision under:

```text
data/processed/runs/production_memory_loop/operator_feedback_candidate_promotion_smoke/
```

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest
```

Result: `768 passed` on Python 3.12.12.

```powershell
git diff --check
```

Result: exit 0; CRLF normalization warnings only.

Added-diff and new-file sensitive scan produced no hits for Company source path
copies, configured credential markers, key shapes, customer markers, cookies,
or signed-link markers.

Code file line counts remain under the 300-line target:

- `agentflow/memory/production_operator_feedback_candidate_promotion.py`: 233
  lines
- `apps/cli/production_memory_operator_feedback_candidate_promotion_command.py`:
  68 lines
- `apps/cli/command_registry.py`: 163 lines
- `tests/test_production_memory_operator_feedback_candidate_promotion.py`: 166
  lines

## Remaining Risks

- This slice does not build a next-context overlay from the operator feedback
  candidate decision. A follow-up should decide whether promoted or merged
  operator feedback candidates can be added to a derived context bundle.
- This slice does not add Web rendering for
  `agentflow_production_memory_operator_feedback_candidate_promotion_decision`.
- No provider validation was attempted or required.
- Machine tests are not human acceptance or business validation.
