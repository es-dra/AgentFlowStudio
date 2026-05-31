# AFS-MEMORY-PIPELINE-MVP-001 - Protocol-Driven Memory Video Pipeline

## Task

Replace ad hoc numbered demo execution with one protocol-driven memory-backed
video production pipeline.

## Goal

Run a baseline and memory-backed video experiment from a single protocol file:
brief, assets, memory context, provider route, I2I keyframes, I2V clips,
comparison video, review JSON, and feedback-event draft.

## Non-goals

- Do not add durable Memory runtime, database, vector store, hosted service, or
  RAG.
- Do not create another `memory_advantage_demo_XXX` module.
- Do not claim business validation or final human acceptance.
- Do not store provider keys, signed URLs, bearer headers, local media, or
  generated video in Git.
- Do not redesign the Web UI in this lane.

## Owner Role

Memory / Evidence Steward + Workflow Engineer

## Branch / Worktree

```text
Branch: codex/afs-memory-pipeline-mvp
Worktree: C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-memory-pipeline-mvp
Base branch: master after AFS-MAINTENANCE-RESET-001
```

## Write Scope

- `agentflow/memory/`
- `narratocut/model_gateway/` only for provider-adapter reuse, not new gates
- `apps/cli/` for one generic protocol command
- `examples/agentflow/` sanitized protocol examples
- focused tests for protocol parsing, safety, review, and no-call planning
- docs for the protocol contract

## Do Not Touch

- `apps/web/`
- generated evidence under `data/processed/`
- local media under `data/raw/`
- provider configs, `.env`, `.dev.vars`, `configs/models.yaml`
- private Company knowledge base
- historical demo modules except through a cleanup decision from
  `AFS-MAINTENANCE-RESET-001`

## Input Docs

- `AGENTS.md`
- `docs/company_operating_model.md`
- `docs/agentflow_memory_contract.md`
- `docs/retrospectives/memory_architecture_next_loop_2026_05_29.md`
- `docs/handoff/AFS-MEMORY-ADVANTAGE-DEMO-012.md`
- `docs/handoff/AFS-MEMORY-ADVANTAGE-DEMO-015.md`

## Acceptance Criteria

- [x] A sanitized protocol schema defines project brief, source assets, memory
      cards, provider route, generation lanes, review rubric, and claim
      boundary.
- [x] A no-call plan command writes safe protocol/request/review plan artifacts.
- [ ] Optional live execution uses existing image/video gates and never persists
      provider credentials, bearer headers, signed URLs, data URLs, or absolute
      source media paths.
- [x] Baseline and memory-backed lanes share source assets, provider route,
      model, duration, and script; the only intended difference is memory
      context.
- [x] Review output includes cross-run stability fields when repeated runs are
      available.
- [x] Rejected or expired memory cannot enter context.
- [x] Generated media stays ignored.
- [x] A no-call package command links plan, review, observation, presentation,
      and feedback-event draft artifacts.

## Verification Commands

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests/test_agentflow_asset_memory_validator.py tests/test_kling_video_smoke.py tests/test_minimax_image_smoke.py -q
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m compileall agentflow\memory narratocut\model_gateway apps\cli
git diff --check
```

## Expected Artifacts

- Protocol schema or validator.
- Sanitized example protocol.
- Generic CLI command.
- Review JSON contract and focused tests.
- Feedback-event draft contract and no-call package summary.

## Remote Provider Policy

- [ ] No remote provider needed.
- [ ] Remote LLM needed. Requires `NARRATOCUT_ALLOW_REMOTE_LLM=true`.
- [ ] Remote ASR needed. Requires `NARRATOCUT_ALLOW_REMOTE_ASR=true`.
- [ ] Remote image needed. Requires `NARRATOCUT_ALLOW_REMOTE_IMAGE=true`.
- [ ] Remote video generation needed. Requires an explicit task-specific gate.
- [x] Default work is no-call planning. Live image/video execution requires a
      separate user-approved run with the relevant gates enabled.

## Evidence Path

```text
docs/handoff/AFS-MEMORY-PIPELINE-MVP-001.md
```

## Return Format

1. Status: `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`.
2. Changed files.
3. Verification commands and results.
4. Protocol examples and generated no-call artifact paths.
5. Risks and unfinished work.
6. Whether the worktree should be closed, preserved, or continued.
