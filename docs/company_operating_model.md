# AFS AOS Operating Projection

This file is the AgentFlow Studio execution projection of the Company OS /
AOS source rules. It is not a source rule file and does not replace the
`10-Startup` knowledge base.

Source knowledge base:

```text
D:\Learning materials\Learning_notes\10-Startup
```

## Layer Responsibilities

| Layer | Responsibility |
|---|---|
| `10-Startup` | Company source rules, strategy, governance, candidate memory, and private judgment. |
| `project-development-workflow` | Runtime adapter that turns source rules into executable project workflow. |
| AFS repository | Code, tests, contracts, safe docs, current state, and project-local verification. |
| Branch/worktree | Actual implementation surface for a bounded task. |
| Agent | Executes a scoped task; cannot promote Company OS rules or business claims. |

## Startup Reading

Default AFS startup reads should stay compact:

```text
AGENTS.md
docs/AOS_CURRENT_STATE.md
docs/README.md
```

Add this file, `docs/GFR_EXECUTION_PROJECTION.md`, and specific architecture
contracts only when the task needs them. Historical records should be found by
targeted Git/history search, not by loading long active ledgers.

## Task Modes

| Mode | Use | Execution form |
|---|---|---|
| Light | Read-only scan or narrow single-file fix. | Current checkout is acceptable. |
| Standard | Normal feature, local bug, CLI/schema/doc update. | One bounded lane; worktree if useful. |
| Deep | Multi-module, Runtime Service, Web, provider, architecture, or cleanup work. | One main control thread plus bounded worker/evaluator lanes when needed. |
| Program | Multiple related lanes, product + runtime + cleanup, release preparation, or broad architecture migration. | Main control owns an integration queue, lane contracts, evaluator gates, and explicit stop conditions. |
| Strategic | Company rules, product direction, business validation, or memory promotion. | Prepare evidence/candidate only; human decision required. |

## Lane Policy

AFS should grow beyond narrow single-thread tasks by scaling the task structure,
not by restoring permanent role threads.

Allowed expansion:

- one accountable main control thread;
- temporary worker lanes with bounded scope and verification commands;
- temporary evaluator lanes for product flow, runtime, provider, cleanup
  deletion risk, or quality claims;
- one compact integration queue that records merge, defer, retire, verify, or
  escalate decisions.

Required lane contract:

```text
target
read scope
write scope
forbidden scope
evidence target
verification route
stop condition
return route
```

Invalid expansion:

- fixed CEO/CTO/CPO/COO/PM control planes;
- status-only heartbeat loops;
- governance documents used as delivery evidence;
- product/runtime edits hidden inside a broad unrelated cleanup diff.

## Current Product Line

AgentFlow Studio is an Agent-native production operating layer for AI content
production. The current active surface is:

```text
/studio/ canvas
  -> Runtime Service
  -> prompt optimization
  -> fixed visual assets
  -> graph context resolver
  -> provider-gated keyframe/image evidence
```

Retired Workbench and memory-workbench paths are not current product entrypoints.

## Runtime And Provider Boundaries

Remote provider capabilities are closed by default. Provider smoke, runtime
verification, generated-media quality, human acceptance, business validation,
and durable memory promotion are separate evidence levels.

Before claiming runtime or deployment state, compile a fresh Runtime Surface
Vector covering local repo, GitHub, server `/opt`, server `/home`, `/test`,
systemd units, listening processes, provider gates, and health/auth state.

## Documentation Maintenance

The active docs surface should carry current architecture, current state,
contracts, and verification routes. Long task trackers, devlogs, and handoff
archives are not active state. Delete them when Git history plus focused
contracts are enough to preserve recoverability.

Keep historical material only when it has one of these roles:

- current architecture or API contract;
- current operational runbook;
- machine-verified fixture or schema;
- specific evidence required by an active test;
- concise current state needed for startup.

Otherwise, remove it from the working tree instead of archiving it again.

## Safe Records

The repository may contain code, tests, schemas, safe manifests, safe summaries,
safe public/semi-public engineering docs, current verification commands, and
non-claim boundaries.

The repository must not contain secrets, tokens, cookies, provider keys, signed
URLs, provider raw responses, generated media bytes, private strategy, real
customer information, real costs, contract originals, or unpublished partner
judgment.

## Verification

Maintenance cleanup entrypoint:

```powershell
.\.venv\Scripts\python.exe tools\maintenance_audit.py
git diff --check
```

GFR projection audit:

```powershell
python "D:\Learning materials\Learning_notes\10-Startup\80-Workflow\ai-native-company-workflow\tools\gfr_audit.py" --root "D:\Learning materials\Learning_notes\10-Startup" --pack-index "D:\Learning materials\Learning_notes\10-Startup\00-Company-OS\context-pack-index.json"
```
