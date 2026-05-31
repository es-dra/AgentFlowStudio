# AFS-LOULAN-API-CONTEXT-001 - Loulan API Context Projection Input

## Task

Let `loulan-api-workbench-plan` optionally consume a Loulan context bundle
projection produced from explicit human decisions.

## Goal

Connect the Loulan memory loop:

```text
human review pack
-> explicit decisions
-> context bundle projection
-> API workbench request preview
```

If a projection is supplied, the API workbench must use its human-approved
`context_bundle.memory_refs` and must not fall back to package-level eligible
refs when the projection is blocked.

## Non-goals

- Do not call image or video providers.
- Do not infer approval from review drafts, templates, or package status.
- Do not restructure `D:\Projects\LoulanSceneAssets`.
- Do not persist provider secrets, generated media, response URLs, or Company
  memory.
- Do not implement a live provider adapter or database-backed Memory runtime.

## Owner Role

Provider Adapter Agent + Memory / Evidence Steward + Web UI Agent

## Task Difficulty / Dispatch Mode

```text
Mode: Deep
Why this mode: Crosses memory decision projection, provider request preview,
CLI, contracts, Web inspector, and task records.
Subagent needed: no
Close condition: focused/full verification passes and handoff is recorded.
```

## Branch / Worktree

```text
Branch: codex/loulan-memory-pilot
Worktree: D:\Projects\AgentFlowStudio
Base branch: origin/master
```

## Write Scope

- `agentflow/memory/`
- `apps/cli/`
- `apps/web/`
- `examples/agentflow/`
- `tests/test_loulan_api_workbench.py`
- `docs/loulan_api_workbench_contract.md`
- `TASK_TRACKER.md`, `DEVLOG.md`, and handoff docs

## Do Not Touch

- `D:\Projects\LoulanSceneAssets`
- Company source knowledge base
- provider config, secrets, local `.env`, `.dev.vars`, or model config
- generated media and ignored runtime artifacts except explicit local test output

## Input Docs

- `AGENTS.md`
- `docs/company_operating_model.md`
- `TASK_TRACKER.md`
- `docs/loulan_api_workbench_contract.md`
- `docs/loulan_context_bundle_contract.md`

## Acceptance Criteria

- [x] API workbench accepts optional `context_projection` in code and CLI.
- [x] Ready or partial-ready context projections select references from
      `context_bundle.memory_refs`.
- [x] Blocked projections keep the request manifest blocked and do not fall
      back to package-level eligible refs.
- [x] Reference pack entries keep sha256-only references and no local paths.
- [x] Web inspector surfaces the API plan context projection status.
- [x] No provider call, secret persistence, generated media commit, durable
      memory write, human acceptance claim, or business validation claim.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_api_workbench.py -q
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_api_workbench.py tests\test_loulan_context_bundle.py tests\test_web_memory_loulan_package_static.py tests\test_web_memory_loulan_decision_context_static.py tests\test_contract_examples.py tests\test_agentflow_contract_audit.py -q
.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-api-workbench-plan --help
.\.venv\Scripts\python.exe -B -m apps.cli.main --help
.\.venv\Scripts\python.exe -B -m apps.cli.main version
.\.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
git diff --check
```

## Expected Artifacts

- Updated API workbench plan JSON/report shape.
- Updated CLI help with `--context-projection`.
- Handoff record under `docs/handoff/`.

## Remote Provider Policy

- [x] No remote provider needed.
- [ ] Remote LLM needed. Requires `NARRATOCUT_ALLOW_REMOTE_LLM=true`.
- [ ] Remote ASR needed. Requires `NARRATOCUT_ALLOW_REMOTE_ASR=true`.
- [ ] Remote image needed. Requires `NARRATOCUT_ALLOW_REMOTE_IMAGE=true`.
- [ ] Remote video generation needed. Requires an explicit task-specific gate.
- [ ] External download needed. Requires explicit source and artifact policy.

Secrets, keys, signed URLs, cookies, and private credentials must stay local and
must not be committed.

## Evidence Path

```text
docs/handoff/AFS-LOULAN-API-CONTEXT-001.md
```

## Integration Order

This follows the Loulan decision template, context bundle projection, and Web
context rendering slices. It does not replace the human review lane.

## Return Format

Record changed files, verification commands, evidence paths, residual risks,
and next-node recommendation in the handoff.
