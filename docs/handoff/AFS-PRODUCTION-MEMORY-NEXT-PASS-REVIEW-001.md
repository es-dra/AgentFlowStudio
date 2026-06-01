# AFS-PRODUCTION-MEMORY-NEXT-PASS-REVIEW-001

Status: verified locally on `codex/afs-production-memory-next-pass-review-001`.

## Scope

Add a generic no-provider review/intake node after `next_task_packet`.

The new command is:

```powershell
python -m apps.cli.main production-memory-loop-review-next-pass <next_task_packet.json> <next_pass_result.json> --reviewed-at <iso-timestamp> --output <output-dir>
```

It reads:

- a selected `agentflow_production_memory_next_task_packet`;
- a selected local `agentflow_production_memory_next_pass_result`.

It writes:

- `next_pass_review.json`;
- `next_pass_review.md`.

Implementation files: `agentflow/memory/production_next_pass_review.py`,
`agentflow/memory/production_next_pass_review_render.py`, and
`apps/cli/production_memory_next_pass_review_command.py`.

## Boundaries

- No provider call.
- No next-pass execution.
- No Web scan, browser persistence, or Web-triggered execution.
- No Company KB write.
- No durable memory write.
- No Loulan-specific behavior.
- No human acceptance claim.
- No business validation claim.

## Contract Notes

The review blocks a next-pass result when:

- the source task packet is not ready;
- result provider mode is not `no-provider`;
- result provider calls were started;
- result writes long-term memory or Company KB;
- output artifacts are missing;
- output artifacts use blocked or unknown context refs.

Feedback from the supplied result is converted only into candidate feedback and
pending promotion-decision templates. It is not promoted memory.

## Verification

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_next_pass_review.py -q
```

Result: `5 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_next_pass_review.py tests/test_production_memory_next_task_packet.py tests/test_production_memory_next_context_handoff.py tests/test_production_memory_operator_loop.py tests/test_contract_examples.py tests/test_cli_command_registry_boundaries.py -q
```

Result: `40 passed`.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main --help
```

Result: passed; `production-memory-loop-review-next-pass` is visible.

```powershell
data\processed\venvs\afs-py312\Scripts\python.exe -m pytest
```

Result: `733 passed` on Python 3.12.12.

```powershell
git diff --check
```

Result: exit 0; CRLF normalization warnings only.

## Remaining Risks

- Browser read-only rendering for `agentflow_production_memory_next_pass_review`
  is not part of this slice.
- This does not execute the next AI task; it reviews only explicit result JSON.
- The feedback candidates require a later explicit promotion decision before
  reuse.
- No provider validation was attempted.
