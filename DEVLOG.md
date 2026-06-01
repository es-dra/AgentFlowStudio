# DEVLOG

Status: active short development log. Long historical narrative has been compressed into archive indexes so this file stays usable during project maintenance.

Current references:

- Live work ledger: `TASK_TRACKER.md`.
- Mainline slimming boundary: `docs/maintenance/AFS-SLIMMING-BOUNDARY-001.md`.
- Historical DEVLOG index: `docs/archive/devlog_history_2026_05.md`.
- Pre-reset task history: `docs/archive/task_history_2026_05.md`.

## 2026-06-02 - Production Memory Next Task Packet 001

- Continued the generic Production Memory Architecture path on
  `codex/afs-production-memory-next-task-packet-001`, based on the verified
  next-context handoff Web slice.
- Added `agentflow/memory/production_next_task.py` and
  `production-memory-loop-next-task-packet`.
- The packet consumes a ready `next_context_handoff.json` and writes
  `next_task_packet.json` and `.md` as a no-provider entry packet for the next
  AI task. It exposes `allowed_context_refs` separately from `blocked_refs` and
  repeats feedback/candidate/promotion boundaries.
- Integrated the packet into `production-memory-loop-run-operator-no-provider`
  so one local operator run now emits run/context/readiness/next pass,
  next-context handoff, next-task packet, session report, Company KB candidate
  packet, and operator manifest.
- Boundary kept: no provider call, no Company KB write, no durable memory
  write, no next-pass execution, no human acceptance, and no business
  validation claim.
- Verification so far:
  - `data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_next_task_packet.py -q` -> 4 passed.
  - `data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_operator_loop.py -q` -> 2 passed.
  - `data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_next_task_packet.py tests/test_production_memory_next_context_handoff.py tests/test_production_memory_operator_loop.py tests/test_contract_examples.py tests/test_cli_command_registry_boundaries.py -q` -> 35 passed.
  - `data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main --help` -> passed; `production-memory-loop-next-task-packet` is visible.
  - CLI smoke wrote ignored next-task packet JSON/Markdown outputs through the operator-loop command.
  - `data\processed\venvs\afs-py312\Scripts\python.exe -m pytest` -> 726 passed on Python 3.12.12.
  - `git diff --check` -> exit 0; CRLF normalization warnings only.

## 2026-06-02 - Production Memory Next Context Handoff Web 001

- Continued the generic Production Memory Architecture path on
  `codex/afs-production-memory-next-context-handoff-web-001`, based on the
  verified next-context handoff CLI/operator slice.
- Added read-only Web recognition for
  `agentflow_production_memory_next_context_handoff` through
  `apps/web/memory-workbench-production-next-context.js`.
- The view renders selected local handoff JSON as a task handoff canvas with
  next context refs, blocked refs, no-provider controls, and non-claim
  boundaries.
- Boundary kept: no provider call, no Company KB write, no durable memory
  write, no directory scan, no browser persistence, no workflow execution from
  Web, no Loulan-specific inspector, no human acceptance, and no business
  validation claim.
- Verification so far:
  - `data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_web_static_production_memory_next_context_handoff.py -q` -> 2 passed.
  - `data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_web_static_production_memory_next_context_handoff.py tests/test_web_static_production_memory_operator_loop.py tests/test_web_static_company_kb_feedback_packet.py tests/test_web_static_production_memory_session_report.py tests/test_web_static_production_memory_loop.py tests/test_web_static_artifact_workspace.py tests/test_web_static_artifact_boundaries.py tests/test_web_memory_static_structure.py tests/test_web_memory_canvas_static.py -q` -> 27 passed.
  - `data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_next_context_handoff.py tests/test_production_memory_operator_loop.py tests/test_contract_examples.py tests/test_cli_command_registry_boundaries.py tests/test_web_static_production_memory_next_context_handoff.py -q` -> 33 passed.
  - `data\processed\venvs\afs-py312\Scripts\python.exe -m pytest` -> 722 passed on Python 3.12.12.
  - `git diff --check` -> exit 0; CRLF normalization warnings only.

## 2026-06-02 - Production Memory Next Context Handoff 001

- Continued the generic Production Memory Architecture path on
  `codex/afs-production-memory-next-context-handoff-001`, based on the
  verified operator-loop Web slice.
- Added `agentflow/memory/production_next_context.py` and
  `production-memory-loop-next-context-handoff`.
- The handoff converts a no-provider `production_memory_loop_run.json` into
  `next_context_handoff.json` and `.md` for the next AI task. It lists
  `next_context_refs` separately from `blocked_refs`, includes a bounded task
  prompt, and repeats non-claim boundaries.
- Integrated the handoff into `production-memory-loop-run-operator-no-provider`
  so one local operator run now emits run/context/readiness/next pass,
  next-context handoff, session report, Company KB candidate packet, and
  operator manifest.
- Boundary kept: no provider call, no Company KB write, no durable memory
  write, no next-pass execution, no human acceptance, and no business
  validation claim.
- Verification so far:
  - `data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_next_context_handoff.py -q` -> 3 passed.
  - `data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_next_context_handoff.py tests/test_production_memory_operator_loop.py tests/test_web_static_production_memory_operator_loop.py -q` -> 7 passed.
  - `data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_next_context_handoff.py tests/test_production_memory_operator_loop.py tests/test_production_memory_loop.py tests/test_contract_examples.py tests/test_cli_command_registry_boundaries.py tests/test_web_static_production_memory_operator_loop.py -q` -> 43 passed.
  - `data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main --help` -> passed; `production-memory-loop-next-context-handoff` is visible.
  - CLI smoke wrote ignored `next_context_handoff.json` and `.md` from a no-provider run and from the one-command operator loop.
  - `data\processed\venvs\afs-py312\Scripts\python.exe -m pytest` -> 720 passed on Python 3.12.12.

## 2026-06-02 - Production Memory Operator Loop Web 001

- Continued the generic Production Memory Architecture path on
  `codex/afs-production-memory-operator-loop-web-001`, based on the verified
  operator-loop CLI slice.
- Added read-only Web recognition for
  `agentflow_production_memory_operator_loop_run` through
  `apps/web/memory-workbench-production-operator-loop.js`.
- The view renders operator-loop nodes, generated artifact refs, Company KB
  feedback candidate-only boundary, no-provider controls, and non-claim
  boundaries from explicitly selected local JSON only.
- Boundary kept: no provider call, no Company KB write, no durable memory
  write, no directory scan, no browser persistence, no workflow execution from
  Web, no Loulan-specific inspector, no human acceptance, and no business
  validation claim.
- Verification so far:
  - `data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_web_static_production_memory_operator_loop.py -q` -> 2 passed.
  - `data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_web_static_production_memory_operator_loop.py tests/test_web_static_company_kb_feedback_packet.py tests/test_web_static_production_memory_session_report.py tests/test_web_static_production_memory_loop.py tests/test_web_static_artifact_workspace.py tests/test_web_static_artifact_boundaries.py tests/test_web_memory_static_structure.py tests/test_web_memory_canvas_static.py -q` -> 25 passed.
  - `data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_operator_loop.py tests/test_company_kb_feedback_packet.py tests/test_agentflow_contract_audit.py tests/test_contract_examples.py tests/test_cli_command_registry_boundaries.py tests/test_web_static_production_memory_operator_loop.py -q` -> 40 passed.
  - `data\processed\venvs\afs-py312\Scripts\python.exe -m pytest` -> 717 passed on Python 3.12.12.
  - `git diff --check` -> exit 0; CRLF normalization warnings only.

## 2026-06-02 - Production Memory Operator Loop 001

- Continued the generic Production Memory Architecture path on
  `codex/afs-production-memory-operator-loop-001`, based on the verified
  Company KB feedback Web slice.
- Added `agentflow/memory/production_operator_loop.py` and
  `production-memory-loop-run-operator-no-provider`.
- The command runs the full no-provider operator chain from one
  `agentflow_production_memory_loop` JSON through run/context/readiness/next
  pass, session report, Company KB candidate packet, and an operator-loop
  manifest.
- Boundary kept: no provider call, no Company KB write, no durable memory
  write, no workflow execution beyond no-provider artifact assembly, no human
  acceptance claim, and no business validation claim.
- Verification so far:
  - `data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_operator_loop.py -q` -> 2 passed.
  - `data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main --help` -> passed; `production-memory-loop-run-operator-no-provider` is visible.
  - `data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main production-memory-loop-run-operator-no-provider examples/agentflow/production_memory_loop.example.json --generated-at 2026-06-02T01:00:00+08:00 --source-kb-status restructuring_or_unknown --output data/processed/runs/production_memory_loop/operator_loop` -> ready; wrote run, session report, Company KB candidate packet, and operator manifest under ignored runtime output.
  - `data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_production_memory_operator_loop.py tests/test_production_memory_loop.py tests/test_production_memory_session_report.py tests/test_company_kb_feedback_packet.py tests/test_agentflow_contract_audit.py tests/test_contract_examples.py tests/test_cli_command_registry_boundaries.py -q` -> 54 passed.
  - `data\processed\venvs\afs-py312\Scripts\python.exe -m pytest` -> 715 passed.

## 2026-06-02 - Company KB Feedback Web 001

- Continued the generic Production Memory Architecture path on
  `codex/afs-company-kb-feedback-web-001`, based on the verified Company KB
  feedback packet branch.
- Added read-only Web recognition for
  `agentflow_company_kb_feedback_candidate_packet` through
  `apps/web/memory-workbench-company-kb-feedback.js`.
- The view renders candidate items, explicit non-promotions, source KB status,
  human-review requirement, Company KB write-disabled state, durable memory
  write-disabled state, and non-claim boundaries from explicitly selected
  local JSON only.
- Boundary kept: no Company source KB write, no durable memory write, no
  provider call, no directory scan, no browser persistence, no Loulan-specific
  inspector, no human acceptance, and no business validation claim.
- Verification so far:
  - `data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_web_static_company_kb_feedback_packet.py -q` -> 2 passed.
  - `data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_web_static_company_kb_feedback_packet.py tests/test_web_static_production_memory_session_report.py tests/test_web_static_production_memory_loop.py tests/test_web_static_artifact_workspace.py tests/test_web_static_artifact_boundaries.py tests/test_web_memory_static_structure.py tests/test_web_memory_canvas_static.py -q` -> 23 passed.
  - `data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_company_kb_feedback_packet.py tests/test_agentflow_contract_audit.py tests/test_contract_examples.py tests/test_cli_command_registry_boundaries.py tests/test_web_static_company_kb_feedback_packet.py -q` -> 38 passed.
  - Browser-level smoke using Python Playwright was attempted, but blocked by
    missing `playwright` in the Python 3.12 venv.
  - `data\processed\venvs\afs-py312\Scripts\python.exe -m pytest` -> 713 passed.
  - `git diff --check` -> exit 0; CRLF normalization warnings only.

## 2026-06-02 - Production Memory Loop 001

- Implemented `AFS-PRODUCTION-MEMORY-LOOP-001` as a generic AFS
  Production Memory Architecture slice, not a project-specific content
  production extension.
- Added a no-provider contract and CLI path:
  `agentflow/memory/production_loop.py`,
  `agentflow/memory/production_next_pass.py`,
  `agentflow/memory/production_feedback.py`,
  `apps/cli/production_memory_loop_command.py`,
  `production-memory-loop-validate`, and
  `production-memory-loop-run-no-provider`.
- Added `production-memory-loop-draft-feedback` to draft feedback, candidate
  memory, and a pending promotion decision template without mutating the source
  loop or promoting memory.
- Added `production-memory-loop-review-promotion` and
  `production-memory-loop-run-reviewed-feedback-no-provider` so a reviewed
  operator decision can be overlaid into a derived no-provider loop without
  mutating the source loop or writing durable memory.
- Added the required example root identifiers:
  `kind: agentflow_production_memory_loop` and
  `schema_version: production-memory-loop/v1`.
- Added Web read-only generic production-memory canvas support through
  explicit selected JSON artifacts only. No directory scan, browser
  persistence, provider execution, or project-specific inspector was added.
- Added candidate-only Company KB feedback records under
  `docs/company-kb-feedback-candidates/`; no Company source KB write.
- Optional Image2/Kling validation was not attempted because it is outside the
  core DoD and requires a separate gated provider environment.
- Verification:
  - `python -m pytest tests/test_production_memory_loop.py -q` -> 10 passed.
  - `python -m pytest tests/test_production_memory_loop.py tests/test_contract_examples.py tests/test_cli_command_registry_boundaries.py -q` -> 35 passed.
  - `python -m pytest tests/test_production_memory_promotion_overlay.py tests/test_production_memory_feedback_capture.py tests/test_production_memory_loop.py tests/test_contract_examples.py tests/test_cli_command_registry_boundaries.py -q` -> 45 passed.
  - `python -m apps.cli.main --help` -> passed; new production-memory commands are visible.
  - `python -m apps.cli.main production-memory-loop-validate examples/agentflow/production_memory_loop.example.json` -> passed.
  - `python -m apps.cli.main production-memory-loop-run-no-provider examples/agentflow/production_memory_loop.example.json --output data/processed/runs/production_memory_loop/no_provider` -> ready; 3 included refs, 3 blocked refs, and `next_pass_bundle.json` written.
  - `python -m apps.cli.main production-memory-loop-draft-feedback examples/agentflow/production_memory_loop.example.json --target-ref artifact:approved_storyboard:v1 --decision accepted --summary "Carry the reviewed storyboard structure into the next pass." --created-at 2026-06-02T00:00:00+08:00 --output data/processed/runs/production_memory_loop/feedback_capture` -> draft written; promotion decision remains pending.
  - `python -m apps.cli.main production-memory-loop-review-promotion data/processed/runs/production_memory_loop/feedback_capture/production_memory_feedback_capture.json --decision promoted --rationale "Candidate is traceable to reviewed feedback." --decided-at 2026-06-02T00:05:00+08:00 --output data/processed/runs/production_memory_loop/promotion_decision` -> reviewed promotion decision written.
  - `python -m apps.cli.main production-memory-loop-run-reviewed-feedback-no-provider examples/agentflow/production_memory_loop.example.json --feedback-capture data/processed/runs/production_memory_loop/feedback_capture/production_memory_feedback_capture.json --promotion-decision data/processed/runs/production_memory_loop/promotion_decision/promotion_decision.json --output data/processed/runs/production_memory_loop/reviewed_feedback` -> ready; 4 included refs and 3 blocked refs.
  - Focused Web static suite -> 65 passed.
  - Web static HTTP smoke at `http://127.0.0.1:8771/index.html#memory` -> passed; temporary server stopped.
  - JS syntax checks for touched Web modules -> passed.
  - `python -m pytest` -> 698 passed.
  - `git diff --check` -> exit 0; CRLF normalization warnings only.
- Follow-up boundary: browser-level DOM smoke remains blocked by no detected
  Chrome/Edge executable and no local Playwright package; optional provider
  validation remains blocked because image/video/provider config gates are
  unset.

## 2026-06-02 - Production Memory Session Report 001

- Continued the generic AFS Production Memory Architecture path on
  `codex/afs-production-memory-session-report-001`, based on the verified
  `AFS-PRODUCTION-MEMORY-LOOP-001` commit.
- Added a read-only no-provider operator session report:
  `agentflow/memory/production_session.py` and
  `production-memory-loop-session-report`.
- Added read-only Web recognition for
  `agentflow_production_memory_session_report` through
  `apps/web/memory-workbench-production-session.js`; it renders selected
  session report JSON only and adds no directory scan, browser persistence,
  provider execution, or project-specific inspector.
- The report summarizes included refs, blocked refs, optional feedback capture,
  optional reviewed promotion decision, next operator action, and non-claim
  boundaries. It does not mutate source loops, scan directories, call
  providers, write durable memory, or claim human acceptance.
- Added focused tests in `tests/test_production_memory_session_report.py`.
- Verification so far:
  - `python -m pytest tests/test_production_memory_session_report.py -q` -> 6 passed.
  - `python -m pytest tests/test_production_memory_session_report.py tests/test_production_memory_promotion_overlay.py tests/test_production_memory_feedback_capture.py tests/test_production_memory_loop.py tests/test_cli_command_registry_boundaries.py -q` -> 27 passed.
  - `python -m pytest tests/test_web_static_production_memory_session_report.py tests/test_web_static_production_memory_loop.py tests/test_web_memory_static_structure.py tests/test_web_memory_canvas_static.py tests/test_web_static_artifact_workspace.py tests/test_web_static_artifact_boundaries.py -q` -> 21 passed.
  - `python -m apps.cli.main --help` -> passed; `production-memory-loop-session-report` is visible.
  - `python -m apps.cli.main production-memory-loop-session-report data/processed/runs/production_memory_loop/reviewed_feedback/production_memory_loop_run.json --feedback-capture data/processed/runs/production_memory_loop/feedback_capture/production_memory_feedback_capture.json --promotion-decision data/processed/runs/production_memory_loop/promotion_decision/promotion_decision.json --generated-at 2026-06-02T00:10:00+08:00 --output data/processed/runs/production_memory_loop/session_report` -> ready; wrote JSON and Markdown report under ignored runtime output.
  - `python -m pytest tests/test_web_static_production_memory_session_report.py -q` -> 2 passed.
  - Python Playwright browser smoke loaded `apps/web/index.html#memory`,
    imported the workbench modules in the browser context, parsed a generated
    `agentflow_production_memory_session_report`, and returned
    `projectFormat: agentflow_production_memory_session_report`,
    `state: pass ready`, and `nextPassAction: prepare_next_pass`. Two
    `ERR_CONNECTION_REFUSED` console errors were observed from the local bridge
    not running; this was recorded as environment noise, not provider
    execution.
  - `python -m pytest` -> 706 passed.
  - `data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_web_static_production_memory_session_report.py tests/test_production_memory_loop.py tests/test_production_memory_session_report.py tests/test_cli_command_registry_boundaries.py -q` -> 20 passed on Python 3.12.12.
  - `data\processed\venvs\afs-py312\Scripts\python.exe -m pytest` -> 706 passed on Python 3.12.12.
  - `git diff --check` -> exit 0; CRLF normalization warnings only.

## 2026-06-02 - Company KB Feedback Candidate Packet 001

- Continued the generic Production Memory Architecture path on
  `codex/afs-company-kb-feedback-packet-001`, based on the verified session
  report branch.
- Added a candidate-only Company KB feedback packet:
  `agentflow/memory/company_kb_feedback.py` and
  `production-memory-loop-company-kb-candidates`.
- Added the committed example
  `examples/agentflow/company_kb_feedback_candidate_packet.example.json` and
  registered it in the AgentFlow contract registry.
- The packet is generated from a production-memory session report and records
  reusable project lessons as candidates only. It keeps
  `writes_company_kb: false`, `writes_long_term_memory: false`,
  `promotion_status: candidate_only`, and `requires_human_review: true`.
- Added candidate-only records under `docs/company-kb-feedback-candidates/`;
  no Company source knowledge-base write.
- Verification so far:
  - `data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_company_kb_feedback_packet.py -q` -> 5 passed on Python 3.12.12.
  - `data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_contract_examples.py -q` -> 24 passed on Python 3.12.12.
  - `data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main --help` -> passed; `production-memory-loop-company-kb-candidates` is visible.
  - `data\processed\venvs\afs-py312\Scripts\python.exe -m apps.cli.main production-memory-loop-company-kb-candidates data/processed/runs/production_memory_loop/session_report/production_memory_session_report.json --generated-at 2026-06-02T00:20:00+08:00 --source-kb-status restructuring_or_unknown --output data/processed/runs/production_memory_loop/company_kb_candidates` -> candidate_only; wrote JSON and Markdown report under ignored runtime output.
  - `data\processed\venvs\afs-py312\Scripts\python.exe -m pytest tests/test_company_kb_feedback_packet.py tests/test_contract_examples.py tests/test_agentflow_contract_audit.py tests/test_production_memory_session_report.py tests/test_production_memory_loop.py tests/test_cli_command_registry_boundaries.py -q` -> 52 passed on Python 3.12.12.
  - `data\processed\venvs\afs-py312\Scripts\python.exe -m pytest` -> 711 passed on Python 3.12.12.
  - `git diff --check` -> exit 0; CRLF normalization warnings only.

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

## 2026-05-31 - Workflow Engine Shared Helper Consolidation

- Continued the workflow-engine cleanup under the updated project operating
  rules: task mode `Deep`, no subagent, write scope limited to shared
  workflow-engine node helpers and project records.
- Remote-provider policy: no remote provider calls. Verification used local
  tests only.
- Extended `narratocut/workflow_engine/node_artifacts.py` with the shared
  `load_json_object` helper.
- Reused `node_artifacts.require_input`, `require_output`, and
  `load_json_object` from focused node modules instead of keeping duplicate
  local helper definitions in assembly, BGM, subtitle burn, cover, package,
  transcription, highlight, OCR, NarratoStudio, and PosterFlow nodes.
- Kept node function names, registry wiring, workflow definitions, provider
  gates, and artifact schemas unchanged. Imports use local aliases where that
  keeps the existing node bodies stable.
- Boundary kept: internal helper consolidation only. No workflow execution
  order, harness gate, provider behavior, generated artifact format, human
  acceptance, business validation, or durable Memory behavior changed.
- Verification:
  - `python -m py_compile` on the touched workflow-engine modules -> passed.
  - focused workflow/helper surface:
    `pytest tests/test_workflow_runner.py tests/test_workflow_registry.py tests/test_workflow_full_mock_pipeline.py tests/test_highlight_workflow_nodes.py tests/test_highlight_workflows.py tests/test_video_to_transcript_workflow.py tests/test_video_to_transcript_real_asr_workflow.py tests/test_video_to_highlight_clip_plan_workflow.py tests/test_video_to_highlight_clip_plan_real_asr_workflow.py tests/test_ocr_fusion_workflows.py tests/test_video_assembly_workflow.py tests/test_subtitle_burn_workflow.py tests/test_bgm_mix_workflow.py tests/test_bgm_verified_metadata.py tests/test_cover_export_workflow.py tests/test_finished_package_workflow.py tests/test_narratostudio_workflow.py tests/test_posterflow_workflow.py tests/test_product_golden_path_workflows.py -q`
    -> 81 passed.
  - `pytest -q` -> 662 passed.
  - `git diff --check` -> no whitespace errors; CRLF normalization warnings
    only.
  - Line counts: largest workflow-engine files remain under 300 lines:
    `highlight_nodes.py` 289, `posterflow_nodes.py` 261, `nodes.py` 260,
    `node_artifacts.py` 139.

## 2026-05-31 - Workflow Engine Node Helper Slimming

- Continued the workflow-engine cleanup under the updated project operating
  rules: task mode `Deep`, no subagent, write scope limited to the
  `narratocut.workflow_engine` base node/helper layer and project records.
- Remote-provider policy: no remote provider calls. Verification used local
  tests only.
- Split artifact JSON loading, schema validation, and workflow state fallback
  helpers out of `narratocut/workflow_engine/nodes.py` into
  `narratocut/workflow_engine/node_artifacts.py`.
- Kept `nodes.py` as the base node orchestration and registry entry point:
  `default_node_registry`, `probe_video_metadata`, and
  `check_ffmpeg_available` remain available from the same module path for
  existing imports and tests.
- Boundary kept: this was an internal module-size and responsibility split
  only. No workflow contract, execution order, provider gate, harness quality
  check, artifact schema, human acceptance, business validation, or durable
  Memory behavior changed.
- Verification:
  - `python -m py_compile narratocut/workflow_engine/nodes.py narratocut/workflow_engine/node_artifacts.py`
    -> passed.
  - `pytest tests/test_workflow_runner.py tests/test_workflow_full_mock_pipeline.py tests/test_video_to_real_clips_workflow.py tests/test_clip_plan_to_real_clips_workflow.py tests/test_product_golden_path_workflows.py tests/test_workflow_registry.py -q`
    -> 15 passed.
  - `pytest -q` -> 662 passed.
  - Line counts: `nodes.py` 260, `node_artifacts.py` 128.

## 2026-05-31 - MiniMax Provider Smoke Slimming

- Continued the provider cleanup under the updated project operating rules:
  task mode `Deep`, no subagent, write scope limited to MiniMax provider smoke
  implementation/tests and project records.
- Remote-provider policy: no remote provider calls. Verification used mocked
  MiniMax `urlopen` paths and local tests only.
- Split request planning and safe provider-config resolution into
  `narratocut/model_gateway/minimax_image_plan.py`.
- Split runtime subject-reference validation, prompt-pack construction, and
  image-output summaries into
  `narratocut/model_gateway/minimax_image_runtime.py`.
- Kept public compatibility through
  `narratocut/model_gateway/minimax_image_smoke.py`:
  `build_minimax_image_request_plan` and `run_minimax_image_smoke` remain
  importable from the original module.
- Boundary kept: MiniMax smoke remains a gated legacy evidence/operator path,
  not the visible product path, human acceptance, business validation, or a
  durable Memory runtime.
- Verification:
  - `pytest tests/test_minimax_image_smoke.py tests/test_memory_advantage_demo_012.py tests/test_posterflow_provider.py -q`
    -> 32 passed.
  - `python -m py_compile narratocut/model_gateway/minimax_image_smoke.py narratocut/model_gateway/minimax_image_plan.py narratocut/model_gateway/minimax_image_runtime.py`
    -> passed.
  - Line counts: `minimax_image_smoke.py` 97,
    `minimax_image_plan.py` 151, `minimax_image_runtime.py` 61.

## 2026-05-31 - Kling Provider Smoke Slimming

- Applied the updated project operating rules before continuing the provider
  cleanup: classified the slice as `Deep` because it touches provider/media
  smoke code, architecture boundaries, and evidence claims.
- Kept the work in the current checkout instead of opening a subagent lane:
  the write scope was single-purpose and already in the dirty slimming branch
  context. No subagent was needed.
- Remote-provider policy: no remote provider calls. Verification used mocked
  HTTP/curl paths only.
- Split Kling video runtime concerns out of
  `narratocut/model_gateway/kling_video_smoke.py` into
  `narratocut/model_gateway/kling_video_runtime.py`.
- Split the oversized Kling smoke test surface into focused I2V, T2V, curl,
  request-plan, and task-recovery tests with shared safe fixtures in
  `tests/kling_video_smoke_helpers.py`.
- Kept public smoke entrypoints stable:
  `run_kling_i2v_smoke`, `run_kling_t2v_smoke`, and
  `resume_kling_video_task`.
- Boundary kept: direct Kling smoke remains a legacy evidence/operator path,
  not the visible product path, human acceptance, business validation, or a
  durable Memory runtime.
- Verification:
  - `pytest tests/test_kling_video_smoke.py tests/test_kling_video_t2v_smoke.py tests/test_kling_video_curl_smoke.py tests/test_kling_video_request_plan.py tests/test_kling_video_task_recovery.py -q`
    -> 16 passed.
  - `python -m py_compile narratocut/model_gateway/kling_video_smoke.py narratocut/model_gateway/kling_video_runtime.py tests/test_kling_video_smoke.py tests/test_kling_video_t2v_smoke.py tests/test_kling_video_curl_smoke.py tests/test_kling_video_task_recovery.py tests/test_kling_video_request_plan.py tests/kling_video_smoke_helpers.py`
    -> passed.
  - Line counts: `kling_video_smoke.py` 267,
    `kling_video_runtime.py` 176, largest touched test 181.
  - `python -m apps.cli.main --help` still surfaces
    `memory-video-pipeline-*` and does not surface direct Kling provider smoke.


## Archive Policy

- Keep this root log focused on current maintenance and recent evidence pointers.
- Put long historical summaries in `docs/archive/` and detailed evidence in focused handoff, maintenance, or workbench documents.
- Do not use DEVLOG entries alone as human acceptance, business validation, or durable memory promotion evidence.
