# AFS-LOULAN-DECISION-TEMPLATE-001 - Loulan Decision Template

## Task

Generate a fillable Loulan human decision template from the B01 human review
pack without approving, promoting, or writing memory.

## Goal

Provide the missing protocol step between review-pack preparation and context
bundle projection:

```text
human review pack
-> pending decision template
-> filled human decisions
-> context bundle projection
```

## Non-goals

- Do not infer approval from review-pack drafts.
- Do not create artificial human decisions.
- Do not call image, video, ASR, LLM, or external download providers.
- Do not write Company knowledge or durable Memory runtime.
- Do not claim human acceptance, product acceptance, or business validation.

## Owner Role

Memory / Evidence Steward + Workflow Engineer + QA Reviewer

## Branch

```text
codex/loulan-memory-pilot
```

## Write Scope

- `agentflow/memory/`
- `apps/cli/`
- `examples/agentflow/`
- `docs/`
- focused contract, CLI, and context tests
- tracker, DEVLOG, and handoff docs

## Acceptance Criteria

- [x] Template artifact type is `agentflow_loulan_promotion_decisions`.
- [x] Every generated decision starts as `pending_human_review`.
- [x] Template records no human acceptance, provider calls, or durable memory
      write.
- [x] CLI writes JSON and Markdown template artifacts.
- [x] Passing the unfilled template into `loulan-context-bundle` blocks with
      `blocked_invalid_decisions`.
- [x] Contract example, registry entry, audit report, and docs are registered.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_decision_template.py -q
.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-decision-template --review-pack data\processed\runs\loulan_human_review_pack\local_probe\loulan_human_review_pack.json --created-at "2026-06-01T12:30:00+08:00" --output data\processed\runs\loulan_decision_template\local_probe
.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-context-bundle --review-pack data\processed\runs\loulan_human_review_pack\local_probe\loulan_human_review_pack.json --decisions data\processed\runs\loulan_decision_template\local_probe\loulan_decisions.template.json --created-at "2026-06-01T12:45:00+08:00" --output data\processed\runs\loulan_context_bundle\template_probe
```

## Remote Provider Policy

No remote provider is authorized in this task.

## Evidence Path

```text
docs/handoff/AFS-LOULAN-DECISION-TEMPLATE-001.md
```
