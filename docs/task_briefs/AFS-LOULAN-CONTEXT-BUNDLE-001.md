# AFS-LOULAN-CONTEXT-BUNDLE-001 - Loulan Context Bundle Projection

## Task

Project explicit Loulan human decision records into a no-call next context
bundle draft.

## Goal

Provide the protocol step after human review:

```text
human review pack
-> explicit human decisions
-> decision audit
-> context bundle
-> next prompt draft
```

## Non-goals

- Do not infer approval from review-pack drafts.
- Do not create artificial human decisions.
- Do not call providers or read provider config.
- Do not write Company knowledge or durable Memory runtime.
- Do not claim product acceptance or business validation.

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
- focused contract and CLI tests
- tracker, DEVLOG, and handoff docs

## Acceptance Criteria

- [x] `agentflow_loulan_context_bundle_projection` contract example is
      committed.
- [x] CLI consumes `agentflow_loulan_human_review_pack` and explicit
      `agentflow_loulan_promotion_decisions`.
- [x] Missing decisions block context projection.
- [x] `approve_anchor`, `request_repair`, `promoted`, `merged`, `rejected`,
      and `expired` decisions map to ready or blocked refs without durable
      memory writes.
- [x] Real local B01 smoke uses an empty decision file and remains blocked
      rather than inventing approval.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_context_bundle.py -q
.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-context-bundle --review-pack data\processed\runs\loulan_human_review_pack\local_probe\loulan_human_review_pack.json --decisions data\processed\runs\loulan_context_bundle\local_probe\loulan_decisions.empty.json --created-at "2026-06-01T12:00:00+08:00" --output data\processed\runs\loulan_context_bundle\local_probe
```

## Remote Provider Policy

No remote provider is authorized in this task.

## Evidence Path

```text
docs/handoff/AFS-LOULAN-CONTEXT-BUNDLE-001.md
```
