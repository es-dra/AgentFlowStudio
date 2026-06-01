# AFS-PRODUCTION-MEMORY-OPERATOR-LOOP-FEEDBACK-CANDIDATE-OVERLAY-001

Status: verified locally on
`codex/afs-production-memory-operator-loop-feedback-candidate-overlay-001`.

## Scope

Embed the explicit operator feedback candidate decision overlay into the
generic no-provider operator-loop manifest.

This follows
`AFS-PRODUCTION-MEMORY-OPERATOR-FEEDBACK-CANDIDATE-OVERLAY-001`: the standalone
reviewed overlay still exists, and the operator-loop command can now include
the same packet/decision pair in one auditable operator run.

## Implementation Files

- `agentflow/memory/production_operator_loop.py`
- `agentflow/memory/production_operator_manifest.py`
- `agentflow/memory/production_operator_feedback_candidate_manifest.py`
- `agentflow/memory/production_operator_outputs.py`
- `apps/cli/production_memory_operator_command.py`
- `tests/test_production_memory_operator_loop_feedback_candidate_overlay.py`

## CLI

```powershell
python -m apps.cli.main production-memory-loop-run-operator-no-provider examples/agentflow/production_memory_loop.example.json --generated-at 2026-06-02T10:40:00+08:00 --source-kb-status restructuring_or_unknown --operator-feedback-candidate-packet data/processed/runs/production_memory_loop/operator_feedback_candidate/operator_feedback_candidate_packet.json --operator-feedback-candidate-promotion-decision data/processed/runs/production_memory_loop/operator_feedback_candidate_promotion/operator_feedback_candidate_promotion_decision.json --output data/processed/runs/production_memory_loop/operator_loop_with_feedback_candidate_overlay
```

The operator feedback candidate packet and promotion decision must be supplied
together. When supplied, the command writes:

- `operator_feedback_candidate_promotion_decision/operator_feedback_candidate_promotion_decision.json`
- `operator_feedback_candidate_promotion_decision/operator_feedback_candidate_promotion_decision.md`
- `operator_feedback_candidate_reviewed_feedback/derived_production_memory_loop.json`
- `operator_feedback_candidate_reviewed_feedback/production_memory_loop_run.json`
- `operator_feedback_candidate_reviewed_feedback/context_bundle.json`
- `operator_feedback_candidate_reviewed_feedback/pass_readiness.json`
- `operator_feedback_candidate_reviewed_feedback/next_pass_bundle.json`
- `operator_feedback_candidate_reviewed_feedback/operator_feedback_candidate_promotion_overlay.json`

The operator-loop manifest adds:

- `operator_feedback_candidate_promotion_decision`
- `operator_feedback_candidate_promotion_overlay`

## Contract Boundaries

- pending promotion templates cannot drive the overlay.
- packet-only or decision-only CLI/builder input fails validation.
- promoted and merged decisions can enter the derived reviewed context bundle.
- rejected, expired, and blocked decisions stay blocked.
- `provider_calls_started: false`
- `writes_long_term_memory: false`
- `writes_company_kb: false`
- no provider execution
- no next-pass execution
- no Web behavior change
- no Loulan-specific behavior
- no Company KB write
- no human acceptance or business validation claim

## Verification

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_operator_loop_feedback_candidate_overlay.py -q
```

Initial red result: builder rejected
`operator_feedback_candidate_packet` as an unexpected keyword and the CLI
rejected `--operator-feedback-candidate-packet`. A later red test also exposed
missing validation for packet project pairing.

Green result after implementation: `5 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m py_compile agentflow/memory/production_operator_loop.py agentflow/memory/production_operator_manifest.py agentflow/memory/production_operator_outputs.py agentflow/memory/production_operator_feedback_candidate_manifest.py apps/cli/production_memory_operator_command.py tests/test_production_memory_operator_loop_feedback_candidate_overlay.py
```

Result: passed.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_operator_loop.py tests/test_production_memory_operator_loop_promotion.py tests/test_production_memory_operator_feedback.py tests/test_production_memory_operator_feedback_candidate.py tests/test_production_memory_operator_feedback_candidate_promotion.py tests/test_production_memory_operator_feedback_candidate_overlay.py tests/test_production_memory_operator_loop_feedback_candidate_overlay.py tests/test_contract_examples.py tests/test_cli_command_registry_boundaries.py -q
```

Result: `59 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main --help
```

Result: passed.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_web_static_production_memory_operator_loop.py tests/test_web_static_production_memory_operator_feedback_candidate.py tests/test_web_static_production_memory_operator_feedback.py -q
```

Result: `7 passed`.

CLI smoke generated an ignored operator-loop seed, captured evidence-only
operator feedback, drafted a candidate-only packet, wrote an explicit promoted
decision, then generated an operator loop with embedded
feedback-candidate overlay under:

```text
data/processed/runs/production_memory_loop/operator_loop_feedback_candidate_overlay_smoke/
```

The final operator-loop manifest reported:

- chain status: `ready`
- operator feedback candidate decision effect: `included_in_context`
- manifest nodes:
  - `operator_feedback_candidate_promotion_decision`
  - `operator_feedback_candidate_promotion_overlay`

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest
```

Result: `778 passed` on Python 3.12.12.

Code file line counts remain under the 300-line target:

- `agentflow/memory/production_operator_loop.py`: 227 lines
- `agentflow/memory/production_operator_manifest.py`: 293 lines
- `agentflow/memory/production_operator_outputs.py`: 102 lines
- `agentflow/memory/production_operator_feedback_candidate_manifest.py`: 95
  lines
- `apps/cli/production_memory_operator_command.py`: 147 lines
- `tests/test_production_memory_operator_loop_feedback_candidate_overlay.py`:
  166 lines

## Remaining Risks

- Web rendering does not yet show a dedicated embedded
  operator-feedback-candidate promotion card inside the operator-loop canvas.
- Browser-level verification was not run for this backend-only slice.
- Optional provider validation was not attempted or required.
- Machine verification is not human acceptance or business validation.
