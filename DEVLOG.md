# DEVLOG

## 2026-05-27 - AFS-WEB-REPLAY Local Web UI Workbench

- Reviewed and integrated `codex/afs-web-ui-replay`.
- Replayed the preserved Web UI branch onto current `master` instead of
  merging stale `codex/narratocut-web-ui` history directly.
- Added `apps/web/` as a local Review/Production workbench:
  - Review Mode reads only explicitly selected JSON, Markdown, and video files.
  - Production Mode connects only to the local bridge at `127.0.0.1:8787`.
  - The UI keeps browser state non-persistent and does not use `localStorage`,
    IndexedDB, cookies, uploads, provider config, SaaS, or cloud backend.
- Added `apps/web_bridge/` as a stdlib local bridge for workflow discovery,
  plan generation, background local workflow runs, status polling, and review
  refresh.
- Added `python -m apps.cli.main web-bridge` so the README and actual
  executable entrypoint match.
- Verification:
  - `python -m pytest tests/test_web_static_artifact_viewer.py tests/test_web_production_mode_static.py tests/test_web_production_bridge.py tests/test_alpha_smoke_cli.py tests/test_evidence_summary.py tests/test_agentflow_asset_memory_validator.py`: 60 passed.
  - JS syntax checks with `node --check` for all Web modules: passed.
  - `python -m compileall apps\web_bridge apps\cli tests`: passed.
  - `python -m apps.cli.main --help`: passed and listed `web-bridge`.
  - `python -m apps.cli.main web-bridge --help`: passed.
  - `python -m apps.cli.main version`: `0.1.0`.
  - `git diff --check`: passed with Windows line-ending warnings only.
- Browser smoke:
  - Started the bridge on `127.0.0.1:8787` and served the UI on
    `127.0.0.1:8769`.
  - Confirmed Review Mode rendered with no browser error logs.
  - Confirmed Production Mode showed `bridge ready`.
  - Selected `mock_text_to_slices`, generated `workflow_plan.json`, ran the
    workflow to `success`, saw all four steps pass, and refreshed review to
    `passed`.
- Integrated to `master` at `5d0392f`.
- After all four integration lanes were merged, removed the integrated
  worktrees and local branches for `AFS-PROD-001`, `AFS-QA-001`,
  `AFS-MEM-002`, and `AFS-WEB-REPLAY`.
- Archived the old `codex/narratocut-web-ui` branch as
  `archive/narratocut-web-ui-de8ca8e`, deleted the remote branch, then removed
  the old local worktree and branch. It was superseded by the replay and would
  regress the new CLI bridge entrypoint and handoff state if merged directly.
- Boundary kept: no remote provider calls, durable Memory runtime, database,
  SaaS/backend account system, cloud storage, browser persistence, or automatic
  manifest path scanning was added.

## 2026-05-27 - AFS-MEM-002 Memory Promotion Review Decisions

- Reviewed and integrated `codex/afs-memory-promotion-review`.
- Added `agentflow.memory.promotion` as a side-effect-free promotion review
  validator for candidate memory decisions.
- Reused the new promotion checks from the existing asset-memory contract set
  validator so the example chain and the standalone review surface enforce the
  same rules.
- Required promotion decisions to:
  - use one of `promoted`, `rejected`, `merged`, or `expired`;
  - link the source memory candidate;
  - preserve non-empty `evidence_refs`;
  - include the candidate's evidence refs;
  - keep `writes_long_term_memory: false`;
  - reject durable-memory claim fields such as `durable_memory_ref` and
    `persisted_memory_id`.
- Updated the committed promotion decision example and memory contract docs so
  `promoted` means review approval for downstream artifacts, not a durable
  Memory runtime write.
- Verification after rebase onto mainline:
  - `python -m pytest tests/test_agentflow_asset_memory_validator.py tests/test_contract_examples.py tests/test_narratostudio_asset_feedback_smoke.py tests/test_narratostudio_asset_reuse_chain_audit_smoke.py tests/test_posterflow_quality.py tests/test_evidence_summary.py tests/test_alpha_smoke_cli.py`: 57 passed.
  - `python -m compileall agentflow\memory agentflow\harness`: passed.
  - `python -m apps.cli.main --help`: passed.
  - `python -m apps.cli.main version`: `0.1.0`.
  - `python -m apps.cli.main alpha-smoke --json`: returned
    `status: blocked` because remote image provider env is unset.
  - `git diff --check`: passed.
- Integrated to `master` at `8fd9fe4`.
- Boundary kept: no durable Memory runtime, database, vector store, RAG,
  provider call, Web UI change, or alpha smoke behavior change was added.

## 2026-05-27 - AFS-QA-001 Evidence Summary Adapter

- Reviewed and integrated `codex/afs-quality-evidence-summary`.
- Added `agentflow.harness.evidence_summary` as a compact shared evidence
  summary vocabulary for report surfaces.
- `narratocut.harness.quality_checks.build_quality_report()` now adds an
  additive `evidence_summary` field to quality reports.
- `narratocut.harness.reviewer.review_run()` now adds an additive
  `evidence_summary` field to review reports.
- The summary normalizes pass/fail/warning status variants, preserves artifact
  refs, and explicitly separates machine verification from human acceptance,
  business validation, and memory promotion.
- Verification after rebase onto mainline:
  - `python -m pytest tests/test_agent_reviewer.py tests/test_harness_quality_checks.py tests/test_posterflow_quality.py tests/test_narratostudio_review_hardening.py tests/test_evidence_summary.py tests/test_alpha_smoke_cli.py`: 26 passed.
  - `python -m apps.cli.main --help`: passed.
  - `python -m apps.cli.main version`: `0.1.0`.
  - `python -m apps.cli.main alpha-smoke --json`: returned
    `status: blocked` because remote image provider env is unset.
  - `git diff --check`: passed.
- Integrated to `master` at `17c72e5`.
- Boundary kept: no report consumer was forced to infer human acceptance or
  business validation from machine checks; no provider calls, workflow
  execution, Web UI change, or durable Memory runtime was added.

## 2026-05-27 - AFS-PROD-001 Alpha Smoke Status CLI

- Reviewed and integrated `codex/afs-prod-alpha-smoke`.
- Added `python -m apps.cli.main alpha-smoke` and `--json` as a read-only
  Alpha engineering-readiness summary.
- The command reports:
  - NarratoStudio handoff: `pass` when local evidence references exist.
  - NarratoCut package: `pass` when local evidence references exist.
  - PosterFlow live smoke: `blocked` by default when
    `NARRATOCUT_ALLOW_REMOTE_IMAGE=true` is not set.
- Kept provider boundaries explicit: the command does not call remote LLM,
  ASR, image, or video providers and does not write `data/processed` run
  artifacts.
- Added `tests/test_alpha_smoke_cli.py` and linked the command from
  `docs/alpha_readiness_report.md` and `docs/README.md`.
- Verification after rebase onto mainline:
  - `python -m pytest tests/test_video_to_finished_package_local_asr_workflow.py tests/test_narratostudio_workflow.py tests/test_posterflow_provider.py tests/test_alpha_smoke_cli.py`: 25 passed.
  - `python -m apps.cli.main alpha-smoke --json`: returned
    `status: blocked` with PosterFlow provider env shown as unset.
  - `git diff --check`: passed with Windows line-ending warnings only.
- Integrated to `master` at `5c88d21`.
- Boundary kept: no human acceptance or business validation claim, no live
  provider smoke, no generated media, no Web UI, no durable Memory runtime.

## 2026-05-27 - Parallel Worktree Launch

- Committed the operating-system projection baseline as
  `6d0cf88 docs: add agent operating entry points` so new worktrees inherit
  `docs/agent_operating_roster.md` and `docs/agent_task_brief_template.md`.
- Created four independent worktrees from that baseline:
  - `codex/afs-prod-alpha-smoke` at
    `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-prod-alpha-smoke`
  - `codex/afs-quality-evidence-summary` at
    `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-quality-evidence-summary`
  - `codex/afs-memory-promotion-review` at
    `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-memory-promotion-review`
  - `codex/afs-web-ui-replay` at
    `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-web-ui-replay`
- Dispatched three worker subagents due to the current active-agent limit:
  - `Dewey` / `019e6549-7170-72c3-b588-8eecf1b05784` for `AFS-PROD-001`
  - `Nietzsche` / `019e6549-8563-72b0-b6fb-6f5a486b5d52` for `AFS-QA-001`
  - `Mencius` / `019e6549-9a28-79a1-92be-d7e39a082350` for `AFS-MEM-002`
- `AFS-WEB-REPLAY` remains an opened worktree and is assigned to the main
  controller until a worker slot is free.
- Boundary kept: this launch pass only created branches/worktrees and
  dispatched bounded tasks. No remote providers were called and no generated
  artifacts were committed.

## 2026-05-27 - AFS-OPS-002 Agent Operating Entry Points

- Added project-level execution entry points for the AI-native company
  operating model:
  - `docs/agent_operating_roster.md` defines standing roles, temporary roles,
    dispatch triggers, subagent lifecycle, and the next parallel queue.
  - `docs/agent_task_brief_template.md` provides the bounded task brief to use
    before opening worktrees or spawning subagents.
- Updated `AGENTS.md` and `docs/company_operating_model.md` so substantial
  AFS work routes through the roster and task brief instead of ad hoc prompts.
- Added capability-specific remote provider gates for LLM, ASR, image, video,
  and external downloads. Authorization for one provider capability does not
  authorize another.
- Updated `TASK_TRACKER.md` with the next parallel queue:
  `AFS-PROD-001`, `AFS-QA-001`, `AFS-MEM-002`, and `AFS-WEB-REPLAY`.
- Fixed stale AFS-MEM-001 tracker wording so its detailed status matches the
  integrated mainline state.
- Promoted reusable lessons back to the Company knowledge base:
  subagent lifecycle, old-agent history handling, context trace evidence
  boundaries, and provider capability gates.
- Checked the three previous audit subagent IDs. The agent manager returned
  `not found` for each, so they are inactive history rather than open
  workstreams.
- Verification:
  - `git diff --check`: passed.
  - Company knowledge base `git diff --check`: passed.
  - `python -m pytest tests/test_agentflow_roadmap_docs.py`: 8 passed.
  - `python -m apps.cli.main --help`: passed.
  - `python -m apps.cli.main version`: `0.1.0`.
- Boundary kept: no runtime code, workflow behavior, provider behavior, Web UI
  code, generated artifacts, secrets, or remote calls were changed.

## 2026-05-26 - Web UI Branch Baseline Repair And Hygiene

- Repaired the preserved `codex/narratocut-web-ui` worktree after the
  repository rename left its `.git` pointer aimed at the removed
  `D:\Projects\NarratoCut` checkout.
- Committed and pushed the branch-local Web UI M3.1 supervised production
  workbench checkpoint at `de8ca8e`.
- Moved the worktree to the AgentFlow Studio convention:
  `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\narratocut-web-ui`.
- Classified the branch as preserved but not merge-ready. It is synced to
  `origin/codex/narratocut-web-ui`, but still diverges from `master` and must
  be rebased or replayed before mainline integration.
- Web UI branch verification before push:
  - `python -m pytest tests/test_web_static_artifact_viewer.py tests/test_web_production_mode_static.py tests/test_web_production_bridge.py`: 41 passed.
  - `python -m pytest`: 374 passed.
  - `python -m apps.cli.main --help`: passed.
  - `python -m apps.cli.main version`: `0.1.0`.
  - JS syntax checks, `compileall`, and `git diff --check`: passed.
- Environment note: the old Web UI worktree used Python 3.13.5 during this
  verification. Mainline integration should rerun the same matrix in the
  project-preferred Python 3.12 environment.
- Boundary kept: no Web UI code was merged into `master`; this pass only
  repaired, backed up, relocated, and classified the parallel branch.

## 2026-05-24 - Alpha Readiness Evidence Report

- Replayed the alpha evidence report from the old
  `codex/alpha-readiness-evidence` branch onto current `master` without
  merging the stale provider stack below it.
- Did not use the MiniMax key pasted in chat. The original evidence treated
  PosterFlow live smoke as blocked by provider configuration; this replay keeps
  that evidence boundary and does not perform remote image calls.
- Re-ran NarratoStudio Alpha handoff evidence in the original branch:
  - workflow success at
    `data/processed/runs/demo_narratostudio_handoff_alpha`
  - `inspect-run`: 65 passed / 0 failed / 0 warnings
  - `review-run`: 83 passed / 0 failed / 0 warnings
- Reproduced and fixed committed ASR/BGM demo example drift:
  - old example inputs pointed to missing `data/raw/demo_bgm/bgm.mp3` and
    `data/raw/demo_bgm/bgm.metadata.json`
  - examples now point to `data/raw/demo_bgm/bgm.wav` plus committed
    `examples/demo_bgm/bgm.metadata.example.json`
  - added a focused regression test so finished-package local-ASR examples keep
    valid BGM metadata references
- Re-ran NarratoCut Alpha package evidence in the original branch:
  - workflow success at `data/processed/runs/demo_narratocut_package_alpha`
  - `inspect-run`: 8 passed / 0 failed / 0 warnings
  - `review-run`: 41 passed / 0 failed / 0 warnings
  - `package-report`: refreshed `package_report.md`
- Added `docs/alpha_readiness_report.md` and linked it from `docs/README.md`.
  The report explicitly separates passed evidence, blocked PosterFlow live
  provider state, demo-only memory, deterministic skeleton boundaries, and
  generated-artifact submission boundaries.
- Boundary kept: no generated media or run artifacts committed, no remote image
  call made, no Web UI, database, durable Memory runtime, Agent runtime,
  provider auto-selection, or workflow/CLI rename added.

## 2026-05-26 - AFS-PROV-001 PosterFlow MiniMax Provider Replay

- Rebuilt the old MiniMax provider branch on fresh `master` in
  `codex/posterflow-minimax-rebase` instead of merging
  `origin/codex/posterflow-minimax-provider-tests` directly. The old branch
  was stale against current Memory OS, quality, context, and two-round demo
  contracts.
- Added a native MiniMax PosterFlow image provider:
  - `NARRATOCUT_IMAGE_PROVIDER=minimax` selects MiniMax through
    `create_image_provider_from_env()`.
  - MiniMax defaults to `https://api.minimax.io` and `image-01`.
  - The provider calls `/v1/image_generation`, requests base64 output, enforces
    MiniMax's `n` range of 1 to 9, writes image candidates, and keeps response
    ids hashed in metadata.
- Kept existing OpenAI-compatible behavior as the default provider and moved
  shared remote-image gate / input-hash helpers into
  `narratostudio.posterflow.provider_common`.
- Updated PosterFlow round 1 and round 2 generation nodes to use the provider
  factory while preserving the existing `NARRATOCUT_ALLOW_REMOTE_IMAGE=true`
  safety gate.
- Added provider tests for MiniMax payload shape, secret-safe invocation logs,
  candidate-count validation before remote calls, HTTP/base response error
  hygiene, env provider selection, and base URLs that already include `/v1`.
- TDD evidence:
  - red: `python -m pytest tests/test_posterflow_provider.py` failed with
    `ModuleNotFoundError: No module named 'narratostudio.posterflow.minimax_provider'`.
  - red: the `/v1` base-url regression test failed with
    `https://api.minimax.io/v1/v1/image_generation`.
  - green: provider tests passed after adding the MiniMax provider and endpoint
    normalization.
- Verification:
  - `python -m pytest tests/test_posterflow_provider.py`: 12 passed.
  - `python -m pytest tests/test_posterflow_provider.py tests/test_posterflow_workflow.py tests/test_posterflow_quality.py`: 22 passed.
  - `python -m pytest`: 495 passed.
  - `git diff --check`: passed with Windows line-ending warnings only.
  - `python -m apps.cli.main --help`: passed.
  - `python -m apps.cli.main version`: `0.1.0`.
- Boundary kept: no remote image call was made, no secrets were written, no
  durable Memory runtime or provider orchestration was added, and the stale old
  MiniMax branch was not integrated directly.

## 2026-05-23 - PosterFlow Memory Demo Remote Image Workflow

- Added a PosterFlow visual memory demo that runs inside the existing
  AgentFlow Studio workflow engine.
- Added `narratostudio/posterflow/` with focused schema, SOP, OpenAI-compatible
  image provider, and report/HTML preview modules.
- Added `workflows/posterflow_memory_demo.yaml` plus
  `examples/posterflow/poster_brief.example.json` and
  `examples/posterflow/poster_feedback.example.json`.
- Added `NARRATOCUT_ALLOW_REMOTE_IMAGE=true` as a separate remote-image gate
  from the existing LLM/ASR gates. The provider uses
  `NARRATOCUT_IMAGE_BASE_URL`, `NARRATOCUT_IMAGE_API_KEY`, and
  `NARRATOCUT_IMAGE_MODEL`.
- Added PosterFlow inspect/review quality checks for required artifacts,
  candidate images, feedback-to-candidate references, candidate-only memory,
  accepted-memory profile references, and no long-term memory writes.
- Kept the generated preference profile `demo_only` so it cannot be confused
  with a durable project memory profile.
- Boundary kept: no Web UI, database/vector store, long-term Memory runtime,
  automatic durable preference write, publishing integration, or default remote
  provider call.
- TDD red run:
  - `pytest tests/test_posterflow_provider.py tests/test_posterflow_workflow.py tests/test_posterflow_quality.py`: failed with `ModuleNotFoundError: No module named 'narratostudio.posterflow'`
  - `pytest tests/test_posterflow_provider.py -q`: failed because the image
    provider checked API-key configuration before the remote-image opt-in gate.
  - `pytest tests/test_posterflow_provider.py -q`: failed because HTTP error
    response bodies could enter provider exception messages.
- Targeted verification:
  - `pytest tests/test_posterflow_provider.py -q`: 6 passed
  - `pytest tests/test_posterflow_provider.py tests/test_posterflow_workflow.py tests/test_posterflow_quality.py -q`: 12 passed
- Full verification before final handoff:
  - `python -m compileall apps agentflow narratocut narratostudio tests`: passed
  - `git diff --check`: passed with CRLF warnings only
  - `python -m apps.cli.main --help`: passed
  - `python -m apps.cli.main version`: `0.1.0`
  - `pytest`: 485 passed

## 2026-05-23 - Phase 15.29 NarratoStudio Asset Reuse Chain Audit Smoke

- Synced local `master` to merged PR #69 at `c665a4b`.
- Removed the merged `codex/agentflow-asset-reuse-chain-fixtures` branch
  locally and remotely after confirming it matched `origin/master`; preserved
  the separate `codex/narratocut-web-ui` worktree branch.
- Started `codex/agentflow-asset-reuse-chain-audit-smoke` from a clean
  mainline.
- Added focused TDD coverage in
  `tests/test_narratostudio_asset_reuse_chain_audit_smoke.py`; the first red
  run failed because `agentflow.memory.narratostudio_reuse_audit` did not
  exist.
- Added
  `agentflow.memory.narratostudio_reuse_audit.audit_narratostudio_asset_reuse_chain_fixture`
  as a pure in-memory audit smoke for fixture-built asset reuse chains.
- The audit smoke checks expected chain keys, artifact types, ready/blocked
  status shapes, no-execute/no-memory-write boundaries, and unexpected
  contract-surface drift.
- Boundary kept: no new contract artifact type, Memory runtime, durable
  candidate promotion, long-term memory write, persisted reusable asset
  profile, workflow execution change, CLI change, provider call,
  database/vector-store/file-repository write, hosted API, Web UI behavior, or
  `data/processed/runs/` artifact write.
- Verification started:
  - `.venv\Scripts\python.exe -m pytest tests/test_narratostudio_asset_reuse_chain_audit_smoke.py`: first red run failed with `ModuleNotFoundError: No module named 'agentflow.memory.narratostudio_reuse_audit'`
  - `.venv\Scripts\python.exe -m pytest tests/test_narratostudio_asset_reuse_chain_audit_smoke.py`: 4 passed
  - `.venv\Scripts\python.exe -m pytest tests/test_agentflow_roadmap_docs.py tests/test_agentflow_intermediate_asset_architecture.py`: first red run failed because Phase 15.29 docs were not recorded yet
- Final verification was run in a clean temporary worktree at
  `origin/master` plus only the Phase 15.29 staged patch because the main
  working tree contains unrelated PosterFlow draft changes:
  - `.venv\Scripts\python.exe -m pytest tests/test_narratostudio_asset_reuse_chain_audit_smoke.py tests/test_narratostudio_asset_reuse_chain_fixtures.py tests/test_agentflow_roadmap_docs.py tests/test_agentflow_intermediate_asset_architecture.py`: 20 passed
  - `.venv\Scripts\python.exe -m pytest`: 473 passed
  - `.venv\Scripts\python.exe -m compileall apps agentflow narratocut narratostudio tests`: passed
  - `git diff --check`: passed
  - `.venv\Scripts\python.exe -m apps.cli.main --help`: passed
  - `.venv\Scripts\python.exe -m apps.cli.main version`: `0.1.0`

## 2026-05-23 - Phase 15.28 NarratoStudio Asset Reuse Chain Fixtures

- Synced local `master` to merged PR #68 at `e54b06b`.
- Removed the merged `codex/agentflow-asset-reuse-review-surface` branch
  locally and remotely after confirming its tree matched `origin/master`;
  preserved the separate `codex/narratocut-web-ui` worktree branch.
- Started `codex/agentflow-asset-reuse-chain-fixtures` from a clean mainline.
- Added focused TDD coverage in
  `tests/test_narratostudio_asset_reuse_chain_fixtures.py`; the first red run
  failed because `agentflow.memory.narratostudio_reuse_chain` did not exist.
- Added
  `agentflow.memory.narratostudio_reuse_chain.build_narratostudio_asset_reuse_dry_run_chain`
  as a pure in-memory fixture builder that composes the existing review,
  validation, gate, dry-run plan, and reuse review artifacts.
- Boundary kept: no new contract artifact type, Memory runtime, durable
  candidate promotion, long-term memory write, persisted reusable asset
  profile, workflow execution change, CLI change, provider call,
  database/vector-store/file-repository write, hosted API, Web UI behavior, or
  `data/processed/runs/` artifact write.
- Verification started:
  - `.venv\Scripts\python.exe -m pytest tests/test_narratostudio_asset_reuse_chain_fixtures.py`: first red run failed with `ModuleNotFoundError: No module named 'agentflow.memory.narratostudio_reuse_chain'`
  - `.venv\Scripts\python.exe -m pytest tests/test_narratostudio_asset_reuse_chain_fixtures.py`: 3 passed
  - `.venv\Scripts\python.exe -m pytest tests/test_narratostudio_asset_reuse_chain_fixtures.py tests/test_narratostudio_asset_reuse_review_surface.py tests/test_agentflow_narratostudio_asset_reuse_review_example.py tests/test_agentflow_contract_helpers.py tests/test_contract_examples.py tests/test_agentflow_contract_audit.py tests/test_agentflow_roadmap_docs.py tests/test_agentflow_intermediate_asset_architecture.py`: 53 passed
- Final verification:
  - `.venv\Scripts\python.exe -m pytest`: 467 passed
  - `.venv\Scripts\python.exe -m compileall apps agentflow narratocut narratostudio tests`: passed
  - `git diff --check`: passed with CRLF warnings only
  - `.venv\Scripts\python.exe -m apps.cli.main --help`: passed
  - `.venv\Scripts\python.exe -m apps.cli.main version`: `0.1.0`

## 2026-05-23 - Phase 15.27 NarratoStudio Asset Reuse Review Surface

- Synced local `master` to merged PR #67 at `063b39e`.
- Removed the merged `codex/agentflow-asset-reuse-dry-run-planner` branch
  locally and remotely after confirming its tree matched `origin/master`;
  preserved the separate `codex/narratocut-web-ui` worktree branch.
- Started `codex/agentflow-asset-reuse-review-surface` from a clean mainline.
- Added focused TDD coverage in
  `tests/test_narratostudio_asset_reuse_review_surface.py`; the first red run
  failed because `agentflow.memory.narratostudio_reuse_review` did not exist.
- Added
  `agentflow.memory.narratostudio_reuse_review.review_narratostudio_asset_reuse_dry_run_chain`
  as a pure in-memory review surface for existing review, validation, gate, and
  dry-run plan artifacts.
- The review surface returns
  `agentflow_narratostudio_asset_reuse_review`, checks chain id consistency,
  preserves blocked/failed/ready status, and rejects runtime or
  long-term-memory-write claims.
- Added a committed
  `examples/agentflow/narratostudio_asset_reuse_review.example.json`,
  registered it in AgentFlow contract helpers, registry, and audit examples,
  and covered it in contract example tests.
- Updated Phase 15 roadmap, product roadmap, and intermediate asset
  architecture docs to record Phase 15.27 as chain review only.
- Boundary kept: no Memory runtime, durable candidate promotion, long-term
  memory write, persisted reusable asset profile, workflow execution change,
  CLI change, provider call, database/vector-store/file-repository write,
  hosted API, Web UI behavior, or `data/processed/runs/` artifact write.
- Verification started:
  - `.venv\Scripts\python.exe -m pytest tests/test_narratostudio_asset_reuse_review_surface.py`: first red run failed with `ModuleNotFoundError: No module named 'agentflow.memory.narratostudio_reuse_review'`
  - `.venv\Scripts\python.exe -m pytest tests/test_narratostudio_asset_reuse_review_surface.py`: first implementation found blocking id ordering mismatch for blocked gates
  - `.venv\Scripts\python.exe -m pytest tests/test_narratostudio_asset_reuse_review_surface.py`: 4 passed
  - `.venv\Scripts\python.exe -m pytest tests/test_narratostudio_asset_reuse_review_surface.py tests/test_agentflow_narratostudio_asset_reuse_review_example.py tests/test_agentflow_contract_helpers.py tests/test_contract_examples.py tests/test_agentflow_contract_audit.py tests/test_agentflow_roadmap_docs.py tests/test_agentflow_intermediate_asset_architecture.py`: 49 passed
- Final verification:
  - `.venv\Scripts\python.exe -m pytest`: 463 passed
  - `.venv\Scripts\python.exe -m compileall apps agentflow narratocut narratostudio tests`: passed
  - `git diff --check`: passed with CRLF warnings only
  - `.venv\Scripts\python.exe -m apps.cli.main --help`: passed
  - `.venv\Scripts\python.exe -m apps.cli.main version`: `0.1.0`

## 2026-05-23 - Phase 15.26 NarratoStudio Asset Reuse Dry-run Planner

- Synced local `master` to merged PR #66 at `df44ec6`.
- Removed the merged `codex/agentflow-asset-feedback-review-gate` branch
  locally and remotely after confirming its tree matched `origin/master`;
  preserved the separate `codex/narratocut-web-ui` worktree branch.
- Started `codex/agentflow-asset-reuse-dry-run-planner` from a clean mainline.
- Added focused TDD coverage in
  `tests/test_narratostudio_asset_reuse_dry_run_planner.py`; the first red
  run failed because `agentflow.memory.narratostudio_reuse` did not exist.
- Added
  `agentflow.memory.narratostudio_reuse.plan_narratostudio_asset_reuse_dry_run`
  as a pure in-memory dry-run planner for existing review and gate artifacts.
- The planner returns
  `agentflow_narratostudio_asset_reuse_dry_run_plan`, blocks failed gates,
  keeps selected asset profiles dry-run-only, and rejects runtime or
  long-term-memory-write claims.
- Added a committed
  `examples/agentflow/narratostudio_asset_reuse_dry_run_plan.example.json`,
  registered it in AgentFlow contract helpers, registry, and audit examples,
  and covered it in contract example tests.
- Updated Phase 15 roadmap, product roadmap, and intermediate asset
  architecture docs to record Phase 15.26 as dry-run planning only.
- Boundary kept: no Memory runtime, durable candidate promotion, long-term
  memory write, persisted reusable asset profile, workflow execution change,
  CLI change, provider call, database/vector-store/file-repository write,
  hosted API, Web UI behavior, or `data/processed/runs/` artifact write.
- Verification started:
  - `.venv\Scripts\python.exe -m pytest tests/test_narratostudio_asset_reuse_dry_run_planner.py tests/test_agentflow_contract_helpers.py tests/test_contract_examples.py`: first red run failed with `ModuleNotFoundError: No module named 'agentflow.memory.narratostudio_reuse'`
  - `.venv\Scripts\python.exe -m pytest tests/test_narratostudio_asset_reuse_dry_run_planner.py tests/test_agentflow_contract_helpers.py tests/test_contract_examples.py tests/test_agentflow_contract_audit.py`: 37 passed
  - `.venv\Scripts\python.exe -m pytest`: first full run found the existing `tests/test_agentflow_narratostudio_asset_reuse_dry_run.py` interface and failed because the planner only accepted `review`/`gate`
  - `.venv\Scripts\python.exe -m pytest tests/test_agentflow_narratostudio_asset_reuse_dry_run.py tests/test_narratostudio_asset_reuse_dry_run_planner.py tests/test_agentflow_contract_helpers.py tests/test_contract_examples.py tests/test_agentflow_contract_audit.py tests/test_agentflow_roadmap_docs.py tests/test_agentflow_intermediate_asset_architecture.py`: 50 passed after supporting the existing direct contract-input interface
- Final verification:
  - `.venv\Scripts\python.exe -m pytest`: 457 passed
  - `.venv\Scripts\python.exe -m compileall apps agentflow narratocut narratostudio tests`: passed
  - `git diff --check`: passed with CRLF warnings only
  - `.venv\Scripts\python.exe -m apps.cli.main --help`: passed
  - `.venv\Scripts\python.exe -m apps.cli.main version`: `0.1.0`

## 2026-05-23 - Phase 15.25 NarratoStudio Asset Feedback Review Gate

- Synced local `master` to merged PR #65 at `cfd155f`.
- Removed the merged `codex/agentflow-asset-feedback-review-harness` branch
  locally and remotely after confirming its tree matched `origin/master`;
  preserved the separate `codex/narratocut-web-ui` worktree branch.
- Started `codex/agentflow-asset-feedback-review-gate` from a clean mainline.
- Added focused TDD coverage in
  `tests/test_agentflow_narratostudio_asset_feedback_review_gate.py`; the
  first red run failed because
  `gate_narratostudio_asset_feedback_review` did not exist.
- Added
  `agentflow.harness.narratostudio_review.gate_narratostudio_asset_feedback_review`
  as a pure in-memory decision-only gate for existing
  `agentflow_narratostudio_asset_feedback_review_validation` artifacts.
- The gate returns
  `agentflow_narratostudio_asset_feedback_review_gate`, blocks failed review
  validations, keeps blocking check ids focused on source validation failures,
  and rejects runtime or long-term-memory-write claims.
- Added a committed
  `examples/agentflow/narratostudio_asset_feedback_review_gate.example.json`,
  registered it in AgentFlow contract helpers, registry, and audit examples,
  and covered it in contract example tests.
- Updated Phase 15 roadmap, product roadmap, and intermediate asset
  architecture docs to record Phase 15.25 as decision-only gate work.
- Boundary kept: no Memory runtime, durable candidate promotion, long-term
  memory write, persisted reusable asset profile, workflow execution change,
  CLI change, provider call, database/vector-store/file-repository write,
  hosted API, Web UI behavior, or `data/processed/runs/` artifact write.
- Verification started:
  - `.venv\Scripts\python.exe -m pytest tests/test_agentflow_narratostudio_asset_feedback_review_gate.py`: first red run failed with `ImportError: cannot import name 'gate_narratostudio_asset_feedback_review'`
  - `.venv\Scripts\python.exe -m pytest tests/test_agentflow_narratostudio_asset_feedback_review_gate.py`: first implementation failed because blocking ids included the generic `validation_passed` check instead of only the source validation failure id
  - `.venv\Scripts\python.exe -m pytest tests/test_agentflow_narratostudio_asset_feedback_review_gate.py tests/test_agentflow_narratostudio_asset_feedback_review_harness.py`: 7 passed
  - `.venv\Scripts\python.exe -m pytest tests/test_agentflow_contract_helpers.py tests/test_contract_examples.py`: contract example regression first failed because the gate artifact was missing from examples, registry, and helpers
  - `.venv\Scripts\python.exe -m pytest tests/test_agentflow_contract_helpers.py tests/test_contract_examples.py tests/test_agentflow_contract_audit.py`: 33 passed
- Final verification:
  - `.venv\Scripts\python.exe -m pytest tests/test_agentflow_narratostudio_asset_feedback_review_gate.py tests/test_agentflow_narratostudio_asset_feedback_review_harness.py tests/test_narratostudio_asset_feedback_review_surface.py tests/test_agentflow_contract_helpers.py tests/test_contract_examples.py tests/test_agentflow_contract_audit.py tests/test_agentflow_roadmap_docs.py tests/test_agentflow_intermediate_asset_architecture.py`: 50 passed
  - `.venv\Scripts\python.exe -m pytest`: 446 passed
  - `.venv\Scripts\python.exe -m compileall apps agentflow narratocut narratostudio tests`: passed
  - `git diff --check`: passed with CRLF warnings only
  - `.venv\Scripts\python.exe -m apps.cli.main --help`: passed
  - `.venv\Scripts\python.exe -m apps.cli.main version`: `0.1.0`

## 2026-05-23 - Phase 15.24 NarratoStudio Asset Feedback Review Harness

- Synced local `master` to merged PR #64 at `f007a85`.
- Removed the merged `codex/agentflow-asset-feedback-review-surface` branch
  locally and remotely after confirming its tree matched `origin/master`;
  preserved the separate `codex/narratocut-web-ui` worktree branch.
- Started `codex/agentflow-asset-feedback-review-harness` from a clean
  mainline.
- Added focused TDD coverage in
  `tests/test_agentflow_narratostudio_asset_feedback_review_harness.py`; the
  first red run failed because `agentflow.harness.narratostudio_review` did
  not exist.
- Added
  `agentflow.harness.narratostudio_review.validate_narratostudio_asset_feedback_review`
  as a pure in-memory harness validator for
  `agentflow_narratostudio_asset_feedback_review` artifacts.
- The validator checks review-only boundaries, embedded source/asset-memory
  validation shape, failed-source skip behavior, overall status consistency,
  and private path/secret hygiene.
- Added a committed
  `examples/agentflow/narratostudio_asset_feedback_review_validation.example.json`,
  registered it in AgentFlow contract helpers, registry, and audit examples,
  and covered it in contract example tests.
- Updated Phase 15 roadmap, product roadmap, and intermediate asset
  architecture docs to record Phase 15.24 as harness validation only.
- Boundary kept: no Memory runtime, durable candidate promotion, long-term
  memory write, persisted reusable asset profile, workflow execution change,
  CLI change, provider call, database/vector-store/file-repository write,
  hosted API, Web UI behavior, or `data/processed/runs/` artifact write.
- Verification started:
  - `.venv\Scripts\python.exe -m pytest tests/test_agentflow_narratostudio_asset_feedback_review_harness.py`: first red run failed with `ModuleNotFoundError: No module named 'agentflow.harness.narratostudio_review'`
  - `.venv\Scripts\python.exe -m pytest tests/test_agentflow_narratostudio_asset_feedback_review_harness.py`: 4 passed
- Final verification:
  - `.venv\Scripts\python.exe -m pytest tests/test_agentflow_narratostudio_asset_feedback_review_harness.py tests/test_narratostudio_asset_feedback_review_surface.py tests/test_agentflow_contract_helpers.py tests/test_contract_examples.py tests/test_agentflow_contract_audit.py tests/test_agentflow_roadmap_docs.py tests/test_agentflow_intermediate_asset_architecture.py`: 46 passed
  - `.venv\Scripts\python.exe -m pytest`: 442 passed
  - `.venv\Scripts\python.exe -m compileall apps agentflow narratocut narratostudio tests`: passed
  - `git diff --check`: passed with CRLF warnings only
  - `.venv\Scripts\python.exe -m apps.cli.main --help`: passed
  - `.venv\Scripts\python.exe -m apps.cli.main version`: `0.1.0`

## 2026-05-23 - Phase 15.23 NarratoStudio Asset Feedback Review Surface

- Synced local `master` to merged PR #63 at `f1308e7`.
- Removed the merged `codex/agentflow-asset-feedback-contract-validator`
  branch locally and remotely after confirming its tree matched
  `origin/master`; preserved the separate `codex/narratocut-web-ui` worktree
  branch.
- Started `codex/agentflow-asset-feedback-review-surface` from a clean
  mainline.
- Added focused TDD coverage in
  `tests/test_narratostudio_asset_feedback_review_surface.py`; the first red
  run failed because `agentflow.memory.narratostudio_review` did not exist.
- Added
  `agentflow.memory.narratostudio_review.review_narratostudio_asset_feedback_loop`
  as a pure in-memory review surface that composes source validation, the
  NarratoStudio asset/memory smoke adapter, and AgentFlow asset/memory
  contract-set validation.
- Added a committed
  `examples/agentflow/narratostudio_asset_feedback_review.example.json`,
  registered it in AgentFlow contract helpers, registry, and audit examples,
  and covered it in contract example tests.
- Added a packaging regression in `tests/test_agentflow_package_skeleton.py`
  and included `agentflow*` in `pyproject.toml` package discovery so the
  platform package remains present after editable or wheel installs.
- The review surface returns
  `agentflow_narratostudio_asset_feedback_review` and marks the
  asset/memory step `not_run` when source validation fails, so broken source
  semantics are not hidden by downstream adaptation.
- Updated Phase 15 roadmap, product roadmap, and intermediate asset
  architecture docs to record Phase 15.23 as review-surface work only.
- Boundary kept: no Memory runtime, durable candidate promotion, long-term
  memory write, persisted reusable asset profile, workflow execution change,
  CLI change, provider call, database/vector-store/file-repository write,
  hosted API, Web UI behavior, or `data/processed/runs/` artifact write.
- Verification started:
  - `.venv\Scripts\python.exe -m pytest tests/test_narratostudio_asset_feedback_review_surface.py`: first red run failed with `ModuleNotFoundError: No module named 'agentflow.memory.narratostudio_review'`
  - `.venv\Scripts\python.exe -m pytest tests/test_narratostudio_asset_feedback_review_surface.py`: 2 passed
  - `.venv\Scripts\python.exe -m pytest tests/test_agentflow_contract_helpers.py tests/test_contract_examples.py tests/test_agentflow_contract_audit.py`: contract example regression first failed because the review artifact was missing from examples, registry, and audit coverage
  - `.venv\Scripts\python.exe -m pytest tests/test_agentflow_contract_helpers.py tests/test_contract_examples.py tests/test_agentflow_contract_audit.py`: 31 passed
  - `.venv\Scripts\python.exe -m pytest tests/test_agentflow_package_skeleton.py`: packaging regression first failed because `agentflow` was missing from setuptools package discovery
  - `.venv\Scripts\python.exe -m pytest tests/test_agentflow_package_skeleton.py`: 6 passed
- Final verification:
  - `.venv\Scripts\python.exe -m pytest tests/test_narratostudio_asset_feedback_review_surface.py tests/test_narratostudio_asset_feedback_contract_validator.py tests/test_narratostudio_asset_feedback_smoke.py tests/test_agentflow_asset_memory_validator.py tests/test_agentflow_package_skeleton.py tests/test_agentflow_contract_helpers.py tests/test_contract_examples.py tests/test_agentflow_contract_audit.py tests/test_agentflow_roadmap_docs.py tests/test_agentflow_intermediate_asset_architecture.py`: 65 passed
  - `.venv\Scripts\python.exe -m pytest`: 437 passed
  - `.venv\Scripts\python.exe -m compileall apps agentflow narratocut narratostudio tests`: passed
  - `git diff --check`: passed with CRLF warnings only
  - `.venv\Scripts\python.exe -m apps.cli.main --help`: passed
  - `.venv\Scripts\python.exe -m apps.cli.main version`: `0.1.0`

## 2026-05-23 - Phase 15.22 NarratoStudio Asset Feedback Source Validator

- Synced local `master` to merged PR #62 at `0a197e2`.
- Removed the merged `codex/narratostudio-asset-feedback-smoke` branch locally
  and remotely after confirming its tree matched `origin/master`.
- Started `codex/agentflow-asset-feedback-contract-validator` from a clean
  mainline.
- Added focused TDD coverage in
  `tests/test_narratostudio_asset_feedback_contract_validator.py`; the first
  red run failed because
  `validate_narratostudio_asset_feedback_sources` did not exist.
- Added
  `agentflow.memory.narratostudio_assets.validate_narratostudio_asset_feedback_sources`
  to validate NarratoStudio source payloads before mapping them into the
  AgentFlow asset/memory contract set.
- The validator checks source schema/type, `production_handoff.json` prompt-pack
  refs, candidate-only `memory_candidates.json`, derived
  `feedback_signal_log.json`, and local deterministic `cost_quality_trace.json`.
- Added a regression for malformed candidate stores; the first run exposed a
  `TypeError`, then the validator was tightened to return failed validation
  instead of throwing.
- Added a regression for missing candidate identity fields so source validation
  fails before the mapping helper can raise on missing `id` or `statement`.
- Updated Phase 15 roadmap, product roadmap, and intermediate asset architecture
  docs to record Phase 15.22 as source-payload validation only.
- Boundary kept: no Memory runtime, durable candidate promotion, long-term
  memory write, persisted reusable asset profile, workflow execution change,
  CLI change, provider call, database/vector-store/file-repository write,
  hosted API, Web UI behavior, or `data/processed/runs/` artifact write.
- Verification started:
  - `.venv\Scripts\python.exe -m pytest tests/test_narratostudio_asset_feedback_contract_validator.py`: first red run failed with `ImportError: cannot import name 'validate_narratostudio_asset_feedback_sources'`
  - `.venv\Scripts\python.exe -m pytest tests/test_narratostudio_asset_feedback_contract_validator.py`: 4 passed
  - `.venv\Scripts\python.exe -m pytest tests/test_narratostudio_asset_feedback_contract_validator.py`: malformed candidate store regression first failed with `TypeError: 'NoneType' object is not iterable`
  - `.venv\Scripts\python.exe -m pytest tests/test_narratostudio_asset_feedback_contract_validator.py tests/test_narratostudio_asset_feedback_smoke.py tests/test_agentflow_asset_memory_validator.py`: 17 passed
  - `.venv\Scripts\python.exe -m pytest tests/test_narratostudio_asset_feedback_contract_validator.py`: candidate identity regression first failed because the validator accepted a candidate without `id`
- Final verification:
  - `.venv\Scripts\python.exe -m pytest tests/test_narratostudio_asset_feedback_contract_validator.py tests/test_narratostudio_asset_feedback_smoke.py tests/test_agentflow_asset_memory_validator.py tests/test_agentflow_roadmap_docs.py tests/test_agentflow_intermediate_asset_architecture.py`: 26 passed
  - `.venv\Scripts\python.exe -m pytest`: 433 passed
  - `.venv\Scripts\python.exe -m compileall apps agentflow narratocut narratostudio tests`: passed
  - `git diff --check`: passed with CRLF warnings only
  - `.venv\Scripts\python.exe -m apps.cli.main --help`: passed
  - `.venv\Scripts\python.exe -m apps.cli.main version`: `0.1.0`

## 2026-05-23 - Phase 15.21 NarratoStudio Asset Feedback Loop Smoke

- Continued from merged PR #61 at `a552c45` on
  `codex/narratostudio-asset-feedback-smoke`.
- Confirmed remote state after `git fetch --prune`: `origin/master` at
  `a552c45`, with only `origin/master` and the preserved
  `origin/codex/narratocut-web-ui` branch visible remotely.
- Added focused TDD coverage in
  `tests/test_narratostudio_asset_feedback_smoke.py`; the first red run failed
  because `agentflow.memory.narratostudio_assets` did not exist.
- Added
  `agentflow.memory.narratostudio_assets.build_narratostudio_asset_memory_contract_set`
  as a pure in-memory adapter from current NarratoStudio run payloads into the
  AgentFlow asset/memory contract set.
- The smoke adapter uses `production_handoff.json`, `memory_candidates.json`,
  `feedback_signal_log.json`, and `cost_quality_trace.json` payloads, then the
  existing `agentflow.memory.assets.validate_asset_memory_contract_set`
  validates the resulting contract set.
- Updated Phase 15 roadmap, product roadmap, and intermediate asset architecture
  docs to record Phase 15.21 as a smoke contract loop only.
- Boundary kept: no Memory runtime, durable candidate promotion, long-term
  memory write, persisted reusable asset profile, workflow execution change,
  CLI change, provider call, database/vector-store/file-repository write,
  hosted API, Web UI behavior, or `data/processed/runs/` artifact write.
- Verification started:
  - `.venv\Scripts\python.exe -m pytest tests/test_narratostudio_asset_feedback_smoke.py`: first red run failed with `ModuleNotFoundError: No module named 'agentflow.memory.narratostudio_assets'`
  - `.venv\Scripts\python.exe -m pytest tests/test_narratostudio_asset_feedback_smoke.py`: 2 passed
  - `.venv\Scripts\python.exe -m pytest tests/test_narratostudio_asset_feedback_smoke.py`: two added boundary tests first failed because the helper normalized missing `source_of_truth` and `promotion_status`
  - `.venv\Scripts\python.exe -m pytest tests/test_narratostudio_asset_feedback_smoke.py`: 4 passed
- Final verification:
  - `.venv\Scripts\python.exe -m pytest tests/test_narratostudio_asset_feedback_smoke.py tests/test_agentflow_asset_memory_validator.py tests/test_narratostudio_workflow.py tests/test_agentflow_roadmap_docs.py tests/test_agentflow_intermediate_asset_architecture.py`: 26 passed
  - `.venv\Scripts\python.exe -m pytest`: 427 passed
  - `.venv\Scripts\python.exe -m compileall apps agentflow narratocut narratostudio tests`: passed
  - `git diff --check`: passed with CRLF warnings only
  - `.venv\Scripts\python.exe -m apps.cli.main --help`: passed
  - `.venv\Scripts\python.exe -m apps.cli.main version`: `0.1.0`

## 2026-05-22 - Phase 15.20 Intermediate Asset / Memory Validator

- Synced local `master` to merged PR #60 at `5806508`.
- Removed the merged `codex/agentflow-skill-validator-migration` branch
  locally and remotely after confirming the feature branch and `origin/master`
  had identical tree hashes.
- Started `codex/agentflow-asset-memory-validator` from a clean mainline.
- Added focused TDD coverage in `tests/test_agentflow_asset_memory_validator.py`;
  the first red run failed because `agentflow.memory.assets` did not exist.
- Added `agentflow.memory.assets.validate_asset_memory_contract_set` as a pure
  in-memory artifact validator for the current intermediate asset, reusable
  asset profile, asset reuse decision, memory candidate, and memory promotion
  decision contracts.
- Added a chain check that `reusable_asset_profile.promotion_decision_ref`
  points to the provided memory promotion decision, and corrected the committed
  reusable asset profile example to reference the current decision id.
- Updated `agentflow.memory` package metadata from reserved namespace to
  platform memory helper layer while keeping runtime status `not_implemented`.
- Updated intermediate asset, memory, architecture refactor, product roadmap,
  and Phase 15 roadmap docs to record this as contract-set validation only.
- Boundary kept: no Memory runtime, candidate promotion, long-term memory write,
  reusable asset creation, workflow execution, skill execution, Router runtime,
  provider call, database/vector-store/file-repository write, CLI change,
  workflow change, schema version change, hosted API, or Web UI change.
- Verification started:
  - `.venv\Scripts\python.exe -m pytest tests/test_agentflow_asset_memory_validator.py`: first red run failed with `ModuleNotFoundError: No module named 'agentflow.memory.assets'`
  - `.venv\Scripts\python.exe -m pytest tests/test_agentflow_asset_memory_validator.py`: 7 passed
  - `.venv\Scripts\python.exe -m pytest tests/test_agentflow_asset_memory_validator.py tests/test_agentflow_package_skeleton.py`: 12 passed
  - `.venv\Scripts\python.exe -m pytest tests/test_agentflow_asset_memory_validator.py tests/test_agentflow_package_skeleton.py tests/test_agentflow_architecture_refactor_plan.py tests/test_agentflow_intermediate_asset_architecture.py tests/test_agentflow_roadmap_docs.py`: 25 passed
  - `.venv\Scripts\python.exe -m pytest tests/test_agentflow_asset_memory_validator.py`: one added chain test failed before the promotion decision reference check was implemented
  - `.venv\Scripts\python.exe -m pytest tests/test_agentflow_asset_memory_validator.py tests/test_contract_examples.py tests/test_agentflow_contract_helpers.py`: 33 passed
- Final verification:
  - `.venv\Scripts\python.exe -m pytest`: 423 passed
  - `.venv\Scripts\python.exe -m compileall apps agentflow narratocut narratostudio tests`: passed
  - `git diff --check`: passed with CRLF warnings only
  - `.venv\Scripts\python.exe -m apps.cli.main --help`: passed
  - `.venv\Scripts\python.exe -m apps.cli.main version`: `0.1.0`

## 2026-05-22 - Phase 15.19 Skill Replay Validator Migration

- Synced local `master` to merged PR #59 at `70604b3`.
- Removed the merged `codex/agentflow-router-validator-migration` branch
  locally and remotely after confirming the feature branch and `origin/master`
  had identical tree hashes.
- Started `codex/agentflow-skill-validator-migration` from a clean mainline.
- Added focused TDD coverage in
  `tests/test_agentflow_skill_validator_migration.py`; the first red run failed
  because `agentflow.harness.agentflow_skill` did not exist.
- Moved Skill replay validator implementation to
  `agentflow.harness.agentflow_skill`.
- Replaced `narratocut.harness.agentflow_skill` with a compatibility wrapper
  that re-exports the platform validator and constants.
- Updated Skill replay validator tests to import from the platform path for new
  code, while keeping compatibility coverage for the legacy NarratoCut path.
- Boundary kept: no skill runtime, skill execution, workflow execution,
  provider call, runtime state, long-term memory write, database row, generated
  run artifact, CLI change, workflow change, schema version change, hosted API,
  or Web UI change.
- Verification started:
  - `.venv\Scripts\python.exe -m pytest tests/test_agentflow_skill_validator_migration.py`: first red run failed with `ModuleNotFoundError: No module named 'agentflow.harness.agentflow_skill'`
  - `.venv\Scripts\python.exe -m pytest tests/test_agentflow_skill_validator_migration.py tests/test_agentflow_skill_replay_validator.py tests/test_agentflow_harness_constants.py tests/test_agentflow_package_skeleton.py`: 17 passed
- Final verification:
  - `.venv\Scripts\python.exe -m pytest tests/test_agentflow_skill_validator_migration.py tests/test_agentflow_skill_replay_validator.py tests/test_agentflow_router_validator_migration.py tests/test_agentflow_router_dry_run_validator.py tests/test_agentflow_harness_constants.py tests/test_agentflow_package_skeleton.py tests/test_agentflow_roadmap_docs.py tests/test_agentflow_architecture_refactor_plan.py tests/test_agentflow_runtime_readiness.py`: 40 passed
  - `.venv\Scripts\python.exe -m pytest`: 414 passed
  - `.venv\Scripts\python.exe -m compileall apps agentflow narratocut narratostudio tests`: passed
  - `git diff --check`: passed with CRLF warnings only
  - `.venv\Scripts\python.exe -m apps.cli.main --help`: passed
  - `.venv\Scripts\python.exe -m apps.cli.main version`: `0.1.0`

## 2026-05-22 - Phase 15.18 Router Dry-run Validator Migration

- Synced local `master` to merged PR #58 at `9382d97` and started
  `codex/agentflow-router-validator-migration` from a clean mainline.
- Removed the merged `codex/agentflow-validator-constants` branch locally and
  remotely after confirming patch equivalence with `origin/master`.
- Added focused TDD coverage in
  `tests/test_agentflow_router_validator_migration.py`; the first red run
  failed because `agentflow.harness.agentflow_router` did not exist.
- Moved Router dry-run validator implementation to
  `agentflow.harness.agentflow_router`.
- Updated `agentflow.harness` package metadata from reserved namespace to
  platform harness layer while keeping runtime status `not_implemented`.
- Replaced `narratocut.harness.agentflow_router` with a compatibility wrapper
  that re-exports the platform validator and constants.
- Updated Router validator tests to import from the platform path for new code,
  while keeping compatibility coverage for the legacy NarratoCut path.
- Updated Router contract, architecture refactor plan, product roadmap, and
  Phase 15 roadmap to record this as Router validator migration only.
- Boundary kept: no Skill replay validator migration, Router runtime, live skill
  selection, skill execution, workflow execution, runtime state, long-term
  memory write, database row, generated run artifact, CLI change, workflow
  change, provider behavior, hosted API, or Web UI change.
- Verification:
  - `.venv\Scripts\python.exe -m pytest tests/test_agentflow_package_skeleton.py tests/test_agentflow_router_validator_migration.py tests/test_agentflow_router_dry_run_validator.py tests/test_agentflow_harness_constants.py tests/test_agentflow_contract_helpers.py tests/test_agentflow_skill_replay_validator.py`: 30 passed
  - `.venv\Scripts\python.exe -m pytest`: 412 passed
  - `.venv\Scripts\python.exe -m compileall apps agentflow narratocut narratostudio tests`: passed
  - `git diff --check`: passed with CRLF warnings only
  - `.venv\Scripts\python.exe -m apps.cli.main --help`: passed
  - `.venv\Scripts\python.exe -m apps.cli.main version`: `0.1.0`

## 2026-05-22 - Phase 15.17 AgentFlow Validator Constants

- Synced local `master` to merged PR #57 at `dd7c2e8` and started
  `codex/agentflow-validator-constants` from a clean mainline.
- Cleaned up stale AgentFlow remote branches whose patches were already present
  on `origin/master`:
  - `codex/agentflow-architecture-refactor-plan`
  - `codex/agentflow-asset-memory-architecture-plan`
  - `codex/agentflow-contract-helpers`
  - `codex/agentflow-package-skeleton`
- Removed local stale AgentFlow branches after confirming patch equivalence with
  `git cherry`; preserved `codex/narratocut-web-ui`.
- Added `agentflow.harness.constants` for shared AgentFlow validator schema
  version, result status strings, and forbidden private/generated/secret
  fragments.
- Updated Router dry-run and Skill replay validators to import the shared
  constants while keeping validator functions in `narratocut.harness.*`.
- Added focused TDD coverage in `tests/test_agentflow_harness_constants.py`;
  the first red run failed because `agentflow.harness.constants` did not exist.
- Updated roadmap/refactor docs to record this as constants migration only.
- Boundary kept: no validator behavior migration, workflow change, CLI change,
  runtime behavior, package rename, workflow rename, artifact contract change,
  provider call, Web UI change, or generated artifact change.
- Verification:
  - `.venv\Scripts\python.exe -m pytest tests/test_agentflow_harness_constants.py tests/test_agentflow_router_dry_run_validator.py tests/test_agentflow_skill_replay_validator.py tests/test_agentflow_package_skeleton.py`: 22 passed
  - `.venv\Scripts\python.exe -m pytest`: 409 passed
  - `.venv\Scripts\python.exe -m compileall apps agentflow narratocut narratostudio tests`: passed
  - `git diff --check`: passed with CRLF warnings only
  - `.venv\Scripts\python.exe -m apps.cli.main --help`: passed
  - `.venv\Scripts\python.exe -m apps.cli.main version`: `0.1.0`

## 2026-05-22 - Phase 15.17a AgentFlow Repo Rename Docs Alignment

- Synced local `master` to merged PR #56 at `be215ad` and started
  `codex/agentflow-repo-rename-docs` from a clean mainline.
- Updated README, docs navigation, AgentFlow architecture, module boundary,
  product roadmap, Phase 15 roadmap, NarratoStudio contracts, post-v0.1.0
  plan, and AGENTS guidance to describe the repository container as
  `AgentFlowStudio`.
- Preserved module names and implementation boundaries:
  - `agentflow/` remains the platform contract and harness migration layer.
  - `narratostudio/` remains the production-side structured handoff MVP.
  - `narratocut/` remains the distribution-side short-video packaging and
    review MVP.
- Boundary kept: docs-only alignment; no Python package rename, CLI rename,
  workflow rename, artifact contract change, version/tag change, runtime
  migration, provider call, Web UI change, or generated artifact change.
- Verification:
  - `.venv\Scripts\python.exe -m pytest tests/test_contract_examples.py tests/test_agentflow_contract_helpers.py`: 25 passed
  - `.venv\Scripts\python.exe -m pytest`: 407 passed
  - `.venv\Scripts\python.exe -m compileall apps agentflow narratocut narratostudio tests`: passed
  - `git diff --check`: passed with CRLF warnings only
  - `.venv\Scripts\python.exe -m apps.cli.main --help`: passed
  - `.venv\Scripts\python.exe -m apps.cli.main version`: `0.1.0`

## 2026-05-22 - Phase 15.13 AgentFlow Intermediate Asset Architecture

- Synced local `master` to merged PR #52 at `7e42a30` and started `codex/agentflow-asset-memory-architecture-plan` from a clean mainline.
- Added focused TDD coverage for intermediate asset examples, reusable asset profiles, asset reuse decisions, registry/audit coverage, and architecture docs.
- First red run failed as expected because `docs/agentflow_intermediate_asset_architecture.md` and the three new AgentFlow asset examples did not exist, and registry/audit/roadmap entries had not been updated.
- Added `docs/agentflow_intermediate_asset_architecture.md` to define the `Agent action -> artifact -> feedback signal -> memory candidate -> promotion decision -> reusable asset` loop.
- Added minimal `agentflow_intermediate_asset`, `agentflow_reusable_asset_profile`, and `agentflow_asset_reuse_decision` examples.
- Updated AgentFlow architecture, artifact map, memory contract, docs navigation, registry, audit report, product roadmap, Phase 15 roadmap, and DEVLOG while keeping the work contract-layer only.
- Verification:
  - `.venv\Scripts\python.exe -m pytest tests/test_contract_examples.py tests/test_agentflow_contract_audit.py tests/test_agentflow_intermediate_asset_architecture.py`: 29 passed
  - `.venv\Scripts\python.exe -m pytest`: 394 passed
  - `.venv\Scripts\python.exe -m compileall apps narratocut narratostudio tests`: passed
  - `git diff --check`: passed with CRLF warnings only
  - `.venv\Scripts\python.exe -m apps.cli.main --help`: passed
  - `.venv\Scripts\python.exe -m apps.cli.main version`: `0.1.0`
- Boundary kept: no workflow, CLI, Memory runtime, Router runtime, skill runtime, database, vector store, cache service, file repository, Web UI, remote provider call, generated run artifact, or long-term memory write changes.

## 2026-05-21 - Phase 15.12 AgentFlow Skill Invocation / Result Replay Validator

- Synced local `master` to merged PR #51 at `f2261b5` and started `codex/agentflow-skill-replay-validator` from a clean mainline.
- Added focused TDD coverage in `tests/test_agentflow_skill_replay_validator.py`; the first red run failed because `narratocut.harness.agentflow_skill` did not exist.
- Added `narratocut.harness.agentflow_skill.validate_skill_invocation_result_replay` as a pure local harness validator for existing `agentflow_skill_invocation` and `agentflow_skill_result` artifacts.
- Added checks for schema version, artifact type, invocation id, project id, skill id, planned invocation status, result status, expected output coverage, quality gate status coverage, passing required gates, review artifact declaration, `writes_long_term_memory: false`, and private path or secret fragments.
- Updated Skill contract, runtime readiness, product roadmap, Phase 15 roadmap, and DEVLOG to keep this scoped as replay validation rather than skill runtime.
- Verification:
  - `.venv\Scripts\python.exe -m pytest tests/test_agentflow_skill_replay_validator.py`: 9 passed
  - `.venv\Scripts\python.exe -m pytest tests/test_agentflow_skill_replay_validator.py tests/test_agentflow_router_dry_run_validator.py tests/test_agentflow_runtime_readiness.py tests/test_agentflow_roadmap_docs.py tests/test_agentflow_pr_review_checklist.py tests/test_contract_examples.py tests/test_agentflow_contract_audit.py`: 50 passed
  - `.venv\Scripts\python.exe -m pytest`: 386 passed
  - `.venv\Scripts\python.exe -m compileall apps narratocut narratostudio tests`: passed
  - `git diff --check`: passed with CRLF warnings only
  - `.venv\Scripts\python.exe -m apps.cli.main --help`: passed
  - `.venv\Scripts\python.exe -m apps.cli.main version`: `0.1.0`
- Boundary kept: no workflow, CLI, skill execution, Router runtime, skill runtime, Memory runtime, database, Web UI, remote provider call, or generated run artifact changes.

## 2026-05-21 - Phase 15.11 AgentFlow Router Dry-run Decision Validator

- Synced local `master` to merged PR #50 at `d10fb55` and started `codex/agentflow-router-dry-run-validator` from a clean mainline.
- Added focused TDD coverage in `tests/test_agentflow_router_dry_run_validator.py`; the first red run failed because `narratocut.harness.agentflow_router` did not exist.
- Added `narratocut.harness.agentflow_router.validate_router_decision_dry_run` as a pure local harness validator for existing `agentflow_router_decision` artifacts.
- Added checks for schema version, artifact type, request summary, selected known skill, selection reason, rejected candidate reasons, selected skill exclusion from rejected candidates, decision-only status, `executes_skill: false`, and private path or secret fragments.
- Updated Router contract, runtime readiness, product roadmap, Phase 15 roadmap, and DEVLOG to keep this scoped as dry-run validation rather than Router runtime.
- Verification:
  - `.venv\Scripts\python.exe -m pytest tests/test_agentflow_router_dry_run_validator.py`: 8 passed
  - `.venv\Scripts\python.exe -m pytest tests/test_agentflow_router_dry_run_validator.py tests/test_agentflow_runtime_readiness.py tests/test_agentflow_roadmap_docs.py tests/test_agentflow_pr_review_checklist.py tests/test_contract_examples.py tests/test_agentflow_contract_audit.py`: 41 passed
  - `.venv\Scripts\python.exe -m pytest`: 377 passed
  - `.venv\Scripts\python.exe -m compileall apps narratocut narratostudio tests`: passed
  - `git diff --check`: passed with CRLF warnings only
  - `.venv\Scripts\python.exe -m apps.cli.main --help`: passed
  - `.venv\Scripts\python.exe -m apps.cli.main version`: `0.1.0`
- Boundary kept: no workflow, CLI, skill execution, Router runtime, skill runtime, Memory runtime, database, Web UI, remote provider call, or generated run artifact changes.

## 2026-05-21 - Phase 15.10 AgentFlow Runtime Readiness Spike

- Synced local `master` to merged PR #49 at `c2244d5` and started `codex/agentflow-runtime-readiness-spike` from a clean mainline.
- Added a focused test first in `tests/test_agentflow_runtime_readiness.py`; the red run failed because `docs/agentflow_runtime_readiness.md` did not exist.
- Added `docs/agentflow_runtime_readiness.md` to define contract, artifact, review, feedback/memory, cost-quality, and operations gates before any AgentFlow runtime work.
- Updated docs navigation, Phase 15 roadmap, and DEVLOG.
- Verification:
  - `.venv\Scripts\python.exe -m pytest tests/test_agentflow_runtime_readiness.py`: 4 passed
  - `.venv\Scripts\python.exe -m pytest tests/test_agentflow_runtime_readiness.py tests/test_agentflow_roadmap_docs.py tests/test_agentflow_pr_review_checklist.py tests/test_contract_examples.py tests/test_agentflow_contract_audit.py`: 33 passed
  - `.venv\Scripts\python.exe -m pytest`: 369 passed
  - `.venv\Scripts\python.exe -m compileall apps narratocut narratostudio tests`: passed
  - `git diff --check`: passed with CRLF warnings only
  - `.venv\Scripts\python.exe -m apps.cli.main --help`: passed
  - `.venv\Scripts\python.exe -m apps.cli.main version`: `0.1.0`
- Boundary kept: docs and tests only; no workflow, CLI, Python runtime, runtime validator, Router runtime, skill runtime, Memory runtime, Web UI, database, or generated run artifact changes.

## 2026-05-21 - Phase 15.9 AgentFlow Roadmap Document Split

- Synced local `master` to merged PR #48 at `89d7a7b` and started `codex/agentflow-roadmap-doc-split` from a clean mainline.
- Added a focused test first in `tests/test_agentflow_roadmap_docs.py`; the red run failed because `docs/product_roadmap.md` was 415 lines and `docs/agentflow_phase15_roadmap.md` did not exist.
- Moved detailed Phase 15.1-15.8 history into `docs/agentflow_phase15_roadmap.md`.
- Shortened `docs/product_roadmap.md` back to a product-level roadmap with a Phase 15 detail link.
- Updated docs navigation and DEVLOG.
- Verification:
  - `.venv\Scripts\python.exe -m pytest tests/test_agentflow_roadmap_docs.py`: 4 passed
  - `.venv\Scripts\python.exe -m pytest tests/test_agentflow_roadmap_docs.py tests/test_agentflow_pr_review_checklist.py tests/test_contract_examples.py tests/test_agentflow_contract_audit.py`: 29 passed
  - `.venv\Scripts\python.exe -m pytest`: 365 passed
  - `.venv\Scripts\python.exe -m compileall apps narratocut narratostudio tests`: passed
  - `git diff --check`: passed with CRLF warnings only
  - `.venv\Scripts\python.exe -m apps.cli.main --help`: passed
  - `.venv\Scripts\python.exe -m apps.cli.main version`: `0.1.0`
- Boundary kept: docs and tests only; no workflow, CLI, Python runtime, runtime validator, Router runtime, skill runtime, Memory runtime, Web UI, or generated run artifact changes.

## 2026-05-21 - Phase 15.8 AgentFlow PR Review Checklist

- Synced local `master` to merged PR #47 at `3489e19` and started `codex/agentflow-pr-review-checklist` from a clean mainline.
- Added a focused test first in `tests/test_agentflow_pr_review_checklist.py`; the red run failed because `docs/agentflow_pr_review_checklist.md` did not exist.
- Added `docs/agentflow_pr_review_checklist.md` as the human review gate for AgentFlow contract-layer PRs.
- Updated docs navigation, contract validation docs, architecture, roadmap, and DEVLOG.
- Verification:
  - `.venv\Scripts\python.exe -m pytest tests/test_agentflow_pr_review_checklist.py`: 4 passed
  - `.venv\Scripts\python.exe -m pytest tests/test_contract_examples.py tests/test_agentflow_contract_audit.py tests/test_agentflow_pr_review_checklist.py`: 25 passed
  - `.venv\Scripts\python.exe -m pytest`: 361 passed
  - `.venv\Scripts\python.exe -m compileall apps narratocut narratostudio tests`: passed
  - `git diff --check`: passed with CRLF warnings only
  - `.venv\Scripts\python.exe -m apps.cli.main --help`: passed
  - `.venv\Scripts\python.exe -m apps.cli.main version`: `0.1.0`
- Boundary kept: no workflow, CLI, Python runtime, CI config, runtime validator, registry service, Router runtime, skill runtime, Memory runtime, database, cross-module execution, Web UI, or remote provider behavior changed.

## 2026-05-21 - Phase 15.7 AgentFlow Contract Audit Gate

- Synced local `master` to merged PR #46 at `36dcdd1` and started `codex/agentflow-contract-audit-gate` from a clean mainline.
- Added a static AgentFlow contract audit report example:
  - `examples/agentflow/contract_audit_report.example.json`
- Added focused audit tests in `tests/test_agentflow_contract_audit.py` so the audit report must cover registry contracts, keep docs/examples marked present, preserve `schema_version: 0.1.0`, record boundary checks, and avoid claiming runtime validation.
- Added `docs/agentflow_contract_validation.md` and updated docs navigation, architecture, registry docs, roadmap, and DEVLOG.
- Verification:
  - `.venv\Scripts\python.exe -m pytest tests/test_agentflow_contract_audit.py`: 5 passed
  - `.venv\Scripts\python.exe -m pytest tests/test_contract_examples.py`: 16 passed
  - `.venv\Scripts\python.exe -m pytest`: 357 passed
  - `.venv\Scripts\python.exe -m compileall apps narratocut narratostudio tests`: passed
  - `git diff --check`: passed with CRLF warnings only
  - `.venv\Scripts\python.exe -m apps.cli.main --help`: passed
  - `.venv\Scripts\python.exe -m apps.cli.main version`: `0.1.0`
- Boundary kept: no workflow, CLI, Python runtime, runtime validator, registry service, Router runtime, skill runtime, Memory runtime, database, cross-module execution, Web UI, or remote provider behavior changed.

## 2026-05-21 - Phase 15.6 AgentFlow Contract Registry

- Synced local `master` to merged PR #45 at `fcd8127` and started `codex/agentflow-contract-registry` from a clean mainline.
- Added a minimal AgentFlow contract registry example:
  - `examples/agentflow/contract_registry.example.json`
- Extended contract example tests so the registry must use `schema_version: 0.1.0`, declare `artifact_type: agentflow_contract_registry`, stay `contract_discovery` scoped, point to committed examples and docs, match indexed `artifact_type` values, and declare validation rules without runtime execution.
- Added `docs/agentflow_contract_registry.md` and updated AgentFlow architecture, artifact map, docs navigation, and roadmap so the registry is discoverable as a local contract index.
- Verification:
  - `.venv\Scripts\python.exe -m pytest tests/test_contract_examples.py`: 16 passed
  - `.venv\Scripts\python.exe -m pytest`: 352 passed
  - `.venv\Scripts\python.exe -m compileall apps narratocut narratostudio tests`: passed
  - `git diff --check`: passed with CRLF warnings only
  - `.venv\Scripts\python.exe -m apps.cli.main --help`: passed
  - `.venv\Scripts\python.exe -m apps.cli.main version`: `0.1.0`
- Boundary kept: no workflow, CLI, Python runtime, Pydantic schema package, registry service, Router runtime, skill runtime, Memory runtime, database, cross-module execution, Web UI, or remote provider behavior changed.

## 2026-05-21 - Phase 15.5 AgentFlow Skill / Router Contracts

- Synced local `master` to merged PR #44 at `2ce4b52` and started `codex/agentflow-skill-router-contracts` from a clean mainline.
- Added minimal AgentFlow skill and Router examples:
  - `examples/agentflow/skill_invocation.example.json`
  - `examples/agentflow/skill_result.example.json`
  - `examples/agentflow/router_decision.example.json`
- Extended contract example tests so the new examples must use `schema_version: 0.1.0`, declare the correct `artifact_type`, keep Router decisions as `decision_only`, include rejected candidate skill reasons, and avoid private paths, secrets, generated media, or local run artifacts.
- Updated AgentFlow docs so:
  - skill invocation is a planned call artifact, not execution proof
  - skill result is an output and quality-gate summary, not a runtime implementation
  - Router decision is an auditable selection record and does not execute skills
  - Phase 15.4 is marked complete and Phase 15.5 is scoped to docs/examples/tests only
- Verification:
  - `.venv\Scripts\python.exe -m pytest tests/test_contract_examples.py`: 13 passed
  - `.venv\Scripts\python.exe -m pytest`: 349 passed
  - `.venv\Scripts\python.exe -m compileall apps narratocut narratostudio tests`: passed
  - `git diff --check`: passed with CRLF warnings only
  - `.venv\Scripts\python.exe -m apps.cli.main --help`: passed
  - `.venv\Scripts\python.exe -m apps.cli.main version`: `0.1.0`
- Boundary kept: no workflow, CLI, Python runtime, Pydantic schema package, Router runtime, skill runtime, permission system, cross-module execution, Web UI, or remote provider behavior changed.

## 2026-05-21 - Phase 15.4 AgentFlow Memory Signal Contracts

- Synced local `master` to merged PR #43 at `2f7feaa` and started `codex/agentflow-memory-signal-contracts` from a clean mainline.
- Added minimal AgentFlow memory signal examples:
  - `examples/agentflow/memory_candidate.example.json`
  - `examples/agentflow/memory_promotion_decision.example.json`
- Extended contract example tests so AgentFlow memory examples must use `schema_version: 0.1.0`, keep memory candidates as `promotion_status: candidate`, and make promotion decisions explicit human-reviewed artifacts that do not write long-term memory.
- Updated memory and NarratoStudio docs to keep the boundaries clear:
  - `feedback.jsonl` remains the raw feedback source of truth.
  - `feedback_signal_log.json` is derived run interpretation only.
  - `memory_candidates.json` is candidate-only and not durable memory.
  - `cost_quality_trace.json` is execution strategy evidence, not a creative quality guarantee.
- Verification:
  - `.venv\Scripts\python.exe -m pytest tests/test_contract_examples.py`: 9 passed
  - `.venv\Scripts\python.exe -m pytest`: 345 passed
  - `.venv\Scripts\python.exe -m compileall apps narratocut narratostudio tests`: passed
  - `git diff --check`: passed with CRLF warnings only
  - `.venv\Scripts\python.exe -m apps.cli.main --help`: passed
  - `.venv\Scripts\python.exe -m apps.cli.main version`: `0.1.0`
- Boundary kept: no workflow, CLI, database, vector store, Router runtime, Memory runtime, skill runtime, Web UI, or remote provider behavior changed.

## 2026-05-21 - Phase 15.3 NarratoStudio Review Hardening

- Synced local `master` to merged PR #42 at `8e1aff0` and started `codex/narratostudio-review-hardening` from a clean mainline.
- Added focused regression tests for NarratoStudio review failures when:
  - a scene references a missing outline beat
  - an outline beat has no scene coverage
  - a scene has no shot coverage
  - a shot has no prompt coverage
  - `production_handoff.json` core artifact IDs drift from upstream artifacts
  - `production_handoff.json` misses a required artifact reference
  - `production_report.md` loses basic NarratoStudio handoff identity markers
- Hardened `narratostudio_production_handoff` quality checks for the JSON artifact chain:
  `episode_outline.json -> scene_plan.json -> shot_plan.json -> prompt_pack.json -> production_handoff.json`.
- Kept `production_report.md` as a human-readable review surface only. The harness checks its presence and lightweight identity, but strong consistency remains in JSON artifacts and `production_handoff.json`.
- Verification:
  - `.venv\Scripts\python.exe -m pytest tests/test_narratostudio_review_hardening.py tests/test_narratostudio_workflow.py tests/test_narratostudio_schemas.py`: 19 passed
  - `.venv\Scripts\python.exe -m pytest`: 343 passed
  - `.venv\Scripts\python.exe -m compileall apps narratocut narratostudio tests`: passed
  - `git diff --check`: passed with CRLF warnings only
  - `.venv\Scripts\python.exe -m apps.cli.main --help`: passed
  - `.venv\Scripts\python.exe -m apps.cli.main version`: `0.1.0`
  - NarratoStudio smoke run: workflow success, inspect `65 passed / 0 failed / 0 warnings`, review `83 passed / 0 failed / 0 warnings`
- Boundary kept: no workflow generation logic, CLI, package name, Router runtime, Memory runtime, skill runtime, Web UI, database, or remote provider behavior changed.

## 2026-05-20 - NarratoCut v0.1.0 Delivery Closeout

- Synced `master` to PR #38, confirmed the old delivery-hardening branch had an
  identical tree to `origin/master`, deleted the stale remote branch, and
  started `codex/phase-1-v0-1-delivery-closeout`.
- Repositioned NarratoCut as the distribution-side short video highlight
  workflow module of AgentFlow Studio while keeping the repo and local folder
  named `NarratoCut`.
- Extended `run_manifest.json` with an additive `artifact_index` while keeping
  the existing `artifacts` string map backward-compatible for current tests,
  reviewers, and workflows.
- Extended `review_report.json` with `quality_level` and `delivery_status` so
  agents and future UI code can read handoff state without inferring it only
  from raw check counts.
- Added v0.1.0 delivery docs: agent usage guide, delivery checklist, golden
  sample path, project manifest contract, feedback contract, platform profile
  contract, and asset lifecycle.
- Added contract examples with `schema_version`: project manifest JSON,
  feedback JSONL, and Douyin/Xiaohongshu/YouTube Shorts platform profiles.
- Boundary kept: no Web UI, no NarratoStudio, no Router runtime, no Memory
  runtime, and no claim that deterministic highlight scoring is editorially
  mature.

## 2026-05-20 - Phase 14.5 Selection Diagnostics

- Started `feature/phase-14-5-selection-diagnostics` from the merged Phase
  14.4E `master` after syncing `origin/master` and deleting the merged
  Phase 14.4E branch locally and remotely.
- Added `selection_diagnostics.json` generation from the existing
  `highlight_score_report.json` state. The diagnostic artifact summarizes
  selected score range, top rejected candidates, near misses, rejection reason
  counts, source-time distribution, boundary strategy distribution, and warning
  signals such as clustered selection, duplicate-source-window pressure, weak
  hook evidence, and near-miss rejected candidates.
- Added workflow node `write_selection_diagnostics` and inserted it after
  `write_highlight_score_report` in ASR-first finished-package workflows and
  the OCR-subtitle candidate scoring workflow.
- Updated `package_report.md` so finished-package reports include a compact
  Selection Diagnostics section alongside selected clips and rejected
  candidates.
- Extended the candidate scoring harness to require and validate
  `selection_diagnostics.json` for candidate-scoring runs.
- Updated workflow docs, workspace/tool contracts, tool catalog, and agent
  skill output contracts so agents can read diagnostics before deciding whether
  to rerun, review manually, or tune candidate settings.
- Boundary kept: diagnostics are read-only over existing scores. This phase
  does not change scoring weights, selected highlights, clip boundaries, media
  execution, ASR/OCR providers, or Web UI behavior.

## 2026-05-19 - Phase 14.2A Candidate Windows

- Started `feature/phase-14-2a-candidate-windows` from the merged local-ASR
  product acceptance `master`.
- Added `narratocut.candidate_sop.generate_candidate_windows` to expand a
  timestamped transcript into adjacent 1..N segment windows and record the
  transcript content channel for future ASR/OCR/fused transcript inputs.
- Added the `generate_candidate_windows` workflow node and
  `workflows/transcript_to_candidate_windows.yaml`, producing
  `candidate_windows.json` without scoring, highlight selection, FFmpeg,
  remote models, or video-frame inspection.
- Added a demo input and focused tests for window generation, duration bounds,
  node artifact writing, workflow loading, and static plan drafting.
- Added a `candidate_windows` inspect/review quality profile so
  `inspect-run` and `review-run` validate `candidate_windows.json` directly
  instead of falling back to the legacy mock hooks/scripts/clips checks.
- Updated the static tool catalog, tool contracts, README, and workflow docs so
  `candidate_windows.json` is a formal Phase 14.2A artifact for later viral
  scoring.
- Updated the viral quality plan after route review: keep Phase 14.2A narrow,
  prioritize Subtitle OCR Timeline next, then add ASR/OCR candidate fusion and
  scoring.
- Boundary kept: Phase 14.2A only generates candidate windows. Viral scoring,
  selected/rejected reasons, package reports, Web UI, and multimodal detection
  remain future work.

## 2026-05-19 - Phase 14.0B Product Quality Smoke Reclassification

- Started `feature/phase-14-0b-product-quality-smoke` from the merged Phase
  14.0 documentation `master`.
- Reclassified the Phase 13 Golden Path as an engineering smoke, not a
  product-quality acceptance run.
- Added optional `evidence` paths to `finished_package_manifest.json` so package
  review can inspect upstream artifacts such as `final_video_manifest.json`,
  `real_slice_manifest.json`, `clip_plan.json`, `subtitle_manifest.json`, and
  `audio_mix_manifest.json`.
- Added finished-package product-quality warnings for single-clip demo cuts,
  `0s`-only starts, missing highlight evidence, missing subtitle source-video
  binding, subtitle duration exceeding the primary video, and unverified BGM
  content fit.
- Updated the Golden Path docs and package example so the next product test can
  surface engineering success separately from product-quality warnings.
- Added `docs/product_quality_smoke.md` with the current expected warning set
  and the local Phase 14.0B baseline:
  `inspect-run` reports `11 passed / 0 failed / 6 warnings`, while
  `review-run` reports `17 passed / 0 failed / 7 warnings`.

## 2026-05-19 - Phase 14.0 Documentation and Golden Path Prep

- Started `feature/phase-14-0-docs-golden-path` from the Phase 13 complete
  `master`.
- Refreshed `README.md` and `README.zh-CN.md` to position NarratoCut as a
  CLI-first technical MVP with real final-video, subtitle, cover, BGM, package,
  inspect, and review capabilities.
- Replaced the stale Phase 13 Web UI roadmap with a Phase 14 Productization
  roadmap.
- Added `docs/current_architecture.md` to summarize the post-Phase-13
  architecture and artifact model.
- Added `docs/golden_path.md` to define the local Phase 13 complete product
  smoke from source video and ClipPlan to `finished_package_manifest.json`.
- Ran the Phase 13 complete Golden Path with local ignored media:
  `clip_plan_to_real_clips`, `clips_to_final_video`, `transcript_to_subtitles`,
  `final_video_with_subtitles`, `final_video_to_cover`,
  `final_video_with_bgm`, and `final_video_package`.
- Recorded the smoke result in `docs/product_smoke_phase13.md`: all seven
  workflows succeeded, and every inspect/review report showed `0 failed` and
  `0 warnings`.
- Generated real product artifacts under ignored
  `data/processed/runs/golden_path_phase13_*` directories, including
  `final_video.mp4`, `subtitles.srt`, `final_video_with_subtitles.mp4`,
  `cover.jpg`, `final_video_with_bgm.mp4`, and
  `finished_package_manifest.json`.
- Kept generated media and smoke outputs under ignored `data/` paths.

## 2026-05-19 - Phase 13.7 Finished Video Package Manifest

- Started `feature/phase-13-7-finished-video-package` from the merged Phase
  13.6 `master`.
- Added `workflows/final_video_package.yaml` as a narrow manifest-only
  workflow: existing final video artifacts -> `finished_package_manifest.json`.
- Added `narratocut/package_sop/` and `write_finished_package` workflow node to
  index the required final video plus optional subtitle-burned video,
  BGM-mixed video, cover image, and review report paths.
- Added `finished_package` inspect/review support so declared package assets
  are checked for manifest status and file existence.
- Added example input under `examples/demo_package/` that references ignored
  generated artifacts and does not commit real media.
- Kept this increment free of file copying, uploads, final assembly changes,
  subtitle burn-in, BGM mixing, cover export, remote providers, and Web UI.

## 2026-05-19 - Phase 13.6 BGM Mix Hardening

- Started `feature/phase-13-6-bgm-hardening` from the merged Phase 13.5
  `master`.
- Hardened `BGMMixConfig` so `bgm_volume` and `original_audio_volume` must stay
  between `0` and `1`.
- Added a `mix_strategy` option. The default remains `mix_with_original`, while
  `bgm_only` builds a BGM-only audio filter path for silent final videos.
- Added BGM inspect/review warnings for known FFmpeg stderr patterns such as
  `Non-monotonic DTS` and for output duration drift beyond the BGM tolerance.
- Split BGM review tests into a separate focused test file so the main workflow
  test file stays under the 300-line project preference.
- Kept this increment free of music libraries, licensing management, beat
  detection, fades, transitions, final-video assembly changes, subtitles,
  covers, remote providers, and Web UI.

## 2026-05-19 - Phase 13.5 Local BGM Mix

- Started `feature/phase-13-5-bgm-mix` from the merged Phase 13.4 `master`.
- Added `workflows/final_video_with_bgm.yaml` as a narrow local BGM mix
  workflow: existing `final_video.mp4` plus local `bgm.mp3` ->
  `final_video_with_bgm.mp4` and `audio_mix_manifest.json`.
- Added `narratocut/bgm_sop/` for FFmpeg BGM mix command construction,
  execution, failed-manifest writing, volume configuration, and output-name
  safety.
- Added `bgm_mix` inspect/review support so BGM runs are checked for manifest
  status, FFmpeg command/return code, safe relative output paths, output video
  presence, non-empty output size, and video stream presence when FFprobe is
  available.
- Added example input under `examples/demo_bgm/` that references ignored local
  media paths and does not commit real video or music assets.
- Kept this increment free of music libraries, licensing management, beat
  detection, fades, transitions, final-video assembly changes, subtitles,
  covers, remote providers, and Web UI.

## 2026-05-19 - Phase 13.4 Cover Export

- Started `feature/phase-13-4-cover-export` from the merged Phase 13.3
  `master`.
- Added `workflows/final_video_to_cover.yaml` as a narrow cover export
  workflow: existing `final_video.mp4` -> `cover.jpg` plus
  `cover_manifest.json`.
- Added `narratocut/cover_sop/` for FFmpeg single-frame command construction,
  execution, failed-manifest writing, cover timestamp selection, and output-name
  safety.
- Added `cover_export` inspect/review support so cover runs are checked for
  manifest status, FFmpeg command/return code, safe relative output paths,
  cover image presence, and non-empty output size.
- Added example input under `examples/demo_cover/` that references an ignored
  generated final-video path and does not commit real media.
- Kept this increment free of BGM, transitions, subtitle changes, final-video
  assembly changes, cover templates, text overlays, remote providers, video
  frame highlight selection, and Web UI.

## 2026-05-19 - Phase 13.3 Subtitle Burn-In

- Started `feature/phase-13-3-subtitle-burn-in` from the merged Phase 13.2
  `master`.
- Added `workflows/final_video_with_subtitles.yaml` as a narrow execution
  workflow: existing `final_video.mp4` plus existing `subtitles.srt` ->
  `final_video_with_subtitles.mp4` and `subtitle_burn_manifest.json`.
- Added `narratocut/subtitle_burn_sop/` for FFmpeg subtitle burn-in command
  construction, execution, failed-manifest writing, and output-name safety.
- Added `subtitle_burn` inspect/review support so subtitle-burn runs are
  checked for manifest status, FFmpeg command/return code, output video
  presence, non-empty output size, FFmpeg warning classification, and video
  stream presence when FFprobe is available.
- Added example input under `examples/demo_subtitles/` with a committed small
  `.srt` fixture and an ignored generated final-video path.
- Fixed workflow input bundle loading for UTF-8 BOM JSON files so PowerShell
  generated input bundles are parsed as structured workflow inputs instead of
  falling back to legacy `input_text_file` mode.
- Kept this increment free of subtitle generation, final-video assembly
  regeneration, slicing, BGM, covers, transitions, Web UI, remote providers,
  ASR behavior, and video-frame understanding.

## 2026-05-19 - Phase 13.2 Basic Subtitle Export

- Started `feature/phase-13-2-basic-subtitle-export` from the merged Phase
  13.1 `master`.
- Added `workflows/transcript_to_subtitles.yaml` as a narrow subtitle export
  workflow: timestamped `transcript.json` -> `subtitles.srt` plus
  `subtitle_manifest.json`.
- Added `narratocut/subtitle_sop/` for deterministic SRT formatting and
  subtitle manifest generation without FFmpeg, media re-encoding, or remote
  providers.
- Added the `subtitle_export` inspect/review profile so subtitle runs are
  checked for manifest status, subtitle file existence, cue count alignment,
  valid cue ranges, monotonic cue ordering, and non-empty text.
- Added example input under `examples/demo_subtitles/` with a committed text
  transcript fixture and no media dependency.
- Kept this increment free of subtitle burn-in, final-video regeneration, BGM,
  covers, transitions, Web UI, real ASR behavior, visual understanding, and
  remote provider calls.

## 2026-05-19 - Phase 13.1 Final Video Quality Hardening

- Started `feature/phase-13-1-final-video-quality-hardening` from the Phase
  12 completion point at `8347e30`.
- Hardened final-video inspection without changing assembly behavior:
  `final_video_manifest.json` remains the source of truth for generated output
  paths, and FFmpeg concat output is not regenerated differently.
- Added known FFmpeg stderr warning classification for final-video runs.
  `Non-monotonic DTS` is reported as a quality warning rather than a hard
  failure when FFmpeg exits successfully and FFprobe can read the output.
- Added final-video stream presence checking so a missing video stream is
  surfaced as a failed quality check.
- Made `review-run` clearer when `quality_report.json` is missing by telling
  users to run `inspect-run` before `review-run`.

## 2026-05-19 - Phase 12.2 Simple Video Assembly

- Added `workflows/clips_to_final_video.yaml` as the Phase 12 simple assembly
  workflow: existing `real_slice_manifest.json` plus `clips/` -> assembly plan
  -> FFmpeg concat -> `final_video.mp4` and `final_video_manifest.json`.
- Added `narratocut/assembly_sop/` for assembly-specific plan and concat logic
  so slicing remains separate from final-video assembly.
- Added `final_video` harness quality/review support for assembly artifacts,
  including final manifest status, final video existence, non-empty file size,
  and duration tolerance when FFprobe is available.
- Added an example input under `examples/demo_assembly/` that references an
  ignored generated run path rather than committing media.
- Kept this increment free of subtitles, BGM, transitions, covers, Web UI,
  remote providers, video-frame understanding, and new ASR behavior.

## 2026-05-19 - Phase 12.1B Video To Real Clips Composition

- Synced `master` to the merged Phase 12.1A PR and started
  `feature/phase-12-1b-video-to-real-clips`.
- Added `workflows/video_to_real_clips.yaml` as a composition smoke workflow
  that reuses the Phase 11 mock-ASR planning path and then executes the
  generated `clip_plan.json` through Phase 12.1 real slicing.
- Added the `video_real_clips` harness profile so `inspect-run` and
  `review-run` cover video/transcript artifacts, highlight/clip-plan artifacts,
  and real clip slicing artifacts in one run.
- Split real-clip quality checks into `narratocut/harness/real_clip_quality.py`
  and shared profile constants into `quality_profiles.py` so the generic
  quality entrypoint stays thin as Phase 12 adds execution-layer checks.
- Added `examples/demo_asr/video_to_real_clips_input.example.json` using mock
  ASR and the existing ignored local demo video path.
- Kept this increment free of real ASR, video-frame highlight detection, clip
  concatenation, subtitles, BGM, covers, Web UI, remote providers, and
  `final_video.mp4` export.

## 2026-05-19 - Phase 12.1 ClipPlan To Real Clips

- Added `workflows/clip_plan_to_real_clips.yaml` as the Phase 12.1 primary
  execution workflow: source video plus existing `clip_plan.json` -> metadata
  probe -> validation -> real slicing -> `real_slice_manifest.json` and
  `clips/`.
- Kept this phase scoped to ClipPlan execution. It does not run ASR, detect
  highlights, regenerate clip plans, concatenate clips, add subtitles, add BGM,
  create covers, call remote providers, or export `final_video.mp4`.
- Added `examples/demo_slicing/clip_plan_to_real_clips_input.example.json` and
  a small `clip_plan.example.json`; the example references an ignored local
  video path and does not commit real media.
- Extended the real clip inspection/review path with a `real_clips` profile
  that reuses the existing real-video artifact checks without requiring
  transcript, highlight, or audio artifacts.
- Enriched `real_slice_manifest.json` with source video, clip plan path, clips
  directory, FFmpeg command, return code, stdout, and stderr so later assembly
  phases can inspect the execution result.
- Deferred `video_to_real_clips.yaml` to Phase 12.1B unless a follow-up needs a
  separate composition smoke workflow.

## 2026-05-18 - Phase 11.7 Video Artifact Review Hardening

- Started `feature/phase-11-7-video-artifact-review` from the merged Phase
  11.6 `master` after syncing the branch and deleting the completed Phase 11.6
  branch locally and on `origin`.
- Added Phase 11 video artifact harness profiles for `mock_asr_transcript`,
  `real_asr_transcript`, `video_highlight_clip_plan`, and
  `real_asr_highlight_clip_plan`.
- `inspect-run` now recognizes Phase 11 audio/transcript artifacts and writes
  summaries for audio extraction status, transcript provider, segment count,
  timestamp validity, monotonic segment order, and text presence.
- `review-run` now adds a `video_artifacts` section for Phase 11 profiles,
  including audio manifest checks, Transcript schema checks, ASR provider
  metadata checks, source-segment alignment checks for video-to-highlight runs,
  and obvious API secret value leakage checks for explicit real-ASR runs.
- Video-to-highlight runs still include the existing `highlight_artifacts`
  section, so HighlightPlan and ClipPlan review remains shared with Phase 10.
- Kept this increment free of new workflows, new product CLI commands, real
  slicing, final assembly, subtitles, BGM, Web UI, video-frame highlight
  detection, and default remote ASR calls.

## 2026-05-18 - Phase 11.6 Real-ASR Video-to-ClipPlan Workflow

- Synced local `master` to the merged Phase 11.5 PR and deleted the completed
  `feature/phase-11-5-real-asr-workflow` branch locally and on `origin`.
- Started `feature/phase-11-6-real-asr-highlight-clip-plan` from the latest
  `master`.
- Added `workflows/video_to_highlight_clip_plan_real_asr.yaml`, which composes
  explicit OpenAI-compatible ASR with the Phase 10 deterministic highlight
  detection, ROI ranking, and ClipPlan generation path.
- Added an example input bundle under `examples/demo_asr/` that references an
  API-key environment variable name without committing secrets.
- Kept this increment free of video-frame highlight detection, real slicing,
  clip generation, final assembly, subtitles, BGM, Web UI, and new product CLI
  commands.

## 2026-05-18 - Phase 11.5 Explicit Real-ASR Workflow

- Synced local `master` to the merged Phase 11.3/11.4 PR and deleted the
  completed `feature/phase-11-3-4-audio-asr-providers` branch locally and on
  `origin`.
- Started `feature/phase-11-5-real-asr-workflow` from the latest `master`.
- Added workflow node `transcribe_audio_openai_compatible`, which wires the
  optional OpenAI-compatible ASR provider into the workflow engine.
- Added `workflows/video_to_transcript_real_asr.yaml` as an explicit remote-ASR
  path that stops at `transcript.json`.
- Added an example input bundle that uses an API-key environment variable name
  rather than committing any secret.
- Kept default demo workflows on mock ASR and kept this increment free of
  highlight detection, ClipPlan generation, real slicing, final assembly,
  subtitles, BGM, Web UI, and new product CLI commands.

## 2026-05-18 - Phase 11.3/11.4 Audio Extraction and ASR Provider Contracts

- Started `feature/phase-11-3-4-audio-asr-providers` from the merged Phase 11.2
  `master`.
- Strengthened real FFmpeg audio extraction artifacts so `audio_manifest.json`
  records execution status, command arguments, return code, stdout, and stderr.
- Kept mock extraction available and explicitly marked as not executing FFmpeg.
- Added an optional `OpenAICompatibleASRProvider` adapter behind
  `NARRATOCUT_ALLOW_REMOTE_ASR=true`.
- Kept default workflows on fixture-backed mock ASR; no workflow now calls a
  remote ASR provider by default.
- Kept this increment free of video-frame highlight detection, real slicing,
  final assembly, subtitles, BGM, Web UI, and new product CLI commands.

## 2026-05-18 - Phase 11.2 Mock ASR Video-to-ClipPlan Workflow

- Synced local `master` to the merged Phase 11.1 PR and deleted the completed
  `feature/phase-11-video-to-transcript` branch locally and on `origin`.
- Started `feature/phase-11-2-video-to-highlight-clip-plan` from the latest
  `master`.
- Added `workflows/video_to_highlight_clip_plan.yaml`, which composes the
  Phase 11.1 mock-ASR transcript workflow with the Phase 10 deterministic
  highlight detection, ROI ranking, and highlight-to-ClipPlan generation path.
- Added a demo input bundle under `examples/demo_asr/` for the composed
  video-to-highlight-clip-plan workflow.
- Kept this increment free of real ASR providers, video-frame highlight
  detection, FFmpeg slicing, real clip generation, final-video assembly,
  subtitles, BGM, Web UI, and new product CLI commands.

## 2026-05-18 - Phase 11.1 Video-to-Transcript Foundation

- Synced local `master` to the merged Phase 10.7 PR and deleted the completed
  `feature/phase-10-7-highlight-artifact-review` branch locally and on
  `origin`.
- Started `feature/phase-11-video-to-transcript` from the latest `master`.
- Added `narratocut.audio_sop` for the video-to-audio artifact contract,
  including FFmpeg command construction and deterministic mock extraction for
  tests and offline workflow smoke runs.
- Added `narratocut.asr_sop` with an adapter protocol, fixture-backed
  `MockASRProvider`, and transcript normalization into the existing
  `Transcript` schema.
- Added `workflows/video_to_transcript.yaml`, which runs
  `load_video -> extract_audio -> transcribe_audio_mock -> write_transcript`.
- Added `examples/demo_asr/` with a mock ASR transcript fixture and workflow
  input bundle.
- Kept this increment free of video-frame highlight detection, Phase 10
  highlight workflows, ClipPlan generation, FFmpeg slicing, real ASR providers,
  remote LLM calls, clip assembly, subtitles, BGM, Web UI, and new product CLI
  commands.

## 2026-05-18 - Phase 10.7 Highlight Artifact Review

- Synced local `master` to the merged Phase 10 PR and deleted the completed
  `feature/phase-10-highlight-detection` branch locally and on `origin`.
- Started `feature/phase-10-7-highlight-artifact-review` from the latest
  `master`.
- Added a highlight artifact harness profile for `highlight_plan` and
  `highlight_clip_plan` quality profiles.
- `inspect-run` now reports Phase 10 artifact summaries for
  `highlight_plan.json`, including input mode, highlight count, highlight type
  distribution, timestamp presence, ranking factor presence, and score ranges.
- `review-run` now adds a `highlight_artifacts` section that checks
  script-only timestamp boundaries, timestamped transcript ranges, ranking
  factors, highlight IDs, source segment IDs, clip segment metadata, and
  highlight-to-clip ordering.
- Kept this increment free of new workflow nodes, new CLI commands, ASR,
  raw-video analysis, FFmpeg execution, LLM calls, clip assembly, subtitles,
  BGM, and Web UI.

## 2026-05-18 - Phase 10.1/10.2 Highlight Contracts

- Started Phase 10 on `feature/phase-10-highlight-detection` after Phase 9
  was merged into `master`.
- Added `HighlightSegment` and `HighlightPlan` contracts for `script_only`
  and `timestamped_transcript` highlight planning.
- Added `TranscriptSegment` and `Transcript` contracts for externally
  supplied timestamped transcript input. Phase 10 consumes transcripts; it does
  not generate them through ASR.
- Enforced the key Phase 10 boundary: `script_only` highlight plans must not
  carry timestamps, while `timestamped_transcript` plans require timestamps on
  every highlight.
- Added `examples/demo_highlight/` input examples for script-only and
  timestamped-transcript workflows, plus a reusable ROI config.
- Kept this increment free of detector logic, ROI ranking, ClipPlan generation,
  workflow nodes, CLI commands, remote LLM calls, ASR, Web UI, subtitles, BGM,
  and final-video assembly.

## 2026-05-18 - Phase 10.3 Deterministic Highlight Detector

- Added `narratocut.highlight_sop` as the local highlight-detection module.
- Added `DeterministicHighlightDetector` plus convenience functions for
  script-only and timestamped-transcript inputs.
- The detector is a stable, offline baseline. It uses simple rules for hook,
  conflict, insight, and CTA candidates; it does not call the model gateway,
  remote LLMs, ASR, OCR, FFmpeg, or any network service.
- Script-only detection writes untimed `HighlightPlan` objects. Timestamped
  transcript detection preserves `TranscriptSegment` time ranges and source
  segment IDs.
- Kept ROI ranking, ClipPlan generation, workflow nodes, CLI commands, and
  real slicing integration out of Phase 10.3. Those remain later Phase 10
  increments.

## 2026-05-18 - Phase 10.4 ROI-aware Highlight Ranking

- Added `ROIHighlightRanker` and `rank_highlights_by_roi(...)` under
  `narratocut.highlight_sop`.
- Ranking returns a new `HighlightPlan` instead of mutating detector output,
  so later workflows can keep raw and ranked plans separate.
- Added transparent local ranking factors under
  `highlight.metadata.ranking_factors`, including base score, confidence,
  content goal, target platform, priority boosts, matched rules, and
  `final_score`.
- Kept `highlight.score` as the detector score. ROI ranking uses
  `metadata.ranking_factors.final_score` for ordering.
- Added user-facing ROI tags such as `goal:*`, `platform:*`, and
  `priority:*` without discarding detector-provided tags.
- Kept this increment free of performance prediction, virality prediction,
  ClipPlan generation, workflow nodes, CLI commands, remote LLM calls, ASR, and
  final-video assembly.

## 2026-05-18 - Phase 10.5 Highlight-to-ClipPlan Generation

- Added `HighlightClipPlanGenerator` and
  `generate_clip_plan_from_highlights(...)` under `narratocut.highlight_sop`.
- The generator accepts only `timestamped_transcript` `HighlightPlan` objects
  and rejects `script_only` plans instead of inventing timestamps.
- Generated one executable `ClipPlan` with one `ClipSegment` per selected
  highlight, preserving the incoming ranked order.
- Required caller-provided `source_video` for generated segments so the output
  can enter Phase 9 validation and real slicing when the caller supplies a real
  video path.
- Preserved highlight evidence in segment metadata, including highlight ID,
  type, score, confidence, ROI tags, source transcript segment IDs, and ranking
  factors.
- Kept this increment free of FFmpeg execution, workflow nodes, CLI commands,
  ASR, remote LLM calls, clip assembly, subtitles, BGM, and final-video export.

## 2026-05-18 - Phase 10.6 Highlight Workflow Integration

- Added highlight workflow nodes for loading scripts/transcripts, detecting
  highlights, ROI ranking, generating ClipPlan from timestamped highlights, and
  writing highlight/clip plan artifacts.
- Added `workflows/script_to_highlight_plan.yaml`, which writes a ranked
  `highlight_plan.json` and intentionally does not write `clip_plan.json`.
- Added `workflows/transcript_to_highlight_clip_plan.yaml`, which writes a
  ranked `highlight_plan.json` plus executable `clip_plan.json`.
- Kept Phase 10.6 on the existing `ncut run-workflow` path instead of adding a
  product-specific CLI command.
- Updated highlight examples with `max_highlights` and an optional
  `source_video` placeholder for transcript-driven clip plan generation.
- Kept this increment free of ASR, raw-video highlight detection, FFmpeg
  execution, clip assembly, subtitles, BGM, Web UI, and final-video export.

## 2026-05-18 - Phase 9 ROI-aware Real Video Workflow Closure

- Phase 9 establishes the real video execution foundation: it runs a provided
  `ClipPlan` against a local video and produces inspectable/reviewable
  artifacts. It intentionally does not include automatic highlight detection,
  ASR, clip assembly, subtitles, BGM, Web UI, or agent runtime.
- Added a real-video workflow mode with explicit `workflow_mode` and
  `quality_profile` fields in `run_manifest.json`.
- Added `ROISettings`, `VideoMetadata`, and `ClipPlanValidationReport`
  contracts for one local video, one ROI config, one `ClipPlan`, and many
  segments.
- Added FFmpeg/FFprobe path resolution through CLI/env/config and structured
  `ncut ffmpeg-check --json` output.
- Added `workflows/real_video_roi_to_clips.yaml` plus example input JSON files
  under `examples/demo_real_video/` without committing real media.
- Kept `run-workflow`, `inspect-run`, and `review-run` separated:
  `run-workflow` writes execution artifacts, `inspect-run` writes
  `quality_report.json`, and `review-run` writes `review_report.json`.
- Added real-video inspection and review recommendations for FFmpeg/FFprobe,
  validation, and slicing failures.
- Extended the static tool catalog with implemented Phase 9 real-video nodes
  and added optional FFprobe-based clip duration tolerance checks.
- Honored the structured input bundle's relative `output.clips_dir` while
  keeping `clips` as the default output folder.
- Validated the real-video success path with a local ignored demo mp4:
  FFmpeg/FFprobe were ready, `real_slice_manifest.json` reported one succeeded
  10-second clip, `inspect-run` reported `11 passed / 0 failed / 0 warnings`,
  and `review-run` reported `16 passed / 0 failed / 0 warnings`.
- Follow-up direction: Phase 10 should address script/timestamped transcript
  highlight detection, Phase 11 should add video ASR to timestamped transcript,
  and Phase 12 should assemble clips into a final video.

## 2026-05-16 - Phase 4 Model Gateway Lite

- Added a lightweight model gateway layer with config loading, provider errors, `ModelGateway`, and a minimal OpenAI-compatible provider.
- Kept existing ROI and workflow commands on the default mock path; no CLI command requires API keys or network access.
- Added `NARRATOCUT_ALLOW_REMOTE_LLM=true` as an explicit provider-side guard before OpenAI-compatible HTTP calls.
- Updated example model and environment configuration without storing secrets.
- Verification: `pytest` passed with 37 tests, `compileall` passed, and the mock CLI/workflow commands still generated local ignored artifacts under `data/processed/runs/`.

## 2026-05-16 - Phase 5 ClipPlan + Slicing MVP

- Added deterministic `ShortVideoScript -> ClipPlan` planning and mock slicing that writes `.txt` placeholder clips plus `slice_manifest.json`.
- Kept Phase 5 free of FFmpeg, real media reads, real `.mp4` generation, network calls, Web/API, database, queues, and complex workflow DAGs.
- Added CLI commands `generate-clip-plans` and `mock-slice`; CLI remains a thin wrapper over `narratocut.slicing_sop`.
- Verification: `pytest` passed with 41 tests, `compileall` passed, and the Phase 5 CLI chain generated `clip_plans.json`, `slice_manifest.json`, and 3 ignored mock clip files under `data/processed/runs/demo_phase5/`.

## 2026-05-16 - Phase 6 Workflow Full Mock Pipeline

- Added workflow nodes `generate_clip_plans` and `mock_slice`, reusing the Phase 5 slicing SOP without FFmpeg or real media access.
- Added `workflows/mock_text_to_slices.yaml` for the full mock chain: text -> hooks -> scripts -> clip_plans -> mock clips.
- Updated workflow docs with the full mock run command and expected artifacts.
- Verification: full mock workflow test passed and CLI run generated `hooks.json`, `scripts.json`, `clip_plans.json`, `slice_manifest.json`, and 3 ignored `.txt` mock clip files.

## 2026-05-16 - Phase 7 Real Slicing Design + FFmpeg Probe

- Added `ffmpeg_probe` for structured FFmpeg availability checks without requiring FFmpeg during tests.
- Added `real_slicer` command-contract helpers that build, but do not execute, minimal FFmpeg slice commands.
- Added `ffmpeg-check` CLI as an informational local probe; it does not alter mock workflows or require real video assets.
- Added real slicing design notes documenting the current mock boundary and future FFmpeg input/output contract.

## 2026-05-17 - Phase 7.5 Run Contract + Harness Inspection Baseline

- Added standardized run contract artifacts for workflow runs: `run_manifest.json` and `trace.json`.
- Added harness quality checks and run inspection that write `quality_report.json` without moving quality decisions into workflow nodes.
- Added `ncut inspect-run --run-dir ...` to inspect generated workflow run directories and return a non-zero exit code when quality checks fail.
- Documented the run contract boundary in `docs/run_contract.md` and updated workflow/README guidance.
- Verification: `pytest` passed with 57 tests, `compileall` passed, `ncut version` returned `0.1.0`, the full mock workflow generated the run contract artifacts, `inspect-run` reported `12 passed / 0 failed / 0 warnings`, and `git diff --check` passed with line-ending warnings only.

## 2026-05-17 - Phase 7.6 Agent Reviewer Contract

- Added a read-only harness reviewer that reads an existing workflow run and writes `review_report.json`.
- Added `ncut review-run --run-dir ...` for agent-readable review report generation with `passed`, `warning`, and `failed` status aggregation.
- Kept the reviewer outside workflow execution: it does not rerun workflows, call FFmpeg, call remote LLMs, or modify source run artifacts.
- Documented the reviewer contract in `docs/agent_reviewer_contract.md`.

## 2026-05-17 - Phase 7.7 Workflow Plan Draft

- Added a static workflow planner that converts workflow YAML and a planned input file into `workflow_plan.json`.
- Added `ncut draft-plan --workflow ... --input ... --output ...` without executing workflow nodes or creating run artifacts.
- Used `configs/tool_catalog.yaml` only to enrich plan step purpose text; workflow YAML remains the source of step order and outputs.
- Kept planning separate from execution, FFmpeg, remote LLMs, Web/API, database, queue, and agent runtime.
- Documented the planning contract in `docs/workflow_plan_contract.md`.

## 2026-05-17 - Phase 8 Minimal Real Slicing PoC

- Added standalone `slice_clip_plans_real(...)` execution for local FFmpeg slicing from validated clip plans.
- Added `ncut slice-real --video ... --clip-plans ... --output ...` as a separate PoC command; it does not replace the default mock workflow.
- Added `real_slice_manifest.json` output with passed/failed status, clip paths, durations, and errors.
- Kept tests independent from installed FFmpeg by mocking `subprocess.run`; missing FFmpeg returns a clear failed manifest.
- Updated tool contracts so `slice_real` requires FFmpeg, executes an external process, is not safe for automatic agent execution, and requires human review.

## 2026-05-19 - Phase 14.1 ASR-First Product Golden Path

- Started `feature/phase-14-1-asr-highlight-product-golden-path` from the merged Phase 14.0B `master`.
- Added deterministic script-highlight-to-ASR-transcript alignment via `script_highlight_alignment.json`, producing timestamped highlights from script-only highlights without visual semantic retrieval.
- Added clip-timeline subtitle export so subtitles are remapped from original-video transcript timestamps onto the assembled final-video timeline instead of reusing the source-video timeline directly.
- Extended `SubtitleManifest` with `timeline`, and package quality review now warns when subtitle evidence is not explicitly `final_video` timeline.
- Added optional local BGM metadata ingestion to `mix_bgm`; `quality_verified=true` is now carried into `audio_mix_manifest.json` so package review can distinguish verified music from arbitrary noise.
- Added two ASR-first product workflows:
  - `workflows/video_to_finished_package_real_asr.yaml`
  - `workflows/video_script_to_finished_package_real_asr.yaml`
- Added examples for the two workflows and a local BGM metadata example. Examples reference ignored local media only and do not commit videos or music.
- Added focused tests for script alignment, clip-timeline subtitles, BGM verified metadata, product package warning clearance, and both product Golden Path workflows with mocked ASR/FFmpeg.
- Product-quality intent: the old Phase 13 demo warning set remains a useful negative smoke, while the Phase 14.1 workflows can clear the six known product warnings when they receive multi-segment highlights, final-timeline subtitles, and verified BGM metadata.
- Boundaries kept: no visual/multimodal highlight detection, no Web UI, no publishing/upload, no automatic music recommendation, no real ASR in tests, and no default remote ASR without `NARRATOCUT_ALLOW_REMOTE_ASR=true`.

## 2026-05-19 - Local Faster-Whisper ASR Path

- Added `FasterWhisperASRProvider` for local `faster-whisper` transcription with CPU-first defaults (`model=tiny`, `device=cpu`, `compute_type=int8`).
- Added workflow node `transcribe_audio_faster_whisper` and local-ASR product workflow variants:
  - `workflows/video_to_finished_package_local_asr.yaml`
  - `workflows/video_script_to_finished_package_local_asr.yaml`
- Added example input bundles that use ignored local media and local model cache paths, without API keys or remote ASR opt-in.
- Updated tool contracts/catalog and workflow docs to distinguish remote ASR from local ASR.
- Verification so far: focused provider/workflow tests pass with mocked local ASR and FFmpeg. Real local ASR smoke still depends on installing `faster-whisper` and downloading a local model cache.

## 2026-05-19 - Local ASR Quality Hardening

- Improved script-to-transcript alignment for Chinese text by adding Chinese character and bigram tokens instead of relying only on English/number word tokens.
- Added transcript sliding-window matching so one script highlight can align to multiple adjacent ASR segments, which is important for local Whisper models that split Chinese speech into short fragments.
- Updated local-ASR examples to prefer `small` + CPU `int8` for better Chinese quality, with `tiny` kept as the faster engineering-only option.
- Local product smoke:
  - video-only local ASR with `small/int8/cpu`: workflow succeeded, `inspect-run` passed with 0 warnings, `review-run` passed with 0 warnings.
  - video+script local ASR with `small/int8/cpu` and lower local alignment threshold: workflow succeeded, `inspect-run` passed with 0 warnings, `review-run` passed with 0 warnings.

## 2026-05-19 - Phase 14.2B/C OCR Timeline and Candidate Scoring

- Added a deterministic OCR-subtitle timeline SOP that converts frame-level OCR results into `ocr_transcript.json` and `ocr_transcript_manifest.json`.
- Added an explainable candidate scoring SOP that writes `highlight_score_report.json` and selects scored candidates into `highlight_plan.json`.
- Added `workflows/video_subtitle_ocr_to_highlight_plan.yaml` for the offline OCR evidence path: video path validation, OCR timeline, candidate windows, scoring, and selected highlights.
- Added `candidate_scoring` inspect/review quality checks for OCR transcript presence, candidate count, selected score breakdowns, and candidate IDs in selected highlights.
- Updated tool catalog, tool contract docs, workflow docs, and README workflow/artifact lists.
- Boundary kept: no real OCR provider dependency, no frame extraction, no FFmpeg execution, no remote calls, no media slicing, no Web UI.

## 2026-05-19 - Phase 14.2D Short Highlight Product Path

- Switched the ASR-first finished-package workflows from direct highlight detection to the candidate scoring path:
  - `video_to_finished_package_real_asr.yaml`
  - `video_script_to_finished_package_real_asr.yaml`
  - `video_to_finished_package_local_asr.yaml`
  - `video_script_to_finished_package_local_asr.yaml`
- Added product defaults for short promo clips in `generate_candidate_windows`: target windows default to about 5 seconds with 4-6 second preferred candidates when explicit candidate settings are not supplied.
- Added script-alignment evidence propagation into candidate windows, scored highlights, and final clip-plan segment metadata.
- Added duplicate-source-window rejection so the scorer does not fill the final edit with adjacent fixed splits from the same long ASR/alignment window.
- Added finished-package product-quality warnings for clips over the hard short-clip limit, final videos over the hard short-form limit, duplicate clip windows, and clip plans that bypass candidate scoring.
- Real local product acceptance after this change:
  - video-only: 4 clips, clip durations 4.2s / 4.6s / 5.0s / 5.0s, final duration 18.82322s, `inspect-run` pass with 0 warnings, `review-run` passed with 0 warnings.
  - video+script: 4 clips, clip durations 5.0s / 5.0s / 4.98s / 5.0s, final duration 20.00322s, 4 aligned / 0 skipped script highlights, `inspect-run` pass with 0 warnings, `review-run` passed with 0 warnings.
- Product judgment: this fixes the previous 30s/90s overlong-cut failure and makes the current local acceptance suitable for short promo validation. Remaining quality risk is editorial selection depth: scoring is still deterministic and text-first, with OCR/visual/audio fusion planned as later evidence channels.

## 2026-05-20 - Phase 14.3 Workspace and Agent Contract Hardening

- Added `package_report.md` generation for finished-package runs so humans and agents have one readable summary instead of scanning many JSON artifacts.
- Added `ncut package-report --run-dir ...` to refresh the report after `inspect-run` and `review-run`; the workflow writes an initial report, while formal acceptance should refresh it after quality and review artifacts exist.
- Added workflow metadata (`metadata.kind`, `metadata.status`, `metadata.audience`) to recommended product workflows so agents can choose product entrypoints without relying only on filenames.
- Added `skills/` with agent-readable task contracts for video-only and video+script short highlight package generation.
- Added `docs/workspace_contract.md`, refreshed docs/workflow navigation, and updated the tool catalog/docs for `write_package_report`.
- Split FFmpeg CLI handling into `apps/cli/media_commands.py` while adding package-report CLI handling in `apps/cli/report_commands.py`, keeping `apps/cli/main.py` under the 300-line target.
- Boundary kept: no Web UI, no new agent runtime, no autonomous workflow selection, no highlight scoring algorithm rewrite, and no cleanup of ignored local run/model/media artifacts.

## 2026-05-20 - Phase 14.4A Elastic Short Clip Boundaries

- Replaced rigid long-window fixed splits with elastic short-clip boundary generation.
- Long transcript/alignment windows now split into balanced 4-6 second candidates when possible instead of leaving a short tail fragment.
- Unsplittable overlong windows now trim to the target-length core instead of producing sub-four-second weak fragments.
- Candidate evidence now records `boundary_strategy`, `target_duration_sec`, and source-window bounds for selected clips.
- `package_report.md` now displays boundary strategy, target duration, and source window for each selected clip when scoring evidence is available.
- Boundary kept: this improves clip timing shape and explainability, but does not introduce scene/silence detection, visual models, Web UI, or a new viral scoring algorithm.

## 2026-05-20 - Phase 14.4B Elastic Boundary Acceptance

- Synced `master` to PR #32 and cleaned the merged Phase 14.4A branch locally and remotely.
- Re-ran the local video-only product workflow on `data/raw/demo_real_video/input.mp4`.
  - Result: 4 clips, durations 4.2s / 4.6s / 4.79s / 4.59s, final duration 18.222331s.
  - `inspect-run`: pass, 8 passed / 0 failed / 0 warnings.
  - `review-run`: passed, 37 passed / 0 failed / 0 warnings.
- Re-ran the local video+script product workflow on `data/raw/demo_zombie/input.mp4` and `script.txt`.
  - Result: 4 clips, durations 4.9225s / 4.98s / 5.346667s / 4.785s, final duration 20.082292s.
  - Script alignment: 4 aligned / 0 skipped.
  - `inspect-run`: pass, 8 passed / 0 failed / 0 warnings.
  - `review-run`: passed, 38 passed / 0 failed / 0 warnings.
- Refined `package_report.md` boundary display so native short transcript windows are labeled `native_transcript_window` instead of `unknown`.
- Added `docs/product_acceptance_phase14_4b_elastic_boundaries.md` as the acceptance record.
- Boundary kept: this is an execution and boundary-evidence acceptance pass, not a claim that deterministic viral selection is editorially mature.

## 2026-05-20 - Phase 14.4C Local Audio Boundary Signals

- Added `boundary_signal_manifest.json` generation from the already extracted local WAV artifact.
- Added workflow node `analyze_audio_boundary_signals` and inserted it into ASR-first finished-package workflows before transcription/scoring.
- Candidate windows now attach nearest low-energy audio boundary evidence when a successful boundary signal manifest is available.
- `package_report.md` now displays selected-clip audio boundary evidence alongside transcript boundary strategy and source-window evidence.
- Updated workflow docs, workspace contract, tool catalog/contracts, and agent skill outputs so agents can treat audio boundary evidence as a first-class advisory artifact.
- Boundary kept: audio signals are advisory and local-only. They do not replace transcript/scoring logic, do not call remote models, do not add visual/multimodal analysis, and do not fail the product workflow when mock audio or unsupported audio cannot be analyzed.

## 2026-05-20 - Phase 14.4D Audio Boundary Cut-Point Refinement

- Added safe audio-boundary refinement for candidate windows: nearby high-confidence audio boundaries can adjust candidate `start_sec` and/or `end_sec`.
- Refinement is constrained by maximum adjustment distance, source transcript window bounds, and the existing short-clip duration gates, so it cannot produce overlong or underlong candidates.
- Candidate evidence now records `audio_boundary_refinement`, `boundary_strategy=audio_boundary_refined`, and `base_boundary_strategy` for refined elastic subwindows.
- Updated scoring duplicate-source-window rejection so audio-refined split candidates still dedupe against the original transcript/alignment window.
- `package_report.md` now shows base boundary strategy and audio refinement before/after time ranges for selected clips.
- Kept the boundary narrow: no Web UI, no remote LLM, no new dependencies, no visual model, and no claim that deterministic viral selection is editorially mature.

## 2026-05-20 - Phase 14.4E Audio Boundary Refinement Acceptance

- Synced `master` to PR #35 and cleaned the merged Phase 14.4D branch locally and remotely after confirming the remote branch tree matched `master`.
- Re-ran the local video-only product workflow on `data/raw/demo_real_video/input.mp4`.
  - Result: 4 clips, durations 4.2s / 4.6s / 4.79s / 4.56s, final duration 18.189323s.
  - Audio refinement applied to selected candidate `cand_008`: 32.47s - 37.06s -> 32.50s - 37.06s.
  - `inspect-run`: pass, 8 passed / 0 failed / 0 warnings.
  - `review-run`: passed, 38 passed / 0 failed / 0 warnings.
- Re-ran the local video+script product workflow on `data/raw/demo_zombie/input.mp4` and `script.txt`.
  - Result: 4 clips, durations 4.9225s / 4.98s / 5.346667s / 4.785s, final duration 20.082292s.
  - Script alignment: 4 aligned / 0 skipped.
  - No selected candidate required audio-boundary refinement in this run.
  - `inspect-run`: pass, 8 passed / 0 failed / 0 warnings.
  - `review-run`: passed, 39 passed / 0 failed / 0 warnings.
- Refined `package_report.md` audio-boundary display so distant nearest boundaries are summarized as `not nearby` instead of cluttering acceptance reports with misleading far-away evidence.
- Added `docs/product_acceptance_phase14_4e_audio_boundary_refinement.md` as the acceptance record.
- Boundary kept: this is local product acceptance plus report readability hardening, not a broader scoring rewrite or Web UI step.

## 2026-05-20 - Phase 14.6 Delivery Readiness Gate

- Synced local `master` to PR #37, deleted the merged local and remote `feature/phase-14-5-selection-diagnostics` branch, and started `codex/phase-14-6-delivery-hardening` from the latest `master`.
- Added `ncut delivery-readiness` to summarize one or more refreshed product run directories into `delivery_readiness.json` and `delivery_readiness.md`.
- Added `narratocut.package_sop.delivery` as a report-only gate over existing run artifacts: package manifest, quality report, review report, package report, score report, and selection diagnostics.
- Updated tool catalog, tool-contract docs, workspace docs, workflow docs, and agent skill contracts so the delivery readiness report becomes the final handoff gate after `inspect-run`, `review-run`, and `package-report`.
- Smoke-tested the gate against the latest local Phase 14.4E acceptance run directories. The command wrote reports but correctly returned `fail` because those older local runs predate Phase 14.5 and do not contain `selection_diagnostics.json`; formal delivery readiness now requires rerunning the product paths after Phase 14.5+.
- Re-ran both formal local product paths as Phase 14.6 acceptance runs:
  - video-only: `product_acceptance_video_only_phase14_6`, 16 candidates, 4 selected clips, final duration 18.189323s, `inspect-run` pass, `review-run` passed with 39 checks / 0 warnings.
  - video+script: `product_acceptance_video_script_phase14_6`, 18 candidates, 4 selected clips, final duration 20.082292s, 4 aligned / 0 skipped script highlights, `inspect-run` pass, `review-run` passed with 40 checks / 0 warnings.
- Ran final `delivery-readiness` for both Phase 14.6 runs. Result: `warning`, 0 failed runs, 2 warning runs. The warnings are selection-quality signals (`near_miss_rejected`, `too_many_selection_limit_rejections`, `duplicate_source_window_pressure`, `few_strong_hooks`), not execution failures.
- Added `docs/product_acceptance_phase14_6_delivery_readiness.md` as the acceptance record.
- Boundary kept: this gate does not rerun ASR/OCR/slicing/assembly, does not call remote providers, does not add Web UI, and does not claim deterministic selection quality is editorially final.

## 2026-05-20 - Phase 14.6 Selection-Quality Hardening

- Investigated the Phase 14.6 delivery-readiness warnings and confirmed the main root cause was not execution failure: selected candidates were tying on duration-fit because the deterministic scorer did not recognize Chinese short-drama/promo hook, conflict, payoff, or specificity cues.
- Added a focused `candidate_sop.signals` module for multilingual deterministic content signals, keeping `scoring.py` under the 300-line target.
- Updated candidate scoring so Chinese terms such as `消失`, `后悔`, `重生`, `末世`, `广播`, `疫苗`, `年入`, `百万`, `穷酸`, and related payoff/conflict cues contribute to `hook_strength`, `conflict_intensity`, `payoff_or_reversal`, and `specificity_or_novelty`.
- Added a small source-window position penalty for later repeated elastic subwindows, while preserving timeline-ordered `highlight_plan.json` output so final assembly remains natural.
- Refined `selection_diagnostics.json` warnings so expected overlap and duplicate-source pruning remain visible as near-miss evidence but do not raise delivery-readiness warnings unless the pressure is actionable.
- Added regression tests for Chinese short-drama hook prioritization, repeated source subwindow penalties, and non-actionable selection-limit/duplicate pruning warnings.
- Re-ran formal local product paths as selection-quality acceptance runs:
  - video-only: `product_acceptance_video_only_phase14_6_selection_quality`, 16 candidates, 4 selected clips, final duration 18.788998s, `selection_diagnostics.json` 0 warnings, `inspect-run` pass, `review-run` 39 passed / 0 warnings.
  - video+script: `product_acceptance_video_script_phase14_6_selection_quality`, 18 candidates, 4 selected clips, final duration 20.419887s, `selection_diagnostics.json` 0 warnings, `inspect-run` pass, `review-run` 40 passed / 0 warnings.
- Ran final `delivery-readiness` for the selection-quality reruns. Result: `pass`, 2 passed / 0 warning / 0 failed.
- Boundary kept: this closes the visible deterministic selection warnings for current local acceptance素材, but it is still text-first heuristic scoring, not a claim that viral/editorial judgment is mature.

## 2026-05-20 - Post-v0.1.0 Startup Scan and Phase 15 Planning

- Confirmed the release baseline after the `v0.1.0` closeout:
  - local `master`: `bf5e7a1`
  - `origin/master`: `bf5e7a1`
  - remote head: only `master`
  - `v0.1.0` tag type: annotated tag
  - `v0.1.0` tag object: `460deba`
  - `v0.1.0^{}`: `bf5e7a1`
  - working tree: clean before the planning edits
- Added `docs/post_v0_1_0_plan.md` as the post-release operating plan.
- Updated `docs/README.md` and `docs/product_roadmap.md` so future agents start from the Phase 15 plan instead of reopening older phase notes.
- Planning boundary: keep the `v0.1.0` CLI/Agent MVP stable, open a future Web UI branch as a package/run viewer, and expand AgentFlow Studio mainline through architecture/contracts before runtime work.
- Boundary kept: no workflow, schema, CLI, provider, media, or Web UI implementation changed in this planning pass.

## 2026-05-20 - NarratoStudio Mainline MVP

- Added `NarratoStudio` as a sibling production-side MVP module inside the current repository. `NarratoCut` remains the distribution-side module.
- Implemented the first recommended workflow:
  - `creative_brief.json`
  - `story_bible.json`
  - `episode_outline.json`
  - `scene_plan.json`
  - `shot_plan.json`
  - `prompt_pack.json`
  - `production_handoff.json`
  - `production_report.md`
- Added local deterministic SOP logic and Pydantic contracts under `narratostudio/`; no remote LLM, Agent runtime, database, or Web UI was added.
- Added Agent-native auxiliary artifacts:
  - `memory_candidates.json` with candidate-only promotion status
  - `cost_quality_trace.json` with `execution_mode: local_deterministic`
  - `feedback_signal_log.json` as a derived artifact, not a feedback source of truth
  - `execution_trace.json` as a local workflow execution trace
- Added `narratostudio_production_handoff` inspect/review profile and agent skill contract.
- Added `docs/narratostudio_contracts.md`, workflow docs, and the example creative brief.
- Verification:
  - `.venv\Scripts\python.exe -m pytest`: 333 passed
  - `.venv\Scripts\python.exe -m compileall apps narratocut narratostudio tests`: passed
  - `git diff --check`: passed
  - `.venv\Scripts\python.exe -m apps.cli.main --help`: passed
  - `.venv\Scripts\python.exe -m apps.cli.main version`: `0.1.0`
  - NarratoStudio CLI smoke: workflow success, inspect `58 passed / 0 failed / 0 warnings`, review `76 passed / 0 failed / 0 warnings`
- Boundary kept: Web UI branch remains separate; this change does not migrate `D:\Projects\Zhike` and does not rename the repo or CLI.

## 2026-05-21 - Phase 15.2 AgentFlow Mainline Contracts

- Synced local `master` to the merged NarratoStudio PR at `dd0b25e` and started `codex/agentflow-mainline-contracts` from a clean mainline.
- Added AgentFlow Studio contract-layer docs:
  - `docs/agentflow_studio_architecture.md`
  - `docs/module_boundary.md`
  - `docs/agentflow_artifact_map.md`
  - `docs/agentflow_memory_contract.md`
  - `docs/agentflow_skill_contract.md`
- Added minimal AgentFlow examples under `examples/agentflow/`:
  - `project_manifest.example.json`
  - `artifact_map.example.json`
  - `feedback_event.example.jsonl`
- Updated docs navigation, current architecture, and roadmap so Phase 15.2 is discoverable from the main docs index.
- Boundary kept: this is a platform contract layer only; no workflow, CLI, package name, tag, Router runtime, Memory runtime, skill runtime, Web UI, database, or remote provider behavior changed.

## 2026-05-22 - Phase 15.14 AgentFlow Architecture Refactor Plan

- Synced `master` to the merged Phase 15.13 intermediate asset architecture PR and opened `codex/agentflow-architecture-refactor-plan`.
- Added `docs/agentflow_architecture_refactor_plan.md` to define the future `agentflow/` platform package boundary before moving code.
- The plan keeps `narratostudio/` responsible for production-side handoff logic and `narratocut/` responsible for distribution-side media workflows and current CLI behavior.
- Defined a migration order: package skeleton, pure contract utilities, AgentFlow harness validators, compatibility imports, then docs/examples updates.
- Added the regression matrix for contract examples, audit, Router dry-run validation, skill replay validation, NarratoStudio smoke, NarratoCut delivery readiness, CLI help/version, full tests, and compileall.
- Boundary kept: this is a planning slice only; no Python modules were moved, no workflow/CLI behavior changed, and no Router, skill, Memory, database, hosted API, provider, or Web UI runtime was added.

## 2026-05-22 - Phase 15.15 AgentFlow Package Skeleton

- Synced `master` to the merged Phase 15.14 architecture refactor plan and opened `codex/agentflow-package-skeleton`.
- Added the top-level `agentflow/` package with reserved namespaces for `contracts`, `harness`, `memory`, `router`, and `skills`.
- Added import smoke tests proving the new platform namespace imports without runtime side effects and that existing `narratocut.harness.agentflow_router` / `agentflow_skill` imports still work.
- Boundary kept: no validators, contracts, workflow nodes, CLI commands, providers, database, Web UI, Router runtime, skill runtime, or Memory runtime were moved or added.

## 2026-05-22 - Phase 15.16 AgentFlow Contract Example Helpers

- Synced `master` to the merged Phase 15.15 package skeleton and opened `codex/agentflow-contract-helpers`.
- Added `agentflow.contracts.examples` with schema version, committed AgentFlow example paths, artifact type constants, and read-only JSON/JSONL loading helpers.
- Updated contract example tests to reuse the platform helper constants instead of duplicating example path lists.
- Boundary kept: no validators, workflow nodes, CLI commands, artifact contracts, providers, database, Web UI, Router runtime, skill runtime, or Memory runtime were moved or added.

## 2026-05-25 - AFS-MEM-001 PosterFlow Memory OS Loop

- Started `codex/memory-os-loop` in global worktree `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\memory-os-loop` because the main checkout contained intentional uncommitted company-rule projection files.
- Added PosterFlow sidecar Memory OS artifacts while preserving the existing JSON artifacts:
  - `poster_feedback.jsonl` as the raw feedback source of truth.
  - `poster_memory_candidates.jsonl` as candidate-only memory rows.
  - `poster_memory_review.jsonl` as explicit demo human-review decisions with `writes_long_term_memory: false`.
- Kept the slice local and contract-oriented: no remote-provider behavior changed, no durable Memory runtime was added, and no `agentflow/memory/*` runtime expansion was started.
- Extended PosterFlow quality checks and run manifest defaults so inspect/review can reject missing raw feedback, feedback logs that replace raw feedback, JSON/JSONL mismatches, and memory review rows claiming durable writes.
- Used a read-only Explorer subagent for code-location confirmation only; implementation stayed on the main controller to avoid overlapping write scopes.
- Verification:
  - targeted red step: new PosterFlow tests failed on missing `poster_feedback.jsonl` / `poster_memory_review.jsonl`.
  - `python -m pytest tests/test_posterflow_workflow.py tests/test_posterflow_quality.py tests/test_posterflow_provider.py`: 14 passed.
  - `python -m pytest`: 487 passed.
  - `git diff --check`: passed.
  - `python -m apps.cli.main --help`: passed.
  - `python -m apps.cli.main version`: `0.1.0`.
- Boundary kept: this is structure/runtime verification for artifact contracts, not human acceptance of poster creative quality or business validation of Memory OS.

## 2026-05-25 - AFS-CTX-001 PosterFlow Context Runtime Trace

- Continued as a stacked slice on `codex/memory-os-loop` because the Context Runtime artifacts depend on the unintegrated AFS-MEM-001 feedback and memory-review artifacts.
- Added a minimal PosterFlow context assembly layer:
  - `context_bundle.json` records hot/warm/cold/policy context layers, project prefix path, preference profile path, source artifacts, quality rules, retrieval status, and cache plan.
  - `context_assembly_trace.json` records why project prefix, preference profile, retrieval memory, and quality policy were included or excluded.
- Added `narratostudio.posterflow.context_runtime` so context assembly logic stays out of `sop.py` and files remain under the 300-line target.
- Updated `next_round_prompt.json` memory context to reference `context_bundle.json` and the generated cache key.
- Extended PosterFlow inspect/review checks to validate context bundle/profile/prefix refs, trace-to-bundle refs, cache-key match, and no long-term memory writes.
- Verification:
  - targeted red step: `tests/test_posterflow_workflow.py` failed on missing `ContextBundle` / `ContextAssemblyTrace` schema.
  - `python -m pytest tests/test_posterflow_workflow.py tests/test_posterflow_quality.py tests/test_posterflow_provider.py`: 15 passed.
  - `python -m pytest`: 488 passed.
  - `git diff --check`: passed.
  - `python -m apps.cli.main --help`: passed.
  - `python -m apps.cli.main version`: `0.1.0`.
- Boundary kept: this is an artifact-first Context Runtime trace, not RAG, not prefix-cache service, not Router runtime, and not model/provider orchestration.
- Follow-up: before starting `AFS-QLT-001`, integrate or intentionally keep this stacked branch; `narratocut/harness/posterflow_quality.py` is now 285 lines and should be split before adding more PosterFlow quality checks.

## 2026-05-25 - AFS-QLT-001 PosterFlow Quality Feedback Signals

- Started `codex/quality-feedback-signals` from clean `master` after integrating
  AFS-MEM-001 and AFS-CTX-001.
- Split `narratocut/harness/posterflow_quality.py` into focused modules:
  - `posterflow_quality_io.py` for required artifacts, JSON/JSONL parsing, and schema checks.
  - `posterflow_quality_references.py` for cross-artifact reference checks and candidate counts.
  - `posterflow_quality_feedback.py` for candidate quality feedback signals from failed checks.
- Reduced `posterflow_quality.py` from 338 lines to 102 lines; all new modules
  stay under the 300-line project limit.
- Added a minimal quality feedback path:
  - failed PosterFlow quality checks emit `quality_report.json.feedback_signals`;
  - passing PosterFlow runs emit no feedback signals;
  - feedback signals are candidate-only and set `writes_long_term_memory: false`.
- TDD evidence:
  - red: `tests/test_posterflow_quality.py::test_posterflow_review_fails_when_candidate_image_is_missing` failed with missing `feedback_signals`.
  - green: the same test passed after adding `posterflow_quality_feedback.py`.
- Verification:
  - `python -m pytest tests/test_posterflow_quality.py tests/test_posterflow_workflow.py tests/test_posterflow_provider.py`: 15 passed.
- Boundary kept: no durable Memory runtime, no RAG, no provider behavior change,
  no workflow output contract change, and no automatic long-term memory write.

## 2026-05-26 - AFS-DEMO-001 PosterFlow Two-Round Memory Demo

- Started `codex/posterflow-two-round-demo` from updated `master` after
  integrating `AFS-QLT-001` and deleting stale integrated branches.
- Added a true second PosterFlow generation round:
  - `round_2/poster_prompt_pack.json` is derived from
    `next_round_prompt.json`.
  - `round_2/poster_candidates_manifest.json`,
    `round_2/poster_model_invocations.json`, and
    `round_2/image_candidates/` are written by the existing image provider
    path.
  - `poster_round_comparison.json` records round 1 vs round 2 candidate
    evidence, reused memory refs, cache key, and
    `writes_long_term_memory: false`.
  - `poster_two_round_report.md` gives an agent-readable comparison summary.
- Added `narratostudio.posterflow.two_round` so second-round prompt assembly,
  path normalization, comparison JSON, and report rendering stay out of the
  workflow node file.
- Extended PosterFlow inspect/review checks to cover second-round prompt usage,
  second-round candidate images, and comparison-to-manifest consistency.
- TDD evidence:
  - red: `tests/test_posterflow_workflow.py::test_posterflow_memory_demo_workflow_generates_visual_artifacts`
    failed on missing `round_2/poster_prompt_pack.json`.
  - green: the same test passed after adding the second-round nodes.
  - red: `tests/test_posterflow_quality.py::test_posterflow_review_fails_when_round_2_manifest_breaks_memory_reuse`
    passed review incorrectly after a broken comparison report.
  - green: the same test passed after adding round-2 quality reference checks.
  - red: targeted workflow checks failed while round-2 provenance still pointed
    at the first-round prompt pack and inspection did not list
    `round_2/image_candidates/`.
  - green: the same targeted checks passed after fixing round-2 source refs and
    inspection artifact coverage.
- Verification:
  - `python -m pytest tests/test_posterflow_workflow.py tests/test_posterflow_quality.py tests/test_posterflow_provider.py`: 16 passed.
  - `python -m pytest`: 489 passed.
  - `git diff --check`: passed with Windows line-ending warnings only.
  - `python -m apps.cli.main --help`: passed.
  - `python -m apps.cli.main version`: `0.1.0`.
- Boundary kept: no durable Memory runtime, no RAG, no Web UI, no database, no
  new provider policy, and no automatic long-term memory write. The second
  remote-image call remains protected by the existing
  `NARRATOCUT_ALLOW_REMOTE_IMAGE=true` gate.
