# AFS-SLIMMING-BOUNDARY-001 - Mainline Slimming Boundary

Status: boundary ledger drafted; first local ignored-cache cleanup applied.

This record classifies the visible product path, evidence to preserve, legacy
operator paths, and removal candidates before more cleanup is applied.

No provider calls were made for this maintenance pass. No generated media,
provider credentials, signed URLs, local model caches, private Company
knowledge-base content, human acceptance, or business validation is promoted by
this record.

## Source Rules

- Company source knowledge base remains outside this repository:
  `D:\Learning materials\Learning_notes\Company`.
- This repository keeps only execution-facing projection for AgentFlow Studio.
- `memory-video-pipeline-*` is the visible product CLI surface.
- Numbered memory-advantage demos and direct provider smoke commands are
  legacy evidence/operator paths, hidden from default help.
- DEMO-012 through RECORDING-016 are evidence worth preserving.
- Structure verification, runtime verification, human acceptance, business
  validation, provider smoke, and durable memory promotion stay separate.

## Current Branch State

```text
Branch: master
Upstream: origin/master
HEAD: fa6ed76
```

The checkout is intentionally dirty and includes multiple workstreams. This
ledger only classifies boundaries; it does not stage, delete, or reset unrelated
work.

## Mainline Product Surface

| Area | Current files | Classification | Boundary |
|---|---|---|---|
| Memory video pipeline contract | `agentflow/memory/video_pipeline*.py`, `apps/cli/memory_video_pipeline_command.py`, `examples/agentflow/memory_video_pipeline_*.example.json`, `tests/test_memory_video_pipeline_*.py`, `docs/handoff/AFS-MEMORY-PIPELINE-MVP-001.md` | mainline keep | This is the replacement path for numbered memory demos. It stays no-call unless a later provider-execution slice adds explicit gates. |
| Visible CLI surface | `memory-video-pipeline-plan`, `memory-video-pipeline-review`, `memory-video-pipeline-observe`, `memory-video-pipeline-present`, `memory-video-pipeline-package`, `memory-evidence-reuse-review` | mainline keep | These commands should remain visible in `--help`; they must not scan directories, call providers, copy generated media, or write durable memory by default. |
| Web Memory Workbench | `apps/web/memory-workbench*.js`, `apps/web/memory-workbench*.css`, `docs/workbench/`, `tests/test_web_memory_*.py` | mainline keep, still static/local | Keep as operator UI for explicit package artifacts. It remains read-only/local, with no provider call, directory scan, browser persistence, artifact writes, or durable Memory runtime. |
| Workflow engine core | `narratocut/workflow_engine/`, `workflows/`, `tests/test_*workflow*.py` | mainline keep | Keep execution order in `workflow_engine`; keep quality gates in `harness`; avoid circular imports. Current files are under the 300-line target after helper slimming. |
| AgentFlow contracts and examples | `agentflow/contracts/`, `examples/agentflow/`, related contract tests | mainline keep | Keep sanitized examples only. Examples must not contain private paths, provider keys, signed URLs, bearer headers, data URLs, or generated media. |

## Evidence To Preserve

| Evidence group | Current files | Classification | Boundary |
|---|---|---|---|
| Local Alpha 0.4 evidence | `docs/handoff/AFS-RUN-PACKAGE-001.md`, `docs/handoff/AFS-WEB-OPERATOR-002.md`, `docs/handoff/AFS-MEMORY-QUALITY-002.md`, `docs/local_alpha_0_4_acceptance_reconciliation.md` | preserve evidence | Structure/runtime/review evidence only. Do not treat as business validation or durable Memory runtime. |
| DEMO-012 | `narratocut/memory_advantage_demo_012*.py`, `tests/test_memory_advantage_demo_012.py`, `docs/handoff/AFS-MEMORY-ADVANTAGE-DEMO-012.md` | preserve evidence, legacy hidden | First credible route pattern: fixed reference -> MiniMax I2I keyframes -> Kling I2V. Keep until the protocol runner covers the same evidence path. |
| DEMO-013 and DEMO-014 | `docs/handoff/AFS-MEMORY-ADVANTAGE-DEMO-013.md`, `docs/handoff/AFS-MEMORY-ADVANTAGE-DEMO-014.md` | preserve as docs-only evidence | Useful comparison history, not product surface. Do not reopen as Python modules. |
| DEMO-015 | `narratocut/memory_advantage_demo_015*.py`, `tests/test_memory_advantage_demo_015.py`, `docs/handoff/AFS-MEMORY-ADVANTAGE-DEMO-015.md` | preserve evidence, legacy hidden | Keep protocol/runtime evidence until generic memory video pipeline live execution and review can replace it. |
| RECORDING-016 | `docs/handoff/AFS-MEMORY-ADVANTAGE-RECORDING-016.md`, `tools/run_memory_advantage_recording_016.ps1`, generated evidence under ignored `data/processed/` | preserve evidence and runbook | Current strongest demo signal. Keep claims bounded to cross-run consistency and asset-anchor retention. Live video remains explicit-gate only. |
| Competition material | `docs/handoff/AFS-COMPETITION-DEMO-RUN-SHEET.md`, `docs/handoff/AFS-COMPETITION-DEMO-TALK-TRACK.md` | preserve presentation support | Keep as rehearsal material. It must preserve non-claim boundaries and avoid committing generated media. |

## Legacy Operator Paths

| Area | Current files | Classification | Retirement condition |
|---|---|---|---|
| Direct Kling video smoke | `narratocut/model_gateway/kling_*.py`, `apps/cli/kling_video_command.py`, `tests/test_kling_video_*.py`, `tests/kling_video_smoke_helpers.py` | keep hidden/operator | Retire direct CLI exposure after `memory-video-pipeline-*` can run optional gated live I2V lanes and task recovery through a protocol file. |
| Direct MiniMax image smoke | `narratocut/model_gateway/minimax_image_*.py`, `apps/cli/minimax_image_command.py`, `tests/test_minimax_image_smoke.py` | keep hidden/operator | Retire direct CLI exposure after protocol execution owns optional gated keyframe generation and subject-reference handling. |
| PosterFlow provider adapter | `narratostudio/posterflow/minimax_provider.py`, `tests/test_posterflow_provider.py` | keep adapter | This is a provider adapter, not a product command. Keep as long as PosterFlow and MiniMax image generation are supported behind explicit image gates. |
| Numbered demo CLI wrapper | `apps/cli/memory_demo_commands.py` | keep hidden until replacement | Remove after DEMO-012 and DEMO-015 runtime behavior is represented by protocol-driven commands and tests. |
| Shared DEMO-011 content | `narratocut/memory_advantage_demo_011_content.py` | keep temporarily | Delete after asset-card data is migrated into sanitized protocol examples or a generic asset-memory fixture. |

## Removal Candidates

These are candidates only. Remove in a separate cleanup patch after confirming
imports, tests, and docs for the affected area.

| Candidate | Evidence | Proposed action | Gate before deletion |
|---|---|---|---|
| Old generated bytecode caches | ignored `__pycache__` entries under `apps/`, `agentflow/`, `narratocut/`, `narratostudio/`, `tests/` | applied: deleted from local checkout only | Confirmed all 35 targets were inside the repository and ignored by Git before deletion; never stage generated caches. |
| Long-form historical DEVLOG body | root `DEVLOG.md` had a multi-thousand-line historical body | applied: compressed into dated archive index | Created `docs/archive/devlog_history_2026_05.md`, preserved current 2026-05-31 entries in root `DEVLOG.md`, and saved full pre-slimming raw text under ignored `data/processed/maintenance_backups/AFS-SLIMMING-DEVLOG-001/`. |
| DEMO-012 bespoke runtime modules | active only as evidence/operator path | replace with protocol execution, then remove | Protocol runner supports same MiniMax I2I + Kling I2V chain with tests and hidden legacy command removed. |
| DEMO-015 bespoke runtime modules | active only as evidence/operator path | replace with protocol execution, then remove | Protocol runner supports same baseline vs memory-backed I2V chain and review artifact shape. |
| Provider smoke direct commands | hidden but still importable | retire direct commands from app registry after protocol live execution exists | Focused provider/protocol tests pass; legacy docs point to protocol path. |

## Applied Cleanup - 2026-05-31

- Deleted 35 ignored `__pycache__` directories under `apps/`, `agentflow/`,
  `narratocut/`, `narratostudio/`, and `tests/`.
- Before deletion, each resolved absolute path was confirmed inside
  `D:\Projects\AgentFlowStudio`, and each relative path was confirmed ignored
  by Git with `git check-ignore`.
- No tracked source file, test file, evidence document, provider adapter,
  generated run evidence, secret, local configuration, or Company knowledge-base
  file was deleted.
- Verification after cleanup:
  - `python -B -m apps.cli.main --help` -> passed; visible product CLI surface
    stayed on `memory-video-pipeline-*`, `memory-evidence-reuse-review`, and
    `web-bridge`.
  - `python -B -m pytest tests/test_memory_video_pipeline_workflow.py tests/test_memory_advantage_demo_012.py tests/test_memory_advantage_demo_015.py tests/test_minimax_image_smoke.py tests/test_kling_video_smoke.py -q`
    -> 32 passed.
  - Source/test `__pycache__` recount under the cleanup roots -> 0 remaining.
  - `git diff --check` -> no whitespace errors; CRLF normalization warnings
    only.

## Applied DEVLOG Compression - 2026-05-31

- Replaced the root `DEVLOG.md` long-form historical body with an active short
  log that keeps current 2026-05-31 maintenance entries and links to live
  ledgers.
- Added `docs/archive/devlog_history_2026_05.md` as a compact historical
  section index for the older 2026-05 DEVLOG entries.
- Preserved the full pre-slimming DEVLOG text under ignored local path
  `data/processed/maintenance_backups/AFS-SLIMMING-DEVLOG-001/DEVLOG.pre_slimming_2026-05-31.md`.
- Line-count result: root `DEVLOG.md` and the committed DEVLOG archive index
  are both under the 300-line target.
- Boundary kept: no source code, tests, provider adapters, evidence runbooks,
  generated run evidence, secrets, local configuration, or Company
  knowledge-base files were changed.
- Verification after compression:
  - `python -B -m apps.cli.main --help` -> passed.
  - `python -B -m pytest tests/test_agentflow_roadmap_docs.py tests/test_memory_video_pipeline_workflow.py tests/test_memory_advantage_demo_012.py tests/test_memory_advantage_demo_015.py tests/test_minimax_image_smoke.py tests/test_kling_video_smoke.py -q`
    -> 48 passed.
  - Root `DEVLOG.md` and `docs/archive/devlog_history_2026_05.md` are both
    under the 300-line target.
  - Source/test `__pycache__` recount under cleanup roots -> 0 remaining.
  - `git diff --check` -> no whitespace errors; CRLF normalization warnings
    only.

## Applied Staging Classification - 2026-05-31

- Added `docs/maintenance/AFS-STAGING-CANDIDATE-001.md` to classify the dirty
  checkout before any staging.
- Current snapshot at classification time: 51 modified tracked files and 120
  untracked files.
- The ledger separates mainline staging candidates, evidence/runbook
  preservation, provider/operator quarantine, numbered-demo legacy, and
  local-only ignored runtime artifacts.
- The full rule hierarchy is explicitly applied: Company source knowledge base
  -> global workflow skills -> project `AGENTS.md` ->
  `docs/company_operating_model.md` -> `TASK_TRACKER.md` / branch handoff ->
  current task.
- Provider config bridge issue captured and addressed:
  `narratocut/model_gateway/company_secrets.py` no longer hardcodes a local
  Company `.secrets` path as a default. Provider/operator staging still needs
  separate no-secret and capability-gate review. Focused provider/operator
  tests now cover explicit path, `NARRATOCUT_PROVIDER_CONFIG`, and hidden CLI
  help fallback wording.
- Provider/operator staging review added:
  `docs/maintenance/AFS-PROVIDER-OPERATOR-STAGING-REVIEW-001.md` records the
  separate support-slice decision and keeps direct provider commands outside
  the default product surface.
- Mainline staging bundle drafted:
  `docs/maintenance/AFS-MAINLINE-STAGING-BUNDLE-001.md` records the current
  product mainline plus reviewed support/evidence layering. CLI registration is
  now split between product `command_registry.py` and hidden
  `support_command_registry.py`.
- Boundary kept: no staging, commit, deletion, source rewrite, provider call,
  generated media promotion, or Company knowledge-base copy.

## Applied Oversized File Split - 2026-05-31

- Split `narratocut/memory_advantage_demo_012_review.py` by moving HTML
  rendering into `narratocut/memory_advantage_demo_012_review_html.py`.
- Split `tests/test_memory_advantage_demo_012.py` by moving fake provider
  manifest helpers into `tests/memory_advantage_demo_012_helpers.py`.
- Split `tests/test_contract_examples.py` by moving memory-video-pipeline
  contract example checks into
  `tests/test_contract_examples_memory_video_pipeline.py`.
- Current changed/untracked code/docs scan reports no files over the
  300 effective-line target.
- Verification after split:
  - `python -B -m pytest --assert=plain tests/test_memory_advantage_demo_012.py tests/test_contract_examples.py tests/test_contract_examples_memory_video_pipeline.py -q`
    -> 39 passed.
- Boundary kept: no behavior change, provider call, generated media promotion,
  staging, commit, or Company knowledge-base copy.

## Applied Staging Preflight Guard - 2026-05-31

- Added `tools/staging_preflight.py` as a no-side-effect dirty-tree preflight
  over `git status --short`.
- It expands untracked directories and fails local-only paths, generated media
  or bytecode, effective file length over 300 lines, and hardcoded local Company
  `.secrets` paths.
- Added `tests/test_staging_preflight.py` for parsing, directory expansion,
  local-only path blocking, secret-path blocking, and pass report formatting.
- Current dirty tree preflight passes after excluding generated test temp data
  from the working tree.

## Do Not Remove Yet

- `memory-video-pipeline-*` implementation, examples, and tests.
- Web Memory Workbench files tied to `AFS-WORKBENCH-IMPLEMENTATION-001`.
- DEMO-012 through RECORDING-016 evidence docs and runbooks.
- Provider adapters needed by hidden operator smoke tests or future gated live
  execution.
- Ignored generated run evidence under `data/processed/`; keep ignored and
  reference only when needed.

## Next Cleanup Order

1. Keep this ledger as the boundary reference for subsequent deletion patches.
2. Add protocol-driven optional live execution for image/I2V only if explicitly
   approved and capability gates are set.
3. Once protocol live execution exists, remove hidden numbered demo commands
   and then the bespoke DEMO-012/015 modules.
4. Run a dedicated provider/operator staging review before including hidden live
   tooling in a branch commit; the config bridge no longer carries the local
   Company `.secrets` default.
5. Use `docs/maintenance/AFS-STAGING-CANDIDATE-001.md` as the staging checklist
   before any branch commit.

## Verification For This Ledger

This ledger should be checked with:

```powershell
python -m apps.cli.main --help
pytest tests/test_memory_video_pipeline_workflow.py tests/test_memory_advantage_demo_012.py tests/test_memory_advantage_demo_015.py tests/test_minimax_image_smoke.py tests/test_kling_video_smoke.py -q
git diff --check
```
