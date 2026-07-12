# AgentFlow Studio Agent Instructions

## Mission

AgentFlow Studio is an Agent-native production operating layer for AI content
production. The current product surface is the Studio canvas at `/studio/`,
backed by the Runtime Service and provider-gated generation paths.

Current scope is local internal testing and hardening. Repository changes must
not be described as SaaS readiness, public release readiness, provider QA,
generated-media QA, human acceptance, business validation, legal readiness, or
durable Company OS promotion.

## Rule Order

Read rules in this order when they conflict:

```text
D:\Learning materials\Learning_notes\10-Startup
  -> project-development-workflow skill
  -> AGENTS.md
  -> docs/AOS_CURRENT_STATE.md
  -> docs/README.md
  -> current task
```

The `10-Startup` tree is the source knowledge base. This repository is only an
execution projection: code, tests, contracts, safe docs, and current project
state needed to work on AFS.

## Startup

When entering, resuming, scanning, debugging, or editing this repository:

1. Use the `project-development-workflow` skill first.
2. Run a startup scan before changing files.
3. Read `docs/AOS_CURRENT_STATE.md` and `docs/README.md`.
4. Read `docs/company_operating_model.md` or `docs/GFR_EXECUTION_PROJECTION.md`
   only when the task touches operating rules, AOS/GFR projection, cleanup, or
   cross-surface state.
5. Define the write scope, forbidden scope, verification route, provider/tool
   gates, non-claims, and closeout shape before substantial edits.

Do not read old full trackers, handoff directories, smoke logs, or retired
Workbench material as startup context. Historical records are recoverable from
Git history or a targeted restored reference when a task has a specific ID,
file path, branch name, PR number, or keyword.

## AOS Task Shape

For substantial work, internally apply an AOS Startup Packet:

```text
Goal Contract
Task Packet
Evidence target
Runtime Surface Vector when local/GitHub/server/process/provider state can drift
Integration Queue route
Improvement Queue route
```

Minimum fields:

```text
target outcome
read scope
write scope
forbidden scope
provider/tool gates
verification route
non-claims
stop conditions
closeout shape
```

## Scale-Up Mode

The default control plane is one accountable main thread, but substantial work
does not have to stay single-lane. Use Deep or Program mode when the task spans
multiple product surfaces, runtime state, provider gates, broad cleanup, or
research/evaluation.

Scale-up rules:

- Keep one main control thread responsible for scope, evidence, integration,
  and closeout.
- Add temporary worker or evaluator lanes only with a bounded lane contract:
  target, read/write scope, forbidden scope, evidence target, verification
  command, stop condition, and return route.
- Do not recreate permanent CEO/CTO/CPO/COO/PM threads.
- Do not use heartbeat as status reporting. A control tick must advance,
  integrate, evaluate, retire, unblock, or record a concrete no-op reason.
- For user-facing Studio, Runtime Service, provider, release, cleanup with
  deletion risk, or quality-claim work, add an evaluator gate before closeout.
- For multi-surface work, maintain a compact integration queue instead of
  creating new long-running ledgers.
- For release or runtime work, use a separate Release Lane. Updating `/opt` or
  another deploy checkout is not enough: the managed process must be restarted
  or reloaded through its service manager, and a fresh runtime health/process
  check must prove that the target commit is loaded.

If the working tree already contains a broad uncommitted cleanup, either finish
and integrate that cleanup first or isolate the new task in a fresh worktree.
Do not bury product/runtime changes inside a huge governance cleanup diff
unless the task explicitly authorizes that tradeoff.

## Worktree And Branches

- Use `codex/*` for new branches unless instructed otherwise.
- Prefer an isolated worktree for substantial multi-file, provider, Runtime
  Service, Web, architecture, or cleanup work.
- Do not use `git reset --hard` or destructive checkout commands unless the
  user explicitly requests them.
- Preserve unrelated dirty changes. If another change affects the task, work
  with it instead of reverting it.

## Provider Gates

Remote provider capabilities are closed by default and must be authorized by
capability:

| Capability | Default | Gate |
|---|---|---|
| LLM | closed | `AFS_ALLOW_REMOTE_LLM=true` |
| ASR | closed | `AFS_ALLOW_REMOTE_ASR=true` |
| image | closed | `AFS_ALLOW_REMOTE_IMAGE=true` |
| video | closed | task-level explicit authorization or a future separate gate |
| external download | closed | task-level source, purpose, storage, and cleanup policy |

Image authorization does not authorize video, LLM, ASR, or external downloads.

## Engineering Boundaries

- Prefer schema-first and contract-first changes.
- Build deterministic harnesses before provider paths.
- Treat runtime verification, provider smoke, human acceptance, business
  validation, and durable memory promotion as different evidence levels.
- Feedback and candidate memory are evidence, not automatic durable memory.
- Runtime success does not prove human acceptance or business validation.
- Provider smoke does not prove generated-media QA.

## Frontend / Runtime Boundary

The frontend talks to the Runtime Service boundary, not CLI internals.

Frontend-safe values include:

- `project_id`
- `job_id`
- `artifact_id`
- safe summaries
- safe manifests
- OpenAPI fields

Frontend code must not receive provider secrets, local absolute private asset
paths, signed URLs, generated media bytes, or internal orchestration details.

## Documentation Maintenance

Keep the active documentation surface small and current:

- `docs/AOS_CURRENT_STATE.md` is the compact startup surface.
- `docs/README.md` is the documentation entrypoint.
- `docs/company_operating_model.md` and `docs/GFR_EXECUTION_PROJECTION.md` are
  AOS/GFR projections, not source rules.
- Current architecture and contract documents belong under `docs/architecture/`
  or focused root docs.

Long historical ledgers and handoff archives are not active state. Delete them
from the working tree when replacement contracts or Git history are sufficient.
Do not keep noisy documents merely because they once supported a loop.

Do not resurrect `DEVLOG.md`, `TASK_TRACKER.md`, `docs/handoff/INDEX.md`, or a
retired handoff archive to satisfy a worker habit or resolve a rebase conflict.
Use the PR body, thread closeout, and focused current state/program documents
unless a task-specific audit reason proves a durable repo record is required.

## Verification

Choose verification by blast radius. Common commands:

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main --help
.\.venv\Scripts\python.exe -m apps.cli.main version
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe tools\maintenance_audit.py
git diff --check
```

For release/runtime freshness claims, also verify:

```powershell
git -C <deploy-checkout> rev-parse HEAD
systemctl status <service> --no-pager
ss -ltnp | Select-String "8790|8791|8792"
curl -fsS http://127.0.0.1:8790/health
```

If service restart requires an unavailable sudo or service-manager capability,
record `deploy_dir_updated` plus `runtime_stale`; do not claim delivery and do
not bypass systemd by killing the process unless the task explicitly authorizes
that emergency route.

For COS/GFR projection work, also use the current `10-Startup` audit:

```powershell
python "D:\Learning materials\Learning_notes\10-Startup\80-Workflow\ai-native-company-workflow\tools\gfr_audit.py" --root "D:\Learning materials\Learning_notes\10-Startup" --pack-index "D:\Learning materials\Learning_notes\10-Startup\00-Company-OS\context-pack-index.json"
```

## Records

Update project records only when the update creates reusable current state,
verification evidence, integration decisions, or handoff value. Prefer one
focused current surface over multiple governance artifacts. Do not write
secrets, provider raw responses, signed URLs, private strategy, real customer
data, real costs, or unpublished commercial judgments into this repository.

Experience that should feed back to Company OS must enter the `10-Startup`
candidate/limited flow. Agents cannot promote repo observations into active
Company OS rules on their own.
