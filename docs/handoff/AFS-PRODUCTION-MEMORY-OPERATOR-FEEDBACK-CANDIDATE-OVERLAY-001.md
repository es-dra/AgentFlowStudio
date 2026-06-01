# AFS-PRODUCTION-MEMORY-OPERATOR-FEEDBACK-CANDIDATE-OVERLAY-001

Status: verified locally on
`codex/afs-production-memory-operator-feedback-candidate-overlay-001`.

## Scope

Derive a no-provider follow-up context bundle from an explicit operator
feedback candidate decision.

This closes the backend step after
`AFS-PRODUCTION-MEMORY-OPERATOR-FEEDBACK-CANDIDATE-PROMOTION-001`: candidate
packet plus explicit decision can now be converted into a derived
production-memory loop and auditable context overlay.

## Implementation Files

- `agentflow/memory/production_operator_feedback_candidate_overlay.py`
- `apps/cli/production_memory_operator_feedback_candidate_overlay_command.py`
- `apps/cli/command_registry.py`
- `tests/test_production_memory_operator_feedback_candidate_overlay.py`

## CLI

```powershell
python -m apps.cli.main production-memory-loop-run-operator-feedback-candidate-reviewed-no-provider examples/agentflow/production_memory_loop.example.json --candidate-packet data/processed/runs/production_memory_loop/operator_feedback_candidate/operator_feedback_candidate_packet.json --promotion-decision data/processed/runs/production_memory_loop/operator_feedback_candidate_promotion/operator_feedback_candidate_promotion_decision.json --output data/processed/runs/production_memory_loop/operator_feedback_candidate_reviewed
```

The command writes:

- `derived_production_memory_loop.json`
- `production_memory_loop_run.json`
- `context_bundle.json`
- `pass_readiness.json`
- `next_pass_bundle.json`
- `operator_feedback_candidate_promotion_overlay.json`

## Contract Boundaries

- pending promotion templates cannot drive the overlay.
- explicit decision `source_packet_id`, `source_feedback_event_id`, source
  pending template id, and candidate id must match the candidate packet.
- promoted and merged decisions can include the candidate in context.
- rejected, expired, and blocked decisions keep the candidate in blocked refs.
- the operator-node target is recorded as evidence only and is not eligible
  for next context by itself.
- `provider_calls_started: false`
- `writes_long_term_memory: false`
- `writes_company_kb: false`
- no next-pass execution
- no Web behavior
- no Loulan-specific behavior
- no human acceptance or business validation claim

## Verification

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_operator_feedback_candidate_overlay.py -q
```

Initial red result: CLI invocation failed because
`production-memory-loop-run-operator-feedback-candidate-reviewed-no-provider`
was not registered.

Green result after implementation: `5 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m py_compile agentflow/memory/production_operator_feedback_candidate_overlay.py apps/cli/production_memory_operator_feedback_candidate_overlay_command.py apps/cli/command_registry.py
```

Result: passed.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_operator_feedback_candidate_overlay.py tests/test_production_memory_operator_feedback_candidate_promotion.py tests/test_production_memory_operator_feedback_candidate.py tests/test_production_memory_operator_feedback.py tests/test_production_memory_operator_loop.py tests/test_production_memory_operator_loop_promotion.py tests/test_production_memory_next_pass_promotion.py tests/test_contract_examples.py tests/test_cli_command_registry_boundaries.py -q
```

Result: `59 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main --help
```

Result: passed; the new
`production-memory-loop-run-operator-feedback-candidate-reviewed-no-provider`
command is registered.

CLI smoke generated an ignored operator-loop manifest, captured evidence-only
operator feedback, drafted a candidate-only packet, wrote an explicit promoted
decision, then generated a reviewed context overlay under:

```text
data/processed/runs/production_memory_loop/operator_feedback_candidate_overlay_smoke/
```

The reviewed run reported:

- status: ready
- decision effect: `included_in_context`
- included refs: 4
- blocked refs: 3

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest
```

Result: `773 passed` on Python 3.12.12.

```powershell
git diff --check
```

Result: exit 0; CRLF normalization warnings only.

Added-diff and new-file sensitive scan produced no hits for Company source path
copies, configured credential markers, key shapes, customer markers, cookies,
or signed-link markers.

Code file line counts remain under the 300-line target:

- `agentflow/memory/production_operator_feedback_candidate_overlay.py`: 260
  lines
- `apps/cli/production_memory_operator_feedback_candidate_overlay_command.py`:
  84 lines
- `apps/cli/command_registry.py`: 169 lines
- `tests/test_production_memory_operator_feedback_candidate_overlay.py`: 162
  lines

## Remaining Risks

- This slice is backend-only. Web rendering for
  `agentflow_production_memory_operator_feedback_candidate_promotion_overlay`
  remains a follow-up.
- The operator-loop command does not yet embed this reviewed overlay in its
  manifest.
- No provider validation was attempted or required.
- Machine verification is not human acceptance or business validation.
