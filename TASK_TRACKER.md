# AgentFlow Studio Task Tracker

Last updated: 2026-06-02 by Codex

This tracker is the live AgentFlow Studio work ledger. It should contain only
active, next, and blocked work plus short links to current evidence. Historical
completed rows from the pre-reset tracker were moved to
`docs/archive/task_history_2026_05.md`.

Company source knowledge base:

```text
D:\Learning materials\Learning_notes\Company
```

Project-facing operating model:

```text
docs/company_operating_model.md
```

## Current Operating Rule

- Do not open another numbered memory-advantage demo module; use the
  protocol-driven memory video pipeline path instead.
- Keep `memory-video-pipeline-*` as the visible CLI product surface. Numbered
  memory-advantage demo commands and direct provider smoke commands are legacy
  evidence/operator entries and should stay hidden from default help unless a
  task explicitly needs them.
- Do not treat provider smoke, machine tests, generated demos, or contact
  sheets as human acceptance or business validation.
- Do not commit secrets, provider keys, signed URLs, cookies, local media,
  model caches, or generated runtime artifacts.
- Keep remote provider calls gated by capability and explicit task approval.
- At the start of new development conversations, classify the task as
  `Light`, `Standard`, `Deep`, or `Strategic` before choosing main checkout,
  worktree, or subagent execution.
- Start subagents only for bounded roles with independent scope, verifiable
  artifacts, integration order, and close conditions; close or mark inactive
  any idle, stale, blocked, or unverifiable lane.

## Active Work

| ID | Owner role | Scope | Status | Verification / evidence |
|---|---|---|---|---|
| AFS-MAINTENANCE-RESET-001 | Release Integrator + Orchestrator | Classify the dirty worktree, repair/split tracker scope, and record promote/archive/remove decisions before more implementation | classification complete | Evidence: `docs/maintenance/AFS-MAINTENANCE-RESET-001.md`; raw pre-reset tracker bytes preserved under ignored `data/processed/maintenance_backups/AFS-MAINTENANCE-RESET-001/` |
| AFS-MEMORY-PIPELINE-MVP-001 | Workflow Engineer + Memory / Evidence Steward | Replace bespoke numbered demo execution with one protocol-driven memory video pipeline | no-call package command and feedback-event draft complete; live provider execution not implemented | Evidence: `memory-video-pipeline-package`, `examples/agentflow/memory_video_pipeline_package.example.json`, `agentflow/memory/video_pipeline_workflow.py`, `agentflow/memory/video_pipeline_feedback.py`, `docs/handoff/AFS-MEMORY-PIPELINE-MVP-001.md`; provider execution remains optional/gated |
| AFS-POST-DEMO-PRODUCTIZATION | Orchestrator + Product Lead | Convert Local Alpha 0.4 and memory-advantage demo evidence into the next productization queue | roadmap recorded; execute through MVP/workbench lanes | Evidence: `docs/handoff/AFS-POST-DEMO-PRODUCTIZATION-ROADMAP.md`; keeps architecture completeness, runnable image/video demo, workbench usability, Company knowledge feedback, provider gateway, and durable Memory runtime boundaries separated |
| AFS-PRODUCTION-MEMORY-LOOP-001 | Workflow Engineer + Memory / Evidence Steward + Web UI Agent | Implement the first generic Production Memory Architecture loop from source records to context bundle/readiness, planned next-pass bundle, draft feedback capture, explicit promotion-decision overlay, and read-only Web canvas | verified locally; commit on `codex/afs-production-memory-loop-001` | Evidence: `agentflow/memory/production_loop.py`, `agentflow/memory/production_next_pass.py`, `agentflow/memory/production_feedback.py`, `agentflow/memory/production_promotion.py`, `examples/agentflow/production_memory_loop.example.json`, `docs/architecture/production_memory_architecture.md`, `docs/handoff/AFS-PRODUCTION-MEMORY-LOOP-001.md`; full suite passed (`698 passed`); no provider call, no Company KB write, no human acceptance or business validation claim |

## Next Queue

These lanes remain queued behind the current memory-pipeline first slice.

| ID | Owner role | Scope | Entry condition |
|---|---|---|---|
| AFS-WORKBENCH-REDESIGN-001 | Product Lead + Web UI Agent | Design the memory production workbench before further Web implementation | Design brief complete; implementation not started |
| AFS-WORKBENCH-IMPLEMENTATION-001 | Web UI Agent + QA Reviewer | Implement static memory workbench first screen from package fixture | static first screen, explicit package loading, bundle summaries, evidence-bundle gap visibility, read-only artifact inspector, canvas-to-inspector focus, read-only workflow action strip, browser-local feedback draft preview, one-click sample bundle, source-status display, canvas view/focus tools, experiment protocol panel, demo evidence summary, Studio Canvas polish, demo-ready checklist, and readiness cockpit implemented |
| AFS-MEMORY-REVIEW-CLI-001 | Memory / Evidence Steward | Expose evidence reuse validator as a read-only CLI/review command | implemented as stdout-first CLI with explicit optional validation JSON output; no durable writes or provider calls |
| AFS-WEB-EVIDENCE-SUMMARY-001 | Web UI Agent + QA Reviewer | Show memory reuse review summary in Web without promotion or scanning | Optional narrow follow-up after reset |
| AFS-SECOND-PASS-001 | Workflow Engineer + Harness / QA Reviewer | Run a real second pass from accepted context evidence | Requires explicit run plan and artifact boundaries |
| AFS-ACCEPTANCE-FEEDBACK-001 | Orchestrator + Product Lead | Capture human acceptance feedback separately from machine review | Requires selected demo artifacts and human review protocol |

## Blocked / Optional

| ID | Owner role | Scope | Blocker |
|---|---|---|---|
| AFS-POSTER-LIVE-002 | Provider Adapter Agent + Security / Secret Audit Agent | Optional PosterFlow live image smoke | Blocked unless local image-provider env is configured and `NARRATOCUT_ALLOW_REMOTE_IMAGE=true` is explicitly set for the task |
| Durable Memory runtime | Memory / Evidence Steward | Persistent Memory runtime, DB/vector store/RAG, or automatic company memory writes | Not part of the current demo proof; needs a separate design and approval |
| Business validation | Product Lead | External market/user validation | Not performed in Local Alpha 0.4 or the current memory-advantage demos |

## Recent Evidence Index

| Area | Status | Evidence / boundary |
|---|---|---|
| Local Alpha 0.4 runtime | passed runtime verification on this workstation | `docs/handoff/AFS-RUN-PACKAGE-001.md`; ignored run artifacts under `data/processed/runs/local_alpha_0_4_product_loop` |
| Local Alpha 0.4 Web operator | passed after stale readiness blocker fix | `docs/handoff/AFS-WEB-OPERATOR-002.md`; no provider call or generated artifact committed |
| Local Alpha 0.4 memory-quality review | passed as structural traceability only | `docs/handoff/AFS-MEMORY-QUALITY-002.md`; no durable Memory runtime and no real second-pass execution |
| Local Alpha 0.4 acceptance reconciliation | completed as pass/block/non-claim ledger | `docs/local_alpha_0_4_acceptance_reconciliation.md` |
| Kling/MiniMax provider clients | useful provider smoke/client code exists but needs promotion decision | gated adapters under `narratocut/model_gateway/` and CLI commands; no secrets should be committed |
| Mainline slimming boundary | boundary ledger drafted; first cleanup applied | `docs/maintenance/AFS-SLIMMING-BOUNDARY-001.md` classifies memory-video-pipeline and Web Workbench as mainline, DEMO-012 through RECORDING-016 as evidence to preserve, direct Kling/MiniMax smoke and numbered demo commands as hidden legacy/operator paths, and old bytecode/DEVLOG/demo modules as staged removal candidates; ignored bytecode cache cleanup deleted 35 ignored local `__pycache__` directories after path and `git check-ignore` gates; focused boundary tests passed (`32 passed`); no provider calls |
| Ignored bytecode cache cleanup | applied locally | Deleted ignored `__pycache__` directories only under `apps/`, `agentflow/`, `narratocut/`, `narratostudio/`, and `tests/`; 35 targets were inside the repo and ignored by Git, 0 unsafe targets, 0 remaining after `python -B` CLI/test verification; no tracked code/evidence/provider/Company files touched |
| DEVLOG historical compression | applied | Root `DEVLOG.md` is now an active short log under the 300-line target; older 2026-05 sections are indexed in `docs/archive/devlog_history_2026_05.md`, and full pre-slimming raw text is preserved only under ignored `data/processed/maintenance_backups/AFS-SLIMMING-DEVLOG-001/`; docs/boundary tests passed (`48 passed`); no code/provider/evidence runbook/Company files touched |
| Pre-staging candidate ledger | drafted | `docs/maintenance/AFS-STAGING-CANDIDATE-001.md` classifies the dirty checkout before staging: 51 modified tracked files, 120 untracked files, and ignored `data/processed/` runtime/backup roots; provider/operator files are quarantined from mainline staging; the local Company `.secrets` default in `company_secrets.py` has been removed and provider config now requires explicit `--provider-config` or `NARRATOCUT_PROVIDER_CONFIG`; docs/boundary tests passed (`48 passed`) |
| Provider config bridge hardening | applied | `narratocut/model_gateway/company_secrets.py` no longer commits a machine-local Company `.secrets` default; hidden provider/operator CLI commands default provider config to `None` and rely on explicit path or `NARRATOCUT_PROVIDER_CONFIG`; focused provider/operator tests passed (`29 passed`); default CLI and hidden command help checked; hardcoded local `.secrets` path scan clean; no provider calls |
| Provider/operator staging review | drafted | `docs/maintenance/AFS-PROVIDER-OPERATOR-STAGING-REVIEW-001.md` classifies direct Kling/MiniMax commands, provider adapters, RECORDING-016 script, and mocked tests as a separate hidden support slice; live recording script now requires explicit provider config as well as the video gate; provider/operator suite passed (`44 passed`); docs test passed (`16 passed`); no provider calls |
| Mainline staging bundle | #73 merged; #72 ready for master review | `docs/maintenance/AFS-MAINLINE-STAGING-BUNDLE-001.md` defines the current integration bundle as product mainline plus reviewed hidden support/evidence; #73 merged the Local Alpha 0.4 base into `master` as `94401afe`, while #72 was rebased onto `origin/master`, retargeted to `master`, and marked ready for review; CLI registration is split between product `command_registry.py` and hidden `support_command_registry.py`; post-rebase full suite passed (`675 passed`); no provider calls |
| Oversized file slimming | applied | DEMO-012 HTML rendering, DEMO-012 test manifest helpers, and memory-video-pipeline contract example checks were split into focused files; current changed/untracked code/docs effective-line scan reports no files over 300 lines; focused DEMO-012 and contract example tests passed (`39 passed`); no provider calls |
| Staging preflight guard | applied and used for bundle commit | `tools/staging_preflight.py` turns the staging boundary into a local no-side-effect check over `git status --short`; it fails local-only paths, oversized effective files, and hardcoded Company `.secrets` paths; preflight unit tests passed and the committed mainline bundle passed preflight before commit; no provider calls |
| Workflow engine node slimming | focused split applied | `narratocut/workflow_engine/nodes.py` now keeps base node orchestration and registry under 300 lines, while `narratocut/workflow_engine/node_artifacts.py` owns artifact JSON loading, schema validation, state fallback, and shared node input/output helpers; duplicate helper definitions were removed from focused node modules; focused workflow/helper tests passed (`81 passed`) and full suite passed (`662 passed`); no provider calls |
| Kling provider smoke slimming | focused split applied | `narratocut/model_gateway/kling_video_smoke.py` now keeps public smoke orchestration under 300 lines, `narratocut/model_gateway/kling_video_runtime.py` owns HTTP/curl runtime parsing, and focused Kling tests passed (`16 passed`); no provider calls |
| MiniMax provider smoke slimming | focused split applied | `narratocut/model_gateway/minimax_image_smoke.py` now keeps public smoke entrypoints under 300 lines, `narratocut/model_gateway/minimax_image_plan.py` owns request planning/config resolution, and `narratocut/model_gateway/minimax_image_runtime.py` owns runtime image helpers; focused MiniMax/provider tests passed (`32 passed`); no provider calls |
| Memory video pipeline protocol | no-call plan, review, and observation slices complete | `memory-video-pipeline-plan` writes sanitized plan artifacts; `memory-video-pipeline-review` reads explicit I2V manifest refs; `memory-video-pipeline-observe` records bounded human visual notes under ignored `data/processed/` |
| Memory video package command | no-call product package complete | `memory-video-pipeline-package` links plan, explicit-artifact review, bounded observation, presentation material, and an `agentflow_feedback_event` draft; no provider calls, media copy, durable memory write, human acceptance, or business validation |
| CLI product surface | first slimming slice applied | Default `python -m apps.cli.main --help` now promotes `memory-video-pipeline-*` and hides numbered memory-advantage demo/provider smoke commands; legacy commands remain directly invocable for existing evidence runbooks |
| CLI module split | command registry extracted | `apps/cli/main.py` now stays under the 300-line project target; extension command imports and Typer registration live in `apps/cli/command_registry.py` |
| Web static test slimming | focused test split applied | Oversized Web static suites were split by responsibility: production mode, memory workbench structure/feedback/canvas/sample, artifact viewer structure, artifact workspace normalization, and read-only boundaries; focused Web static suite passed (`50 passed`) and full suite passed (`662 passed`) |
| Web runtime module slimming | focused JS split applied | `apps/web/app.js`, `apps/web/production-mode.js`, and `apps/web/memory-workbench-package.js` now stay under the 300-line target by moving Review rendering, local bridge transport/buttons, and package-ref constants into focused modules; focused Web static suite passed (`50 passed`), full suite passed (`662 passed`), and Edge headless loaded `#memory` without detected module/syntax error markers |
| Web CSS module slimming | focused CSS split applied | `apps/web/styles.css` and `apps/web/memory-workbench.css` are import-only entries with base/layout/control/responsive rules moved into focused files under 300 lines; focused Web static suite passed (`50 passed`), full suite passed (`662 passed`), and Edge headless loaded `#memory` without detected module/CSS load or syntax error markers |
| Web shell template slimming | focused HTML shell split applied | `apps/web/index.html` is now a 17-line static root that mounts local Review, Production, and Memory shell template modules before element collection; shell template files stay under 300 lines; focused Web static suite passed (`50 passed`), full suite passed (`662 passed`), and Edge headless rendered `#memory` without detected template/module error markers |
| Web README slimming | focused docs split applied | `apps/web/README.md` is now a short operator entry point under 300 lines; detailed Web workbench milestones and reference material live in `docs/workbench/web_workbench_milestones.md` and `docs/workbench/web_workbench_reference.md`; focused Web static suite passed (`50 passed`) and full suite passed (`662 passed`) |
| Numbered demo cleanup | DEMO-002 and DEMO-008 through DEMO-011 retired from active code | Bespoke early demo modules, focused tests, CLI registrations, and DEMO-006 through DEMO-011 handoff drafts removed; `docs/archive/task_history_2026_05.md` keeps compressed history; `memory_advantage_demo_011_content.py` remains only as shared asset-card data for DEMO-012/015 |
| Memory advantage demo evidence | compelling but bounded demo evidence exists | strongest current signal is RECORDING-016: repeated same-keyframe I2V where baseline varied more and memory-backed outputs were more consistent |
| RECORDING-016 operator recording | ready for explicit-gate live recording | `tools/run_memory_advantage_recording_016.ps1` supports dry-run and requires `-AllowRemoteVideo` or `NARRATOCUT_ALLOW_REMOTE_VIDEO=true` for Kling I2V; runbook: `docs/handoff/AFS-MEMORY-ADVANTAGE-RECORDING-016.md` |
| Competition demo narration | ready for rehearsal | `docs/handoff/AFS-COMPETITION-DEMO-TALK-TRACK.md` provides a 60-second live talk track, a 3-minute recording script, claim boundaries, and judge Q&A |
| Competition demo run sheet | machine rehearsal passed; ready for human rehearsal | `docs/handoff/AFS-COMPETITION-DEMO-RUN-SHEET.md` lists preflight, Slidev commands, optional live I2V recording, fallbacks, safe wording, human rehearsal checklist, and feedback capture template |
| Post-demo productization roadmap | ready for next-lane execution | `docs/handoff/AFS-POST-DEMO-PRODUCTIZATION-ROADMAP.md` turns the demo evidence into the next queue: protocol-driven memory pipeline, workbench design, human feedback capture, read-only review CLI, Web evidence summary, and later provider gateway |
| Memory production workbench design | ready for implementation planning | `docs/workbench/AFS-WORKBENCH-REDESIGN-001.md` defines the operator workflow, first screen, states, memory provenance display, local-only boundaries, and browser verification plan; no Web implementation or provider call |
| Memory workbench implementation slice | focused Web verification passed | `apps/web/memory-workbench-controller.js`, `apps/web/memory-workbench-package.js`, `apps/web/memory-workbench-inspector.js`, `apps/web/memory-workbench-feedback.js`, `apps/web/memory-workbench-sample.js`, `apps/web/memory-workbench-render.js`, `apps/web/memory-workbench-demo-summary.js`, `apps/web/memory-workbench-demo-render.js`, `apps/web/memory-workbench-demo-checklist.js`, `apps/web/memory-workbench-demo-checklist-render.js`, and `apps/web/memory-workbench-studio.css` let user-selected protocol/package/review/observation/presentation/feedback JSON refresh and inspect the canvas from explicit artifacts, including referenced-but-not-selected bundle gaps, read-only node-to-card focus, navigation-only workflow actions, copy-only `agentflow_feedback_event` draft preview, a sanitized in-memory `Load sample bundle` path, source-status display, Flow/Compare/Review focus tools, an Experiment Protocol panel for lane parity plus non-claim boundaries, a Demo Evidence Summary talk-track panel, a grouped demo-ready checklist, a dynamic `Can present / Evidence gaps / Do not claim` readiness cockpit, a Studio Canvas first-screen header, and hash-based `#memory` demo entry; focused Web static tests passed (`66 passed`); no bridge edits, provider calls, directory scanning, browser persistence, ref auto-open, raw JSON editing, workflow execution, artifact write, project-file auto-read, or durable Memory runtime |
| Memory evidence reuse CLI | focused memory/contract verification passed | `memory-evidence-reuse-review` reads explicit review/candidate/decision JSON, validates `runtime evidence -> feedback source -> memory candidate -> promotion decision -> context bundle -> second-pass prompt`, fails broken refs and rejected reuse, writes no file by default, and writes validation JSON only when `--output` is explicit; focused tests passed (`57 passed`); no provider calls, runtime artifact writes, durable memory write, second-pass execution, human acceptance, or business validation |
| Production memory loop 001 | generic no-provider product slice verified | `production-memory-loop-validate`, `production-memory-loop-run-no-provider`, `production-memory-loop-draft-feedback`, `production-memory-loop-review-promotion`, and `production-memory-loop-run-reviewed-feedback-no-provider` validate `project_input -> artifact_ledger -> feedback_events -> memory_candidates -> promotion_decisions -> context_bundle -> pass_readiness -> next_pass_bundle`, plus draft new feedback/candidate/pending-promotion artifacts and reviewed promotion overlay artifacts; example requires `kind: agentflow_production_memory_loop` and `schema_version: production-memory-loop/v1`; focused loop tests passed (`10 passed`), feedback capture tests passed (`5 passed`), promotion overlay tests passed (`4 passed`), Web static suite passed (`65 passed`), Web static HTTP smoke passed, full suite passed (`698 passed`); browser-level DOM smoke remains blocked by no detected browser runner; optional provider validation remains blocked by unset image/video/provider gates; no provider calls, durable memory writes, Company KB writes, project-specific inspector, human acceptance, or business validation |

## Archive

- Pre-reset tracker history: `docs/archive/task_history_2026_05.md`.
- Raw pre-reset tracker bytes, including the invalid UTF-8 source file, are
  preserved outside Git under
  `data/processed/maintenance_backups/AFS-MAINTENANCE-RESET-001/`.
- Long dated narrative belongs in `DEVLOG.md` only as short pointers to
  detailed docs, not as another full historical tracker.
