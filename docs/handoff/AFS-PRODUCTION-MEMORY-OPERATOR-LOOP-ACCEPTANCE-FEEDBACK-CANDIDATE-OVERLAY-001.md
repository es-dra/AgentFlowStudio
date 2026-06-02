# AFS-PRODUCTION-MEMORY-OPERATOR-LOOP-ACCEPTANCE-FEEDBACK-CANDIDATE-OVERLAY-001

Status: verified locally on
`codex/afs-production-memory-operator-loop-acceptance-feedback-overlay-001`.

## Scope

Embed the explicit acceptance feedback candidate decision overlay into the
generic no-provider operator-loop manifest.

This follows `AFS-PRODUCTION-MEMORY-ACCEPTANCE-FEEDBACK-OVERLAY-001`: the
standalone reviewed overlay still exists, and the operator-loop command can now
include the same packet/decision pair in one auditable operator run.

## Implementation Files

- `agentflow/memory/production_operator_loop.py`
- `agentflow/memory/production_operator_manifest.py`
- `agentflow/memory/production_operator_outputs.py`
- `agentflow/memory/production_operator_candidate_promotions.py`
- `agentflow/memory/production_operator_acceptance_feedback_candidate_manifest.py`
- `apps/cli/production_memory_operator_command.py`
- `apps/web/memory-workbench-production-operator-loop.js`
- `apps/web/memory-workbench-production-inspector-facts.js`
- `tests/test_production_memory_operator_loop_acceptance_feedback_candidate_overlay.py`
- `tests/test_web_static_production_memory_operator_loop_acceptance_feedback_candidate.py`

## CLI

```powershell
python -m apps.cli.main production-memory-loop-run-operator-no-provider examples/agentflow/production_memory_loop.example.json --generated-at 2026-06-03T04:20:00+08:00 --source-kb-status restructuring_or_unknown --acceptance-feedback-candidate-packet data/processed/runs/production_memory_loop/acceptance_feedback_candidate/acceptance_feedback_candidate_packet.json --acceptance-feedback-candidate-promotion-decision data/processed/runs/production_memory_loop/acceptance_feedback_candidate_promotion/acceptance_feedback_candidate_promotion_decision.json --output data/processed/runs/production_memory_loop/operator_loop_with_acceptance_feedback_candidate_overlay
```

The acceptance feedback candidate packet and promotion decision must be
supplied together. When supplied, the command writes:

- `acceptance_feedback_candidate_promotion_decision/acceptance_feedback_candidate_promotion_decision.json`
- `acceptance_feedback_candidate_promotion_decision/acceptance_feedback_candidate_promotion_decision.md`
- `acceptance_feedback_candidate_reviewed_feedback/derived_production_memory_loop.json`
- `acceptance_feedback_candidate_reviewed_feedback/production_memory_loop_run.json`
- `acceptance_feedback_candidate_reviewed_feedback/context_bundle.json`
- `acceptance_feedback_candidate_reviewed_feedback/pass_readiness.json`
- `acceptance_feedback_candidate_reviewed_feedback/next_pass_bundle.json`
- `acceptance_feedback_candidate_reviewed_feedback/acceptance_feedback_candidate_promotion_overlay.json`

The operator-loop manifest adds:

- `acceptance_feedback_candidate_promotion_decision`
- `acceptance_feedback_candidate_promotion_overlay`

## Contract Boundaries

- pending promotion templates cannot drive the overlay.
- packet-only or decision-only CLI/builder input fails validation.
- candidate packet and decision `source_project_id` must match the source loop
  project.
- promoted and merged decisions can enter the derived reviewed context bundle.
- rejected, expired, and blocked decisions stay blocked.
- `provider_calls_started: false`
- `writes_long_term_memory: false`
- `writes_company_kb: false`
- no provider execution
- no next-pass execution
- no Loulan-specific behavior
- no Company KB write
- no new human acceptance or business validation claim

## Verification

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_operator_loop_acceptance_feedback_candidate_overlay.py -q
```

Initial red result: builder rejected
`acceptance_feedback_candidate_packet` as an unexpected keyword and the CLI
rejected `--acceptance-feedback-candidate-packet`.

Green result after implementation: `5 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_web_static_production_memory_operator_loop_acceptance_feedback_candidate.py -q
```

Initial red result: the Web operator-loop canvas did not render an acceptance
feedback candidate promotion lane/card/control/fact.

Green result after implementation: `1 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m py_compile agentflow/memory/production_operator_loop.py agentflow/memory/production_operator_manifest.py agentflow/memory/production_operator_outputs.py agentflow/memory/production_operator_candidate_promotions.py agentflow/memory/production_operator_acceptance_feedback_candidate_manifest.py apps/cli/production_memory_operator_command.py tests/test_production_memory_operator_loop_acceptance_feedback_candidate_overlay.py
```

Result: passed.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_operator_loop_acceptance_feedback_candidate_overlay.py tests/test_production_memory_operator_loop_feedback_candidate_overlay.py tests/test_production_memory_acceptance_feedback_candidate_overlay.py tests/test_production_memory_acceptance_feedback_candidate_promotion.py tests/test_production_memory_acceptance_feedback_candidate.py tests/test_production_memory_acceptance_feedback.py tests/test_production_memory_operator_loop.py tests/test_contract_examples.py tests/test_cli_command_registry_boundaries.py -q
```

Result: `65 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_web_static_production_memory_operator_loop_acceptance_feedback_candidate.py tests/test_web_static_production_memory_operator_loop.py tests/test_web_static_production_memory_operator_loop_feedback_candidate.py tests/test_web_static_production_memory_acceptance_feedback.py tests/test_web_static_production_memory_acceptance_feedback_candidate.py tests/test_web_static_production_memory_acceptance_feedback_candidate_promotion.py tests/test_web_static_production_memory_operator_feedback.py tests/test_web_static_production_memory_operator_feedback_candidate.py -q
```

Result: `15 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main --help
```

Result: passed.

CLI smoke generated an ignored operator-loop seed, recorded bounded acceptance
feedback input, drafted a candidate-only packet, wrote an explicit promoted
decision, then generated an operator loop with embedded acceptance-feedback
candidate overlay under:

```text
data/processed/runs/production_memory_loop/ol_accept_overlay_smoke/
```

The final operator-loop manifest reported:

- chain status: `ready`
- acceptance feedback candidate decision effect: `included_in_context`
- manifest nodes:
  - `acceptance_feedback_candidate_promotion_decision`
  - `acceptance_feedback_candidate_promotion_overlay`

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest
```

Result: `861 passed` on Python 3.12.12.

Code file line counts remain under the 300-line target:

- `agentflow/memory/production_operator_loop.py`: 292 lines
- `agentflow/memory/production_operator_manifest.py`: 234 lines
- `agentflow/memory/production_operator_outputs.py`: 134 lines
- `agentflow/memory/production_operator_candidate_promotions.py`: 69 lines
- `agentflow/memory/production_operator_acceptance_feedback_candidate_manifest.py`:
  80 lines
- `apps/cli/production_memory_operator_command.py`: 224 lines
- `apps/web/memory-workbench-production-operator-loop.js`: 228 lines
- `apps/web/memory-workbench-production-inspector-facts.js`: 232 lines

## Remaining Risks

- Browser-level verification was not run; this slice used static Web tests.
- Optional provider validation was not attempted or required.
- CLI smoke uses synthetic local acceptance feedback input for verification; it
  is not a new human acceptance, business validation, or durable memory
  promotion.
- Machine verification is not human acceptance or business validation.
