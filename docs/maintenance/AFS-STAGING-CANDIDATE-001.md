# AFS-STAGING-CANDIDATE-001 - Pre-Staging Candidate Ledger

Status: current dirty checkout classified before any staging.

This ledger is a staging and cleanup guide only. It does not stage, commit,
delete, merge, or approve any lane.

No remote provider calls were made for this pass. Structure verification,
runtime verification, human acceptance, business validation, provider smoke,
and durable memory promotion remain separate.

## Rule Hierarchy Applied

This classification uses the active project hierarchy:

```text
10-Startup source knowledge base
  -> global workflow skills
  -> project AGENTS.md
  -> docs/company_operating_model.md
  -> TASK_TRACKER.md / branch handoff
  -> current task
```

Operational consequences:

- `D:\Learning materials\Learning_notes\10-Startup` remains the company
  source-of-truth knowledge base.
- This repository should stage only execution-facing AFS projection material.
- Private company strategy, provider secrets, local secret file contents,
  private retrospectives, real costs, customer details, and unpublished
  business assumptions must stay out of Git.
- AFS repo-layer boundaries stay intact: `agentflow/` for platform
  contracts/harness/router/memory/skills, `agentflow_production/` for production-side
  structured handoff, and `agentflow_studio/` for distribution-side packaging/review.

## Current Worktree Snapshot

Observed on 2026-05-31:

- Modified tracked files: 51.
- Untracked files: 120.
- Ignored local runtime/maintenance roots visible under `data/processed/`.
- Root `DEVLOG.md`: 182 lines after compression.
- `docs/archive/devlog_history_2026_05.md`: 200 lines.
- `docs/maintenance/AFS-SLIMMING-BOUNDARY-001.md`: 126 lines before this
  ledger update.

Top-level untracked distribution:

| Top level | Count | Meaning |
|---|---:|---|
| `apps/` | 38 | CLI split, Web workbench, and Web slimming modules |
| `tests/` | 26 | focused tests for memory pipeline, Web, and provider/operator paths |
| `docs/` | 25 | archive, maintenance, handoff, workbench, retrospective, and task brief docs |
| `agentflow_studio/` | 18 | numbered demo evidence modules, provider/operator code, and workflow helper |
| `agentflow/` | 6 | memory video pipeline implementation |
| `examples/` | 6 | sanitized AgentFlow example artifacts |
| `tools/` | 1 | RECORDING-016 operator script |

## Stage Candidate Groups

| Group | Files / directories | Stage posture | Gate |
|---|---|---|---|
| Maintenance control | `DEVLOG.md`, `TASK_TRACKER.md`, `docs/archive/devlog_history_2026_05.md`, `docs/archive/task_history_2026_05.md`, `docs/maintenance/` | stage together as the current cleanup ledger | docs test, CLI help, `git diff --check`, no ignored artifact staging |
| Company workflow projection | `AGENTS.md`, `docs/company_operating_model.md`, `docs/agent_operating_roster.md`, `docs/agent_task_brief_template.md`, `docs/task_briefs/README.md` | stage with maintenance if still aligned with Company source projection | confirm no private Company strategy or secrets copied |
| AgentFlow contracts/examples | `agentflow/contracts/examples.py`, `agentflow/memory/promotion.py`, `examples/agentflow/*.json`, contract tests | stage as platform contract and Memory evidence infrastructure | contract/example tests and no-secret scan |
| Memory video pipeline mainline | `agentflow/memory/video_pipeline*.py`, `apps/cli/memory_video_pipeline_command.py`, `apps/cli/memory_review_command.py`, `examples/agentflow/memory_video_pipeline_*.json`, `tests/test_memory_video_pipeline_*.py`, `tests/test_memory_review_cli.py` | mainline keep; stage as product-facing replacement for numbered demos | visible CLI remains `memory-video-pipeline-*`; focused memory pipeline tests |
| Web Memory Workbench | `apps/web/memory-workbench*`, `apps/web/app-shell-*`, `apps/web/app-workspace-render.js`, `apps/web/production-*`, split CSS files, `docs/workbench/`, Web static tests | mainline keep; stage as local read-only operator UI | Web static tests and browser/static verification if UI is changed again |
| Workflow-engine slimming | `agentflow_studio/workflow_engine/*.py`, `tests/test_*workflow*.py` | stage as architecture slimming | focused workflow tests and full suite before integration |
| Evidence docs and runbooks | `docs/handoff/AFS-MEMORY-ADVANTAGE-DEMO-012.md` through `RECORDING-016`, competition run sheet/talk track, Local Alpha reconciliation docs | preserve evidence; stage as docs/runbooks only | claim-boundary review; no generated media |

## Quarantine Before Staging

These files are useful but should not be staged with the mainline product group
without a dedicated review or refactor.

| Area | Files | Reason | Required action |
|---|---|---|---|
| Provider/operator CLI | `apps/cli/kling_*`, `apps/cli/minimax_image_command.py`, `apps/cli/memory_demo_commands.py` | hidden legacy/operator surface; not default product surface | reviewed in `AFS-PROVIDER-OPERATOR-STAGING-REVIEW-001`; stage only as separate support slice |
| Provider config bridge | `agentflow_studio/model_gateway/company_secrets.py` and imports | hardcoded local Company `.secrets` default removed; provider config now requires explicit `--provider-config` or `AFS_PROVIDER_CONFIG` | reviewed; keep separate from mainline staging |
| Provider runtime adapters | `agentflow_studio/model_gateway/kling_*`, `agentflow_studio/model_gateway/minimax_image_*`, `agentflow_production/posterflow/minimax_provider.py` | useful gated provider clients, but tied to live-call policy | reviewed with no-secret scan, mocked tests, and capability gate checks; stage only separately |
| Numbered demo runtime modules | `agentflow_studio/memory_advantage_demo_012*.py`, `agentflow_studio/memory_advantage_demo_015*.py`, shared DEMO-011 content | evidence/operator path only; protocol path should replace it | do not delete yet; stage only if preserving runnable evidence is intentional |
| RECORDING-016 script | `tools/run_memory_advantage_recording_016.ps1` | useful operator script but can trigger live video if explicitly allowed | now requires both explicit video gate and explicit provider config; keep as operator evidence only |

## Local-Only / Never Stage

- Ignored runtime artifacts under `data/processed/alpha_evidence_inputs/`,
  `data/processed/local_alpha_0_4/`, `data/processed/poster_runs/`,
  `data/processed/product_acceptance_phase14_1/`, and
  `data/processed/runs/`.
- Ignored Web screenshots under `data/processed/workbench-*.png`.
- Ignored maintenance backups under `data/processed/maintenance_backups/`,
  including the full pre-slimming `DEVLOG.md` backup.
- Python bytecode caches. Current source/test recount after cleanup is 0.

## No-Secret Review Notes

The sanitized scan for changed and untracked text files reported pattern hits
for placeholder terms such as `Bearer`, `secret_key`, `api_key`, and signed URL
policy wording. It did not print line contents.

Interpretation for staging:

- Mainline memory pipeline files intentionally reject or sanitize bearer
  headers, signed URLs, and secret-like data.
- Provider tests intentionally use fake keys and mocked provider responses.
- `company_secrets.py` no longer hardcodes the local Company `.secrets` path as
  a default. Provider/operator files still need separate staging review because
  they remain hidden, gated live-call tooling.

## Recommended Staging Order

1. Use `docs/maintenance/AFS-MAINLINE-STAGING-BUNDLE-001.md` as the current
   bundle manifest.
2. Keep product mainline and reviewed support/evidence as explicit layers.
   Product registrations now live in `apps/cli/command_registry.py`; hidden
   provider/demo registrations live in `apps/cli/support_command_registry.py`.
3. Run `python -B tools/staging_preflight.py --repo-root .` before staging to
  catch local-only paths, effective line-count regressions, and hardcoded
   10-Startup `.secrets` paths.
4. Keep provider direct commands and numbered demo runtime out of the default
   product surface even if they are staged as reviewed hidden support.
5. Keep generated runtime artifacts, provider configs, local media, caches, and
   Company source knowledge out of Git.

## Verification Commands

Use this minimum set before staging from this ledger:

```powershell
python -B -m apps.cli.main --help
python -B tools/staging_preflight.py --repo-root .
python -B -m pytest tests/test_agentflow_roadmap_docs.py tests/test_memory_video_pipeline_workflow.py tests/test_memory_advantage_demo_012.py tests/test_memory_advantage_demo_015.py tests/test_minimax_image_smoke.py tests/test_kling_video_smoke.py -q
python -B -m pytest --assert=plain tests/test_kling_video_request_plan.py tests/test_kling_video_smoke.py tests/test_kling_video_t2v_smoke.py tests/test_kling_video_curl_smoke.py tests/test_kling_video_task_recovery.py tests/test_minimax_image_smoke.py -q
git diff --check
git status --ignored --short
```

## Verification For This Pass

- `python -B -m apps.cli.main --help` -> passed; default CLI remains centered
  on `memory-video-pipeline-*`, `memory-evidence-reuse-review`, and
  `web-bridge`.
- `python -B tools/staging_preflight.py --repo-root .` -> passed for the
  current dirty tree.
- `python -B -m pytest tests/test_agentflow_roadmap_docs.py tests/test_memory_video_pipeline_workflow.py tests/test_memory_advantage_demo_012.py tests/test_memory_advantage_demo_015.py tests/test_minimax_image_smoke.py tests/test_kling_video_smoke.py -q`
  -> 48 passed.
- `git diff --check` -> no whitespace errors; CRLF normalization warnings only.
- Source/test `__pycache__` recount under cleanup roots -> 0 remaining.
- `git status --short --ignored data/processed` shows ignored local runtime,
  screenshot, and maintenance backup roots; these remain local-only.

## Provider Config Bridge Update - 2026-05-31

- Removed the hardcoded local 10-Startup `.secrets` provider-config default from
  `agentflow_studio/model_gateway/company_secrets.py`.
- `load_company_provider_secrets()` now resolves an explicit path first, then
  `AFS_PROVIDER_CONFIG`; if neither is present, it fails with a
  configuration error instead of falling back to a machine-local path.
- Hidden provider/operator CLI commands now default `--provider-config` to
  `None` and describe the environment-variable fallback in command help.
- Added tests for missing config path, env-var config loading, and hidden
  Kling/MiniMax CLI help text showing the env fallback.
- Verification:
  - `.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests/test_kling_video_request_plan.py tests/test_kling_video_smoke.py tests/test_kling_video_t2v_smoke.py tests/test_kling_video_curl_smoke.py tests/test_kling_video_task_recovery.py tests/test_minimax_image_smoke.py -q`
    -> 29 passed.
  - Default CLI help and hidden Kling/MiniMax provider help passed without
    surfacing direct provider commands in default help.
  - Hardcoded local Company `.secrets` provider path scan -> no matches.
