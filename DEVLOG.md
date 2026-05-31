# DEVLOG

Status: active short development log. Long historical narrative has been compressed into archive indexes so this file stays usable during project maintenance.

Current references: live work ledger `TASK_TRACKER.md`; historical DEVLOG index
`docs/archive/devlog_history_2026_05.md`; pre-reset task history
`docs/archive/task_history_2026_05.md`.

2026-06-01: Loulan memory pilot package, API workbench dry-run, B01 human review pack, decision template, context bundle projection, optional asset registry gate, and Web decision/context rendering contracts, CLIs, Web projections, examples, tracker rows, task briefs, and handoffs added; see `docs/handoff/AFS-LOULAN-PILOT-001.md`, `docs/handoff/AFS-LOULAN-API-WORKBENCH-001.md`, `docs/handoff/AFS-LOULAN-HUMAN-REVIEW-001.md`, `docs/handoff/AFS-LOULAN-DECISION-TEMPLATE-001.md`, `docs/handoff/AFS-LOULAN-CONTEXT-BUNDLE-001.md`, `docs/handoff/AFS-LOULAN-ASSET-REGISTRY-001.md`, and `docs/handoff/AFS-LOULAN-WEB-CONTEXT-001.md`.

2026-06-01: Loulan API workbench accepts optional context bundle projections from explicit human decisions and blocks fallback when supplied projections are not ready; the real no-call context probe confirms 47 pending decisions, the decision review pack groups them as 5 shots plus 42 assets, the worksheet exports empty manual-fill rows, Web renders the worksheet as selected-file evidence, decision intake blocks unfilled manual transfers before context projection, Web renders the intake gate as selected-file evidence, context bundle can now treat a supplied intake report as a hard pre-context gate, Web surfaces that gate in context projection cards/controls/inspector/timeline, API workbench records/rejects supplied context projection intake gates before request preview, API CLI/report shows the gate, and Web surfaces the API plan gate in protocol controls and inspector facts; see `docs/handoff/AFS-LOULAN-API-CONTEXT-001.md`, `docs/handoff/AFS-LOULAN-CONTEXT-PROBE-001.md`, `docs/handoff/AFS-LOULAN-DECISION-REVIEW-001.md`, `docs/handoff/AFS-LOULAN-WEB-DECISION-REVIEW-001.md`, `docs/handoff/AFS-LOULAN-DECISION-WORKSHEET-001.md`, `docs/handoff/AFS-LOULAN-WEB-DECISION-WORKSHEET-001.md`, `docs/handoff/AFS-LOULAN-DECISION-INTAKE-001.md`, `docs/handoff/AFS-LOULAN-WEB-DECISION-INTAKE-001.md`, `docs/handoff/AFS-LOULAN-CONTEXT-BUNDLE-001.md`, `docs/handoff/AFS-LOULAN-CONTEXT-BUNDLE-INTAKE-GATE-001.md`, `docs/handoff/AFS-LOULAN-WEB-CONTEXT-INTAKE-GATE-001.md`, `docs/handoff/AFS-LOULAN-API-INTAKE-GATE-001.md`, `docs/handoff/AFS-LOULAN-API-INTAKE-GATE-CLI-001.md`, and `docs/handoff/AFS-LOULAN-WEB-API-INTAKE-GATE-001.md`.

2026-06-01: Loulan B01 decision import bridge added as a no-call local handoff from the Loulan `b01_human_review_decision_template.json` into AFS `agentflow_loulan_promotion_decisions`; the real probe imports 0 ready decisions and leaves 7 pending, so B01 still blocks context projection until human decisions are filled; see `docs/handoff/AFS-LOULAN-B01-DECISION-IMPORT-001.md`.

2026-06-01: Loulan Web workbench now distinguishes B01 imported decision files from plain promotion-decision templates, surfacing imported-ready, pending, skipped, and source block facts while keeping the selected-file UI read-only and non-acceptance; see `docs/handoff/AFS-LOULAN-WEB-B01-DECISION-IMPORT-001.md`.

2026-06-01: Loulan memory package now reads the optional local B01 feedback-loop gate and Web surfaces the blocked B01 status in package summary, protocol, inspector, and timeline; real no-call probe over `D:\Projects\LoulanSceneAssets` reports 5 pending B01 decisions and no unsafe output refs; see `docs/handoff/AFS-LOULAN-PACKAGE-B01-FEEDBACK-GATE-001.md`.

2026-06-01: Web Artifact Workspace now recognizes a directly selected `loulan_afs_b01_feedback_loop_gate` / `afs_b01_feedback_loop_gate.json` as a read-only memory artifact, so operators can inspect the blocked B01 gate without regenerating the full Loulan package; see `docs/handoff/AFS-LOULAN-WEB-B01-GATE-DIRECT-001.md`.

2026-06-01: Loulan memory package now reads the optional B01 decision crosswalk and Web surfaces the 5-shot local gate, 7-slot AFS import gate, and 47-slot broader decision-review gate as separate blocked layers; see `docs/handoff/AFS-LOULAN-PACKAGE-B01-CROSSWALK-001.md`.

2026-06-01: Web Artifact Workspace now recognizes a directly selected `loulan_afs_b01_decision_crosswalk` / `afs_b01_decision_crosswalk.json` as a read-only memory artifact and keeps B01-specific inspector facts in a separate module; see `docs/handoff/AFS-LOULAN-WEB-B01-CROSSWALK-DIRECT-001.md`.

2026-06-01: Web Artifact Workspace now recognizes the local Loulan `loulan_b01_human_review_decision_template` / `b01_human_review_decision_template.json` directly as a read-only memory artifact, showing the five pending B01 shot decisions without importing or approving them; see `docs/handoff/AFS-LOULAN-WEB-B01-LOCAL-DECISION-TEMPLATE-DIRECT-001.md`.

2026-06-01: Web Artifact Workspace now recognizes Loulan B01 validation/apply status outputs (`loulan_b01_decision_validation_report` and `loulan_b01_decision_apply_result`) directly as read-only memory artifacts so operators can inspect the current gate result without running context projection or provider preview; see `docs/handoff/AFS-LOULAN-WEB-B01-STATUS-DIRECT-001.md`.

2026-06-01: Web Artifact Workspace now recognizes the Loulan unified `asset_registry.json` directly as a read-only memory artifact, surfacing 85-asset health counts and blocked promotion state without regenerating a package or promoting candidates; see `docs/handoff/AFS-LOULAN-WEB-ASSET-REGISTRY-DIRECT-001.md`.

2026-06-01: Web Artifact Workspace now recognizes the Loulan `next_context_bundle_draft.json` directly as a read-only memory artifact, surfacing the B02 target, eligible/blocked refs, review evidence refs, and B01/provider gates while keeping context projection and generation blocked; see `docs/handoff/AFS-LOULAN-WEB-CONTEXT-DRAFT-DIRECT-001.md`.

2026-06-01: Web Artifact Workspace now recognizes the Loulan `b01_decision_apply_plan_draft.json` directly as a read-only memory artifact, showing why B01 apply is still blocked without mutating registry, shot list, context draft, provider state, or durable Memory; see `docs/handoff/AFS-LOULAN-WEB-B01-APPLY-PLAN-DIRECT-001.md`.

2026-06-01: Web Artifact Workspace now recognizes Loulan generation request manifests (`image2_requests.json` and `kling_i2v_requests.json`) directly as read-only memory artifacts, surfacing 38-request Image2/Kling planning summaries without starting any provider call; see `docs/handoff/AFS-LOULAN-WEB-REQUEST-MANIFESTS-DIRECT-001.md`.

## 2026-05-31 - Oversized File Slimming Pass

- Split the remaining current oversized files without changing behavior:
  DEMO-012 review HTML rendering moved to
  `narratocut/memory_advantage_demo_012_review_html.py`, DEMO-012 test
  manifest helpers moved to `tests/memory_advantage_demo_012_helpers.py`, and
  memory-video-pipeline contract example checks moved to
  `tests/test_contract_examples_memory_video_pipeline.py`.
- Result: no changed or untracked code/docs file in the current checkout is
  over the 300 effective-line target.
- Added `tools/staging_preflight.py` to check dirty-tree staging boundaries:
  local-only paths, effective file length, and hardcoded Company secret paths.
- Verification: focused DEMO-012/contract tests -> 39 passed; staging
  preflight -> pass.

## 2026-05-31 - Mainline Staging Bundle Draft

- Continued from the provider/operator review into a coherent staging plan.
- Added `docs/maintenance/AFS-MAINLINE-STAGING-BUNDLE-001.md` as the current
  bundle manifest.
- Key decision: product mainline and reviewed hidden support/evidence should be
  staged as explicit layers. `apps/cli/command_registry.py` now owns product
  command registration, and `apps/cli/support_command_registry.py` owns hidden
  provider/demo registration while full CLI bootstrap preserves both layers.
- Product surface remains `memory-video-pipeline-*`; provider/demo commands
  remain hidden support/evidence and are not human acceptance, business
  validation, provider approval, or durable Memory runtime proof.
- Verification:
  - Memory video pipeline focused tests -> 27 passed.
  - AgentFlow contracts/examples tests -> 52 passed.
  - Web static/workbench tests -> 63 passed.
  - Workflow focused tests -> 19 passed.
  - Provider/demo support tests -> 61 passed.
  - CLI registry boundary tests -> 52 passed.
  - Full suite -> 675 passed.

## 2026-05-31 - Provider / Operator Staging Review

- Continued slimming toward a staged integration plan without provider calls,
  generated media, Company knowledge-base copies, staging, or commits.
- Added `docs/maintenance/AFS-PROVIDER-OPERATOR-STAGING-REVIEW-001.md` to
  classify hidden Kling/MiniMax commands, provider adapters, RECORDING-016, and
  mocked tests as a separate support slice rather than product surface.
- Tightened `tools/run_memory_advantage_recording_016.ps1`: live mode now
  requires `-ProviderConfig` or `NARRATOCUT_PROVIDER_CONFIG` in addition to
  `-AllowRemoteVideo` or `NARRATOCUT_ALLOW_REMOTE_VIDEO=true`.
- Updated RECORDING-016, competition run sheet, and talk track live commands
  to show explicit provider config.
- Verification so far:
  - `.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests/test_recording_016_script.py -q`
    -> 2 passed.
  - Provider/operator suite including Kling, MiniMax, PosterFlow provider, and
    RECORDING-016 script checks -> 44 passed.
  - `tests/test_agentflow_roadmap_docs.py` -> 16 passed.
  - PowerShell parser check for `tools/run_memory_advantage_recording_016.ps1`
    -> passed.
  - Sensitive-pattern scan over reviewed provider/operator paths -> no matches.
  - Default CLI help surface -> hidden provider/demo commands absent.
  - `git diff --check` -> no whitespace errors; CRLF normalization warnings
    only.

## 2026-05-31 - Provider Config Bridge Hardening

- Continued repository slimming under the full project rule hierarchy and the
  staging candidate ledger.
- Remote-provider policy: no remote provider calls. Verification used config
  parsing, CLI help, py_compile, and mocked/local tests only.
- Removed the hardcoded local Company `.secrets` provider-config default from
  `narratocut/model_gateway/company_secrets.py`.
- Added `NARRATOCUT_PROVIDER_CONFIG` as the environment-variable fallback when
  a provider config path is not passed explicitly.
- Updated hidden provider/operator CLI commands so `--provider-config` defaults
  to `None`, with help text pointing to `NARRATOCUT_PROVIDER_CONFIG`.
- Added tests proving that `load_company_provider_secrets()` fails when neither
  explicit path nor environment variable is present, succeeds when the env var
  points at a local test config, and exposes the same env fallback in hidden
  Kling/MiniMax CLI help.
- Boundary kept: provider/operator commands remain hidden from default product
  help, remote calls remain capability-gated, and this change does not promote
  provider smoke, generated media, human acceptance, business validation, or
  durable Memory behavior.
- Verification:
  - `.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests/test_kling_video_request_plan.py tests/test_kling_video_smoke.py tests/test_kling_video_t2v_smoke.py tests/test_kling_video_curl_smoke.py tests/test_kling_video_task_recovery.py tests/test_minimax_image_smoke.py -q`
    -> 29 passed.
  - `.\.venv\Scripts\python.exe -B -m py_compile narratocut/model_gateway/company_secrets.py apps/cli/kling_video_command.py apps/cli/minimax_image_command.py apps/cli/memory_demo_commands.py`
    -> passed.
  - `.\.venv\Scripts\python.exe -B -m apps.cli.main --help`,
    `.\.venv\Scripts\python.exe -B -m apps.cli.main kling-i2v-smoke --help`,
    and `.\.venv\Scripts\python.exe -B -m apps.cli.main minimax-image-smoke --help`
    -> passed.
  - Hardcoded local Company `.secrets` provider path scan -> no matches.

## 2026-05-31 - Pre-Staging Candidate Ledger

- Continued repository slimming under the full project rule hierarchy:
  Company source knowledge base -> global workflow skills -> project
  `AGENTS.md` -> `docs/company_operating_model.md` -> `TASK_TRACKER.md` /
  branch handoff -> current task.
- Remote-provider policy: no remote provider calls. This was classification and
  documentation only.
- Added `docs/maintenance/AFS-STAGING-CANDIDATE-001.md` as the current
  pre-staging classification ledger for the dirty checkout.
- Classified 51 modified tracked files and 120 untracked files into staging
  groups: maintenance control, Company workflow projection, AgentFlow
  contracts/examples, memory video pipeline mainline, Web Memory Workbench,
  workflow-engine slimming, evidence docs/runbooks, provider/operator
  quarantine, numbered demo legacy, and local-only ignored artifacts.
- Captured the staging-blocking design issue that
  `narratocut/model_gateway/company_secrets.py` hardcodes a local Company
  `.secrets` path. It does not contain a secret value in the inspected file,
  but it should be replaced with an environment-variable or explicit CLI path
  policy before provider/operator files are staged.
- Boundary kept: no staging, commit, deletion, source rewrite, provider call,
  generated media promotion, or Company knowledge-base copy.
- Verification:
  - `python -B -m apps.cli.main --help` -> passed; default CLI still exposes
    `memory-video-pipeline-*`, `memory-evidence-reuse-review`, and `web-bridge`
    without surfacing numbered demo/provider smoke commands.
  - `python -B -m pytest tests/test_agentflow_roadmap_docs.py tests/test_memory_video_pipeline_workflow.py tests/test_memory_advantage_demo_012.py tests/test_memory_advantage_demo_015.py tests/test_minimax_image_smoke.py tests/test_kling_video_smoke.py -q`
    -> 48 passed.
  - `git diff --check` -> no whitespace errors; CRLF normalization warnings
    only.
  - Current maintenance documents remained under the 300-line project target.
  - Source/test `__pycache__` recount under cleanup roots -> 0 remaining after
    re-cleaning ignored test bytecode generated by pytest.
  - `git status --short --ignored data/processed` shows ignored local runtime,
    screenshot, and maintenance backup roots only.

## 2026-05-31 - DEVLOG Archive Compression

- Continued the repository slimming work under the updated project operating rules: task mode `Deep`, no subagent, write scope limited to root DEVLOG, archive index, maintenance ledger, and task tracker records.
- Remote-provider policy: no remote provider calls. This was documentation and local maintenance only.
- Replaced the multi-thousand-line live `DEVLOG.md` body with a current short log that keeps the 2026-05-31 maintenance entries and links to authoritative work ledgers.
- Added `docs/archive/devlog_history_2026_05.md` as a compact historical section index for older DEVLOG entries.
- Preserved the full pre-slimming DEVLOG text under ignored local backup `data/processed/maintenance_backups/AFS-SLIMMING-DEVLOG-001/DEVLOG.pre_slimming_2026-05-31.md` for recovery only.
- Boundary kept: no source code, tests, provider adapters, evidence runbooks, generated run evidence, secrets, local configuration, or Company knowledge-base files were changed.
- Verification:
  - `python -B -m apps.cli.main --help` -> passed; visible product CLI
    surface remains centered on `memory-video-pipeline-*`,
    `memory-evidence-reuse-review`, and `web-bridge`.
  - `python -B -m pytest tests/test_agentflow_roadmap_docs.py tests/test_memory_video_pipeline_workflow.py tests/test_memory_advantage_demo_012.py tests/test_memory_advantage_demo_015.py tests/test_minimax_image_smoke.py tests/test_kling_video_smoke.py -q`
    -> 48 passed.
  - Line counts after compression: root `DEVLOG.md` 182 lines,
    `docs/archive/devlog_history_2026_05.md` 200 lines.
  - Source/test `__pycache__` recount under cleanup roots -> 0 remaining.
  - `git diff --check` -> no whitespace errors; CRLF normalization warnings
    only.

## 2026-05-31 - Ignored Bytecode Cache Cleanup

- Practiced the first low-risk slimming action from
  `docs/maintenance/AFS-SLIMMING-BOUNDARY-001.md`.
- Remote-provider policy: no remote provider calls. This was local filesystem
  cleanup plus documentation only.
- Deleted 35 ignored `__pycache__` directories under `apps/`, `agentflow/`,
  `narratocut/`, `narratostudio/`, and `tests/`.
- Safety gate before deletion: each target was resolved under
  `D:\Projects\AgentFlowStudio` and confirmed ignored by Git with
  `git check-ignore`; unsafe target count was 0.
- Boundary kept: no tracked source/test file, evidence document, provider
  adapter, generated run evidence, secret, local config, or Company
  knowledge-base file was deleted.
- Verification:
  - `python -B -m apps.cli.main --help` -> passed.
  - `python -B -m pytest tests/test_memory_video_pipeline_workflow.py tests/test_memory_advantage_demo_012.py tests/test_memory_advantage_demo_015.py tests/test_minimax_image_smoke.py tests/test_kling_video_smoke.py -q`
    -> 32 passed.
  - Source/test `__pycache__` recount under cleanup roots -> 0 remaining.
  - `git diff --check` -> no whitespace errors; CRLF normalization warnings
    only.

## 2026-05-31 - Mainline Slimming Boundary Ledger

- Continued the repository slimming work under the updated project operating
  rules: task mode `Deep`, no subagent, write scope limited to maintenance
  classification and project records.
- Added `docs/maintenance/AFS-SLIMMING-BOUNDARY-001.md` as the current
  mainline slimming boundary ledger.
- Classified `memory-video-pipeline-*`, explicit AgentFlow examples/contracts,
  Web Memory Workbench, and workflow-engine core as mainline keep areas.
- Classified DEMO-012 through RECORDING-016 as evidence to preserve, with
  bounded claims and no human acceptance, business validation, or durable Memory
  runtime claim.
- Classified direct Kling/MiniMax provider smoke and numbered demo commands as
  hidden legacy/operator paths pending protocol-driven replacement.
- Marked old ignored bytecode caches, long-form DEVLOG history, and bespoke
  DEMO-012/015 runtime modules as removal candidates with explicit gates.
- Remote-provider policy: no remote provider calls. This was a classification
  and documentation pass only.
- Verification:
  - `python -m apps.cli.main --help` -> passed; visible CLI surface lists
    `memory-video-pipeline-*` and `memory-evidence-reuse-review`, while hidden
    numbered/provider smoke commands stay off default help.
  - `pytest tests/test_memory_video_pipeline_workflow.py tests/test_memory_advantage_demo_012.py tests/test_memory_advantage_demo_015.py tests/test_minimax_image_smoke.py tests/test_kling_video_smoke.py -q`
    -> 32 passed.
  - `git diff --check` -> no whitespace errors; CRLF normalization warnings
    only.

## 2026-05-31 - Module And Provider Slimming Summary

- Workflow-engine shared helper consolidation, workflow node helper splitting,
  MiniMax smoke slimming, and Kling smoke slimming are treated as completed
  2026-05-31 maintenance slices.
- Evidence and detailed verification are tracked in `TASK_TRACKER.md` and the
  historical index `docs/archive/devlog_history_2026_05.md`.
- Boundary kept: provider smoke remains hidden, explicitly gated evidence; it
  is not the visible product surface, human acceptance, business validation, or
  durable Memory runtime proof.


## Archive Policy

- Keep this root log focused on current maintenance and recent evidence pointers.
- Put long historical summaries in `docs/archive/` and detailed evidence in focused handoff, maintenance, or workbench documents.
- Do not use DEVLOG entries alone as human acceptance, business validation, or durable memory promotion evidence.
