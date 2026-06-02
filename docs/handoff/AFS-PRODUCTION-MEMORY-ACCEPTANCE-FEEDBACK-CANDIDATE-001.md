# AFS-PRODUCTION-MEMORY-ACCEPTANCE-FEEDBACK-CANDIDATE-001

Status: verified locally on
`codex/afs-production-memory-acceptance-feedback-candidate-001`.

## Scope

This slice drafts a candidate-only memory review packet from one explicit
`acceptance_feedback_event.json`.

Added command:

```powershell
python -m apps.cli.main production-memory-loop-draft-acceptance-feedback-candidate data/processed/runs/production_memory_loop/acceptance_feedback/acceptance_feedback_event.json --generated-at 2026-06-03T01:10:00+08:00 --output data/processed/runs/production_memory_loop/acceptance_feedback_candidate
```

The command writes:

- `acceptance_feedback_candidate_packet.json`
- `memory_candidate.json`
- `promotion_decision_template.json`
- `acceptance_feedback_candidate_packet.md`

## Contract

- Artifact kind:
  `agentflow_production_memory_acceptance_feedback_candidate_packet`.
- The source event must be
  `agentflow_production_memory_acceptance_feedback_event` with
  `status=human_recorded`.
- Accepted source feedback drafts a memory candidate with `status=candidate`.
- Rejected or needs-revision source feedback drafts a memory candidate with
  `status=blocked`.
- The promotion decision template is always `pending` and `template_only`.
- A pending template cannot enter next context as a reviewed promotion
  decision.
- The packet carries the source human acceptance decision as evidence. It is
  not a new human acceptance event and not business validation.

## Web

The read-only Web workbench now recognizes selected
`acceptance_feedback_candidate_packet.json` files and renders:

- source acceptance decision;
- memory candidate status;
- pending promotion template;
- business-validation boundary;
- memory and Company KB write boundaries;
- no-provider controls.

The Web slice is selected-file only. It does not scan directories, persist
browser state, execute workflows, call providers, follow refs, or add
project-specific inspector behavior.

## Verification

- Red test failed first because the candidate module did not exist.
- Web red test then failed because the packet source role/view was not wired.
- `data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_production_memory_acceptance_feedback_candidate.py -q`
  passed (`6 passed`).
- `data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests\test_web_static_production_memory_acceptance_feedback_candidate.py -q`
  passed (`2 passed`).
- Py compile for touched Python files passed.
- JS import smoke for the new Web module, controller, and workspace passed.
- Focused acceptance/Web/contract regression passed (`40 passed`).
- CLI help for `production-memory-loop-draft-acceptance-feedback-candidate`
  passed.
- CLI smoke wrote ignored candidate packet, memory candidate, pending promotion
  template, and Markdown report.
- Full suite passed on Python 3.12.12 (`841 passed`).
- `git diff --check` passed with CRLF normalization warnings only.

## Line Counts

Initial checked line counts:

- `agentflow/memory/production_acceptance_feedback_candidate.py`: 197.
- `apps/cli/production_memory_acceptance_feedback_candidate_command.py`: 45.
- `apps/web/memory-workbench-production-acceptance-feedback-candidate.js`: 125.
- `tests/test_production_memory_acceptance_feedback_candidate.py`: 122.
- `tests/test_web_static_production_memory_acceptance_feedback_candidate.py`: 127.
- `apps/web/artifact-workspace.js`: 284.

## Remaining Risks

- This is only a candidate bridge. A later explicit promotion-decision command
  is still required before any acceptance-derived memory candidate can affect a
  future context bundle.
- This is not business validation and does not write Company KB.
- Browser-level smoke is separate from static Web tests and should not be
  described as human acceptance.
