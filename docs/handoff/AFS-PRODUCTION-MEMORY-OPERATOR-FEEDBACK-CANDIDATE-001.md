# AFS-PRODUCTION-MEMORY-OPERATOR-FEEDBACK-CANDIDATE-001

Status: verified locally on
`codex/afs-production-memory-operator-feedback-candidate-001`.

## Scope

Draft a candidate-only memory packet from an evidence-only
`agentflow_production_memory_operator_feedback_event`.

This is the bridge after an operator records feedback against an operator-loop
manifest node. It can prepare a candidate and a pending promotion decision
template for later review, but it does not promote memory, write Company KB,
write long-term memory, or claim human acceptance.

## Implementation Files

- `agentflow/memory/production_operator_feedback_candidate.py`
- `apps/cli/production_memory_operator_feedback_candidate_command.py`
- `apps/cli/command_registry.py`
- `tests/test_production_memory_operator_feedback_candidate.py`

## CLI

```powershell
python -m apps.cli.main production-memory-loop-draft-operator-feedback-candidate data/processed/runs/production_memory_loop/operator_feedback/operator_feedback_event.json --generated-at 2026-06-02T08:20:00+08:00 --output data/processed/runs/production_memory_loop/operator_feedback_candidate
```

The command writes:

- `operator_feedback_candidate_packet.json`
- `memory_candidate.json`
- `promotion_decision_template.json`
- `operator_feedback_candidate_packet.md`

## Contract Boundaries

- `feedback_is_memory: false`
- `candidate_is_promoted_memory: false`
- `promotion_decision_template.decision: pending`
- `promotion_decision_template.template_only: true`
- `provider_calls_started: false`
- `writes_long_term_memory: false`
- `writes_company_kb: false`
- `human_acceptance: not_claimed`
- rejected operator feedback produces a blocked candidate

## Verification

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_operator_feedback_candidate.py -q
```

Initial red result: CLI invocation failed because
`production-memory-loop-draft-operator-feedback-candidate` was not registered.

Green result after implementation: `6 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m py_compile agentflow/memory/production_operator_feedback_candidate.py apps/cli/production_memory_operator_feedback_candidate_command.py apps/cli/command_registry.py
```

Result: passed.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_operator_feedback_candidate.py tests/test_production_memory_operator_feedback.py tests/test_production_memory_operator_loop.py tests/test_production_memory_operator_loop_promotion.py tests/test_contract_examples.py tests/test_cli_command_registry_boundaries.py -q
```

Result: `42 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main --help
```

Result: passed; the new
`production-memory-loop-draft-operator-feedback-candidate` command is
registered.

CLI smoke generated an ignored operator-loop manifest, captured
`operator_feedback_event.json` as `evidence_only`, then wrote a
candidate-only `operator_feedback_candidate_packet.json` with pending promotion
decision template under:

```text
data/processed/runs/production_memory_loop/operator_feedback_candidate_smoke/
```

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest
```

Result: `759 passed` on Python 3.12.12.

```powershell
git diff --check
```

Result: exit 0; CRLF normalization warnings only.

Added-diff and new-file sensitive scan produced no hits for Company source path
copies, configured credential markers, key shapes, customer markers, cookies,
or signed-link markers.

## Remaining Checks Before Commit

- Stage the verified file set.
- Run staged diff check.
- Create local commit only; do not push or open a PR.

## Remaining Risks

- Web read-only rendering for
  `agentflow_production_memory_operator_feedback_candidate_packet` is not part
  of this slice.
- The pending promotion template is not a reviewed promotion decision and must
  not enter next context.
- No provider validation was attempted or required.
