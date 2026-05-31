# AFS-MAINLINE-STAGING-BUNDLE-001 - Mainline Staging Bundle

Status: pushed as ready PR #72 on `codex-mainline-slimming-staging`;
PR #73 has merged the Local Alpha 0.4 mainline base into `master`, and PR #72
is now retargeted to `master`.

This bundle converts the current dirty checkout into a coherent integration
plan. It keeps the product surface centered on `memory-video-pipeline-*` and
keeps reviewed hidden provider/demo support in a separate CLI registry module.

No remote provider calls were made. No generated media, provider config, local
secrets, ignored runtime artifacts, or Company knowledge-base files belong in
this bundle.

## Bundle Strategy

Use one integration bundle with two explicit layers:

- Product mainline: operating docs, contracts, memory video pipeline, Web
  workbench, workflow-engine slimming, and evidence docs.
- Reviewed support/evidence: hidden Kling/MiniMax commands, provider adapters,
  numbered DEMO-012/015 runtime preservation, and RECORDING-016 operator
  script.

Reason: `apps/cli/command_registry.py` now owns product command registration,
while `apps/cli/support_command_registry.py` owns hidden provider/demo support
registration. The full CLI bootstrap still registers both layers to preserve
existing evidence runbooks, but the source boundary is now reviewable by layer.

## Include

Maintenance and operating projection:

- `AGENTS.md`, `DEVLOG.md`, `TASK_TRACKER.md`
- `docs/README.md`, `docs/archive/`, `docs/maintenance/`
- `docs/company_operating_model.md`
- `docs/agent_operating_roster.md`
- `docs/agent_task_brief_template.md`
- `docs/task_briefs/`
- `docs/retrospectives/`

AgentFlow contracts and memory infrastructure:

- `agentflow/contracts/examples.py`
- `agentflow/memory/promotion.py`
- `agentflow/memory/video_pipeline*.py`
- `examples/agentflow/*.json`
- `tests/test_agentflow_*`, `tests/test_contract_examples.py`
- `tests/test_contract_examples_memory_video_pipeline.py`
- `tests/test_memory_video_pipeline_*.py`
- `tests/test_memory_review_cli.py`

CLI and Web mainline:

- `apps/cli/main.py`
- `apps/cli/command_registry.py`
- `apps/cli/memory_video_pipeline_command.py`
- `apps/cli/memory_review_command.py`
- `apps/web/` static workbench and split CSS/JS modules
- `tests/test_web_*`, `tests/web_static_helpers.py`

Workflow-engine slimming:

- `narratocut/workflow_engine/`
- focused workflow tests touched by the current checkout

Evidence docs and runbooks:

- `docs/handoff/AFS-RUN-PACKAGE-001.md`
- `docs/handoff/AFS-WEB-OPERATOR-002.md`
- `docs/handoff/AFS-MEMORY-QUALITY-002.md`
- `docs/handoff/AFS-MEMORY-PIPELINE-MVP-001.md`
- `docs/handoff/AFS-MEMORY-REVIEW-CLI-001.md`
- `docs/handoff/AFS-POST-DEMO-PRODUCTIZATION-ROADMAP.md`
- `docs/handoff/AFS-MEMORY-ADVANTAGE-DEMO-012.md` through
  `docs/handoff/AFS-MEMORY-ADVANTAGE-RECORDING-016.md`
- `docs/handoff/AFS-COMPETITION-DEMO-RUN-SHEET.md`
- `docs/handoff/AFS-COMPETITION-DEMO-TALK-TRACK.md`
- `docs/local_alpha_0_4*.md`
- `docs/workbench/`

Reviewed support/evidence layer:

- `apps/cli/kling_*`, `apps/cli/minimax_image_command.py`,
  `apps/cli/memory_demo_commands.py`
- `apps/cli/support_command_registry.py`
- `narratocut/model_gateway/`
- `narratostudio/posterflow/minimax_provider.py`
- `narratocut/memory_advantage_demo_012_review_html.py`
- `narratocut/memory_advantage_demo_011_content.py`
- `narratocut/memory_advantage_demo_012*.py`
- `narratocut/memory_advantage_demo_015*.py`
- `pyproject.toml`
- `tests/kling_video_smoke_helpers.py`, `tests/provider_smoke_helpers.py`
- `tests/test_kling_video_*.py`, `tests/test_minimax_image_smoke.py`
- `tests/memory_advantage_demo_012_helpers.py`
- `tests/test_memory_advantage_demo_012.py`
- `tests/test_memory_advantage_demo_015.py`
- `tests/test_posterflow_provider.py`
- `tests/test_recording_016_script.py`
- `tools/staging_preflight.py`
- `tests/test_staging_preflight.py`
- `tools/run_memory_advantage_recording_016.ps1`

## Exclude

- `data/processed/`, `data/raw/`, local media, model caches, screenshots, and
  maintenance backups.
- `.env`, `.dev.vars`, `configs/models.yaml`, provider config JSON, cookies,
  tokens, signed URLs, real API keys, or private credential material.
- Python `__pycache__` and other generated caches.
- Any copied source content from
  `D:\Learning materials\Learning_notes\Company`.

## Verification

Focused verification already run for this bundle:

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests/test_memory_video_pipeline_protocol.py tests/test_memory_video_pipeline_workflow.py tests/test_memory_video_pipeline_review.py tests/test_memory_video_pipeline_observation.py tests/test_memory_video_pipeline_presentation.py tests/test_memory_review_cli.py -q
# 27 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests/test_agentflow_asset_memory_validator.py tests/test_agentflow_contract_helpers.py tests/test_contract_examples.py -q
# 52 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests/test_web_memory_static_structure.py tests/test_web_memory_sample_static.py tests/test_web_memory_interaction_static.py tests/test_web_memory_feedback_static.py tests/test_web_memory_canvas_static.py tests/test_web_memory_artifact_summary_static.py tests/test_web_static_artifact_boundaries.py tests/test_web_static_artifact_viewer.py tests/test_web_static_artifact_workspace.py tests/test_web_production_mode_static.py tests/test_web_production_feedback_static.py tests/test_web_production_bridge.py -q
# 63 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests/test_workflow_runner.py tests/test_workflow_run_contract.py tests/test_workflow_registry.py tests/test_workflow_loader.py tests/test_workflow_cli.py tests/test_memory_video_pipeline_workflow.py tests/test_video_to_finished_package_local_asr_workflow.py tests/test_posterflow_workflow.py -q
# 19 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests/test_kling_video_request_plan.py tests/test_kling_video_smoke.py tests/test_kling_video_t2v_smoke.py tests/test_kling_video_curl_smoke.py tests/test_kling_video_task_recovery.py tests/test_minimax_image_smoke.py tests/test_posterflow_provider.py tests/test_memory_advantage_demo_012.py tests/test_memory_advantage_demo_015.py tests/test_recording_016_script.py -q
# 61 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests/test_cli_command_registry_boundaries.py tests/test_memory_video_pipeline_workflow.py tests/test_minimax_image_smoke.py tests/test_kling_video_smoke.py tests/test_kling_video_t2v_smoke.py tests/test_memory_advantage_demo_012.py tests/test_memory_advantage_demo_015.py tests/test_web_production_bridge.py -q
# 52 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests/test_memory_advantage_demo_012.py tests/test_contract_examples.py tests/test_contract_examples_memory_video_pipeline.py -q
# 39 passed
```

Before actual staging, rerun:

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests/test_agentflow_roadmap_docs.py -q
.\.venv\Scripts\python.exe -B -m apps.cli.main --help
.\.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
git diff --check
git status --short --ignored data/processed
```

Final broad verification for this drafting pass:

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain -q
# 675 passed
```

Current checkout verification refresh on 2026-05-31:

```powershell
.\.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
# status: pass

.\.venv\Scripts\python.exe -B -m pytest --assert=plain -p no:cacheprovider --basetemp data\processed\pytest-basetemp\full-current
# 675 passed

.\.venv\Scripts\python.exe -B -m apps.cli.main --help
.\.venv\Scripts\python.exe -B -m apps.cli.main version
# version: 0.1.0
```

Staging execution refresh on 2026-05-31:

```powershell
git diff --cached --name-only
# 182 staged files

git diff --cached --check
# pass

.\.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
# status: pass

.\.venv\Scripts\python.exe -B -m pytest --assert=plain -p no:cacheprovider --basetemp data\processed\pytest-basetemp\full-staged
# 675 passed

git commit -m "feat(agentflow): add memory pipeline mainline bundle"
# fce21bd
```

Remote review chain on 2026-05-31:

- PR #73: `codex-local-alpha-0-4-mainline-sync` -> `master`.
  This published the local `master` base that was ahead of `origin/master` and
  merged as `94401afe`.
- PR #72: `codex-mainline-slimming-staging` ->
  `master`. After #73 merged, this keeps the slimming bundle review scoped to
  the bundle commit series on top of the Local Alpha 0.4 base now in `master`.

Remote readiness follow-up on 2026-05-31:

- Initial GitHub read checks returned PR #73 and PR #72 as open, draft, and
  `mergeable=true`.
- Commit status and workflow-run lookups returned no status/check evidence for
  either PR head, so this is not a remote-CI-passed claim.
- A #73 readiness comment was added with the local verification and
  non-claim boundaries.
- PR #73 was marked ready for review after a retry. At that point, PR #72
  remained draft and dependent until PR #73 was reviewed or merged.
- After the #73 branch was cleaned and repushed at `35bba58`, PR #72 was
  rebased on top of that updated base and pushed with `--force-with-lease`.
  GitHub then reported PR #72 as draft and `mergeable=true` at head `5962a2a`.
- PR #73 was merged to `master` as `94401afe`; PR #72 was then rebased on top
  of `origin/master`, retargeted to `master`, and marked ready for review at
  head `0c70bf4` after a readiness comment was added.

PR #72 review follow-up on 2026-05-31:

- Automated review found that memory video pipeline review could report source
  image parity when an I2V manifest lacked `input_image.sha256` or was not
  actually an I2V manifest.
- The review path now requires `api_family == i2v` and a non-empty
  `input_image.sha256` before computing `same_source_image_sha256`.
- Regression tests cover missing source hashes and non-I2V manifest rejection.

## Commit Boundary

This bundle can become one integration commit only if final verification still
passes and the staged diff contains no local-only artifacts. If the user wants a
smaller series, split into:

1. maintenance and operating docs;
2. memory pipeline plus contracts/examples;
3. Web workbench;
4. workflow-engine slimming;
5. reviewed hidden support/evidence layer.
