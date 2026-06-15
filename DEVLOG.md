# Devlog

## 2026-06-15 - Experimental Video Revision Contract And Fail-Closed Carry Guard

- Added an experimental `video_revision` Runtime contract behind
  `AFS_ENABLE_EXPERIMENTAL_VIDEO_REVISION`:
  `VideoRevisionRequest`, `/video-revisions/preflight`, and `/video-revisions`.
- The new route records best-effort preserve/change intent, temporal scope,
  locked aspects, original base lineage, and a safe
  `afs_video_revision_safe_manifest.v0.1`; it does not submit to Kling yet.
- Added Studio Runtime client methods and a video-node menu entry to enable an
  experimental revision draft from an accepted base video job.
- Hardened Studio generation preflight so fixed assets that are mentioned by
  label but not connected/injected/excluded fail closed before any paid
  image/video submit.
- Improved stale Runtime route failures with route/status metadata and an
  explicit "Restart the 8790 Runtime Service from the current branch" message.
- Added a safe-error guard so unsafe `video_revision` base identifiers are
  rejected as `invalid_video_revision` without leaking paths or secret-like
  fragments.

Verification:

```text
pytest tests/test_api_runtime_video_generations.py tests/test_api_runtime_video_revisions.py -q -> 11 passed
pytest tests/test_api_runtime_context_resolver.py -q -> 17 passed
pytest tests/test_web_studio_static.py -q -> 21 passed
Studio JS node --check all files -> passed
pytest -q -> 390 passed / 527 deselected
pytest -m legacy -q -> 527 passed / 390 deselected
tools/maintenance_audit.py -> failed=0, warning=4
runtime-service-openapi-export -> docs/openapi/afs-runtime-service.openapi.json updated
git diff --check -> exit 0, CRLF notices only
```

Boundary:

- This is a contract/UI safety slice, not proof that Kling can perform localized
  video editing. It supports the desired workflow vocabulary while preserving
  the claim boundary: targeted revisions are best-effort until provider-specific
  V2V/masked/temporal controls are verified.

## 2026-06-15 - Video Localized Regeneration Requirement Record

- Recorded the current Claude/browser feedback issues as project follow-up:
  stale Runtime route mismatch after code updates, multi-node fixed-asset
  detection inconsistency, fixed-asset carry confirmation inconsistency, and
  provider framing preference for wide/full shots.
- Added `docs/handoff/AFS-VIDEO-LOCALIZED-REGEN-20260615.md` to distinguish the
  current Kling I2V plumbing from the user's desired video revision behavior:
  accepted base video -> targeted prompt edit -> preserve unrelated content.
- Added backlog items for multi-node asset/carry consistency, video revision
  contract design, and A/B drift scoring.

Verification:

```text
Documentation-only change; no provider call, code execution, or generated media.
```

Boundary:

- Current Studio video support remains I2V-oriented runtime/provider plumbing,
  not guaranteed localized video editing.
- This record is not human acceptance, business validation, or durable Company
  OS rule promotion.

## 2026-06-14 - Browser Repair Loop 005 Baseline And Guards

- Brought the Loop 003 browser QA red baseline into the active line as
  `docs/maintenance/AFS-AGENT-BROWSER-QA-LOOP-003.md`, so the known issues are
  auditable from the current branch instead of only from a stale QA branch.
- Added an L1 gap audit for the current north-star objective:
  `docs/maintenance/AFS-BROWSER-QA-LOOP-005-GAP-AUDIT.md`.
- Added explicit QAL003 regression anchors to Studio static tests for:
  fixed-asset pre-submit interlock, generated-image promotion entrypoints,
  Runtime-backed asset detail/remove/exclude actions, recent/current project
  visibility, and Kling no-sound UI.
- Added keyframe/video generation manifest safety tests that assert generated
  responses and persisted safe manifests do not expose provider raw payloads,
  provider URLs, media bytes, secrets, or local absolute paths.
- Hardened live LLM prompt optimization after browser QA reproduced the prior
  422 class: prompt-enhancement calls now send a formatter system message,
  retry once on chatty/non-sectional output, and salvage actual prompt text
  from repeated LLM article output without restoring the old local deterministic
  optimizer as the primary path.
- Normalized legacy provider descriptor gates such as `NARRATOCUT_ALLOW_REMOTE_*`
  to the current `AFS_ALLOW_REMOTE_*` names in the provider registry path, so
  ignored external provider configs no longer disagree with Studio gate state.
- Fixed a live Kling I2V P0 found during agent-led QA: the remote submit could
  succeed, but Runtime returned 422 before writing the safe manifest because an
  adapter `output_dir` absolute path was persisted into video task state. Runtime
  now strips `output_dir` before persistence and injects it only transiently for
  polling.
- Fixed a context bundle trace duplicate where a one-run excluded asset also
  appeared as `not_connected_to_target`.
- Ran Round A browser/live checks for T2I optimize, MiniMax image generation,
  generated image asset fixation, Runtime-backed asset detail, carry
  confirmation, one-run asset exclusion, refresh persistence, project isolation,
  video first-frame guard, Kling no-sound UI, and Kling I2V submit/poll/preview.
- Ran Round B valid-media runtime/browser checks with a real 1672x941 reference:
  I2I succeeded, fixed-asset carry preflight/submit succeeded, one-run asset
  exclusion succeeded, Kling I2V reached `succeeded` with a preview, and the
  Studio page loaded the target project with no console warn/error and no
  unsupported audio/sound UI.
- Fixed a new Round B P1 guardrail gap: tiny reference media could reach paid
  MiniMax/Kling provider paths and fail remotely. Provider descriptors now carry
  `min_reference_image_edge_px`; MiniMax image and Kling video default to 256px,
  and Runtime blocks too-small references before dispatch/submit with
  `provider_calls_started=false`.
- Ran Round C after the guardrail fix. It covered T2I, upload, I2I, fixed asset
  promote/detail, fixed-asset carry, one-run exclusion, Kling I2V recovery, and
  Studio load. Round C found one new P1: Studio image-model selection could mask
  the LLM provider fields and return 422 `not_requested`. `minimax_text_requested`
  now checks `llm_provider`, `llm_model`, then `model`, and the live retry
  returned `provider_calls_started=true` / `status=applied`.
- Ran Round D and Round E as two consecutive clean role-matrix rounds. Each
  round used one remote LLM optimization, four MiniMax image submits, and one
  Kling I2V submit. Both rounds passed remote optimize, T2I, upload/I2I, fixed
  asset promote/detail, fixed carry preflight+submit, one-run exclusion, Kling
  I2V safe preview, and Studio load with no unsupported sound/audio UI and no
  console warn/error.
- Added `docs/handoff/AFS-HUMAN-ACCEPTANCE-RUNBOOK-005.md` as the current
  human acceptance entrypoint. The project can claim runtime/browser
  verification for the tested MVP paths, but not human acceptance until the user
  runs the runbook and records pass/fail plus creative-quality scores.

Verification so far:

```text
Loop 005 focused tests:
tests/test_web_studio_static.py
tests/test_api_runtime_generation_manifest_safety.py
selected preflight/token/exclusion tests

26 passed, 1 warning

Additional focused tests:
tests/test_openai_compatible_provider.py
selected prompt optimizer retry/salvage tests
selected provider registry gate-normalization test
selected context resolver asset-exclusion test
selected video task-state path hygiene tests

All selected tests passed.

Round B focused reference/provider guards:
tests/test_api_runtime_keyframe_reference_assets.py
tests/test_api_runtime_video_generations.py
tests/test_provider_adapter_registry.py

37 passed, 1 warning

Prompt optimizer regression after Round C:
tests/test_api_runtime_prompt_memory_loop.py

17 passed, 1 warning

Browser/runtime evidence:
runs/agent_browser_qa_loop_005/round_c_runtime_summary.json
runs/agent_browser_qa_loop_005/round_d3_runtime_summary.json
runs/agent_browser_qa_loop_005/loop005-round-e-clean-1_runtime_summary.json
runs/agent_browser_qa_loop_005/round_d3_studio_load.png
runs/agent_browser_qa_loop_005/round_e_studio_load.png
```

Boundary:

- Loop 005 runtime/browser verification is closed for the tested MVP paths after
  two consecutive clean rounds.
- This is not human acceptance, business validation, or durable-memory
  promotion.
- MiniMax identity similarity and Kling first-frame/motion quality remain
  human-scored through `docs/handoff/AFS-HUMAN-ACCEPTANCE-RUNBOOK-005.md`.

## 2026-06-14 - Asset Exclusion Preflight And Browser Repair Loop 004

- Added generation preflight support for fixed-asset carry review before paid
  submit: keyframe/video preflight, request-level temporary asset exclusions,
  preflight consistency token, and safe visual asset detail endpoint.
- Added Studio generation confirmation when fixed assets will be carried. The
  confirmation always lists carried assets, even when lexical conflict detection
  has no hit, and supports one-run exclusion of a whole asset.
- Changed asset detail popovers to fetch Runtime-backed visual asset details
  instead of trusting node cache only; exposed `从当前节点移除` and `本次不携带`.
- Added fixed-asset entrypoints from drawer image assets and kept generated
  image/node paths compatible with the existing visual asset panel.
- Fixed two browser-discovered P1 issues: stale/legacy model ids now resolve
  through the same model picker path used for display, and canceling the carry
  confirmation now flushes restored node state to Runtime.
- Hid unsupported Kling audio/sound controls unless future descriptors expose
  audio support; the current I2V spec UI shows only ratio, resolution, and
  duration.
- Recorded browser QA evidence and human acceptance runbook for the handoff.

Verification so far:

```text
Focused Runtime preflight/video/visual asset tests: 27 passed, 1 warning
Studio static tests: 14 passed
Changed Studio JS node --check: passed
Browser QA on http://127.0.0.1:8794/studio/?project=loop004-browser-qa:
  carry confirmation passed
  one-run exclusion passed
  cancel persistence passed
  Runtime-backed asset detail popover passed
  Kling video spec no-sound UI passed
```

Evidence:

```text
docs/maintenance/AFS-BROWSER-QA-LOOP-004.md
docs/handoff/AFS-HUMAN-ACCEPTANCE-RUNBOOK-004.md
runs/agent_browser_qa_loop_004/
```

Boundaries:

- Browser/runtime verification only; human acceptance still requires the
  runbook to be executed by the user.
- MiniMax/Kling creative quality remains human-scored.
- No provider raw, signed URL, secret, or private local material was recorded.

## 2026-06-13 - Legacy Freeze And Repository Hygiene

- Added `.gitattributes` and confirmed renormalization did not create broad
  line-ending churn.
- Tagged and pushed `legacy-frozen-20260613` at the pre-cleanup baseline.
- Froze production-memory and distribution-chain tests behind the `legacy`
  marker; default `pytest` now runs the current Runtime/Studio/contract gate,
  while `pytest -m legacy` runs the frozen reference suite.
- Updated maintenance audit to list legacy-frozen paths separately while still
  scanning the full repository for secret-like fragments and runtime artifacts.
- Retired current code/test compatibility for `NARRATOCUT_ALLOW_REMOTE_*`;
  provider gates now use `AFS_ALLOW_REMOTE_*` only.
- Deleted the stale v0.2 Runtime frontend handoff and the orphan
  `ComplianceResult` schema.
- Classified untracked root cleanup/review instruction files as local workspace
  inputs so they do not break repository retention review when present in the
  operator checkout.

Verification so far:

```text
Default pytest: 363 passed, 527 deselected, 2 warnings
Legacy pytest: 527 passed, 363 deselected, 1 warning
Focused provider/schema/runtime/static tests: 66 passed, 1 warning
maintenance_audit: failed=0, passed=4, warning=3
git diff --check: exit 0, Windows LF conversion notices only
```

## 2026-06-13 - Runtime Legacy Route Removal

- Removed Production Memory HTTP business routes from Runtime Service:
  `POST /runs/asset-test`, `POST /runs/two-round-validate`, and
  `POST /provider/validation-plan`.
- Kept production-memory CLI commands, `agentflow/memory`, and production-memory
  harness/function tests intact.
- Regenerated the default Runtime OpenAPI snapshot with
  `AFS_ENABLE_LEGACY_RUNTIME_V02` closed; the snapshot no longer contains the
  removed Production Memory routes or stale v02 routes.
- Kept `/provider/script-draft-plan` as the current LLM script vertical.
- Replaced current default route exception projection with safe error details;
  remaining `detail=str(exc)` usage is legacy-v02-only residual risk.
- Updated the positioning sentence to:
  `AgentFlow Studio 是 AI 内容生产的 Agent-native 生产操作层。`
- Added dependency upper bounds without generating a lock file.

Verification so far:

```text
Focused Runtime contract set: 31 passed, 2 warnings
Default OpenAPI export: passed
maintenance_audit: failed=0, passed=4, warning=2
CLI --help: passed
CLI version: 0.1.0
Full pytest: 886 passed, 2 warnings
git diff --check: exit 0, Windows CRLF notices only
```

## 2026-06-13 - Browser QA Hardening Loop 6/7 And Final Verification

- Continued agent-led browser QA after the live asset and Kling passes.
- Fixed Studio state persistence for `lastContextBundle`: safe included/excluded assets, budget, warnings, and temporary lock override summaries now survive refresh, while `trace_summary`, provider prompt, provider raw, and other runtime-only details remain pruned.
- Added active Runtime save flush after image/video generation and poll success/failure so final node states are not lost to debounce timing.
- Added drawer actions for selected video nodes to use existing image assets as explicit first/last frames; no implicit last-upload or first-upload fallback is used.
- Prevented video nodes from hydrating an image preview URL into `<video>` playback; only Runtime video preview routes can become video `previewUrl`.
- Fixed prompt-bar video behavior: a running video node with `lastVideoJobId` now continues polling instead of submitting another paid video job, and completed nodes return to the normal `生成` action.
- Updated `.env.example` to remove legacy `NARRATOCUT_*` provider gate names.
- Rewrote the browser QA maintenance report in Chinese and added Loop 6/7 evidence plus final verification status.

Verification:

```text
Focused Runtime/Provider/Studio tests: 72 passed, 1 warning
Studio JS node --check: 37 files passed
Full pytest: 886 passed, 2 warnings
maintenance_audit: failed=0, warning=2
git diff --check: exit 0, CRLF notices only
Browser final check: current Studio tab has safe video preview, send action title is 生成, app console warn/error count is 0
```

Boundary: this closes runtime/browser verification for the current hardening loop. It is still not human acceptance; MiniMax identity quality and Kling first-frame creative quality need human scoring.

## 2026-06-13 - Browser QA Hardening Loop 5

- Continued agent-led browser QA on a fresh project and fixed asset semantics discovered during the run.
- Fixed Runtime-synced visual assets in the drawer: fixed assets now keep `asset_type`, `image_asset_refs`, safe preview URLs, and labels such as `人物资产` instead of falling back to `参考`.
- Improved visual asset prefill by extracting from optimized prompt sections and deduplicating repeated phrases in signatures and feature cards.
- Added occupied-region avoidance for dock-created nodes so new nodes no longer land directly on top of existing nodes.
- Fixed drawer `用于当前节点`: fixed visual assets now populate `node.params.visualAssets`, so node badges, context_subgraph, optimizer asset references, and generation resolver all see the same asset.
- Hardened selected video toolbar behavior so a running video task exposes `video-poll` rather than a second submit action.
- Browser evidence covered fresh project creation, T2I optimize/generate, asset fix, refresh drawer restore, readonly asset detail, attached-asset optimization, and attached-asset generation with `本次携带 1 项资产`.

Verification:

```text
tests/test_web_studio_static.py tests/test_api_runtime_studio_state.py tests/test_api_runtime_prompt_memory_loop.py tests/test_api_runtime_creative_agent_keyframes.py: 42 passed, 1 warning
Studio JS node --check for all apps/studio/src/**/*.js: passed
Browser console warn/error: none
Evidence: runs/loop-fresh-asset-drawer-20260613.png, runs/loop-attached-asset-optimize-20260613.png, runs/loop-attached-asset-generation-20260613.png
```

Boundary: live MiniMax image/LLM output remains runtime/provider verification only. Character identity similarity still needs human scoring.

## 2026-06-13 - Browser QA Hardening Loop 4

- Fixed Studio video resume persistence: safe `firstFrameImageAssetId`, `lastFrameImageAssetId`, `lastVideoJobId`, `lastVideoPreviewUrl`, and quota override state now survive `studio-state` save/restore.
- Extended safe preview URL validation to Runtime video preview routes while still rejecting local paths and provider URLs.
- Added the video node `继续轮询视频任务` path after refresh and verified it against a live Kling I2V job.
- Fixed successful video poll rendering: the node `previewUrl` now switches to the video preview endpoint and video nodes render a `<video controls>` player instead of the image preview component.
- Recorded a UX risk: the selected-node toolbar can make `生成` and `更多` easy to mis-hit during QA; one accidental Kling submit was safely completed and reused as resume evidence.

Verification:

```text
tests/test_api_runtime_studio_state.py tests/test_web_studio_static.py: 20 passed
node --check apps/studio/src/node-result-view.js apps/studio/src/node-actions.js apps/studio/src/panels/node-menu.js: passed
Browser QA: refresh -> node menu -> continue poll -> succeeded -> video player rendered
Evidence: runs/kling-poll-ui-video-preview-20260613.png
```

Boundary: this is runtime/browser verification only. The Kling video is technically playable; creative quality and first-frame suitability still need human scoring.

## 2026-06-13 - Browser QA Hardening Loop 3

- Fixed the live Kling I2V browser path discovered during agent-led QA.
- Split Kling Studio execution into true async submit/poll: submit now creates the provider task and returns `submitted`; poll returns `running` or `succeeded`.
- Hardened the Kling adapter against generic provider-plan field leakage and added a safe Runtime manifest fallback for unexpected adapter exceptions.
- Verified a live Studio video-node path with explicit first frame: upload -> set first frame -> submit -> poll -> safe preview.
- Live Kling output succeeded with a safe `video/mp4` preview, H.264 1924x1076, 24fps, 5.04s, 9.13MB. First/last frame evidence was extracted under `runs/`.

Verification:

```text
tests/test_provider_adapter_registry.py tests/test_api_runtime_video_generations.py tests/test_kling_video_smoke.py tests/test_kling_video_request_plan.py tests/test_kling_video_task_recovery.py tests/test_kling_video_completion.py: 44 passed
node --check apps/studio/src/node-actions.js: passed
ffprobe media sanity: passed
```

Boundary: Kling live execution is runtime/provider verification only. The generated clip is technically valid, but quality still needs human scoring; multi-view sheets can produce crop artifacts and should not be treated as ideal video first frames.

## 2026-06-13 - Browser QA Hardening Loop 2

- Continued agent-led browser QA on `codex/afs-browser-qa-hardening-002`.
- Fixed empty-project meta drift between URL/project select/drawer after async project-list refresh.
- Removed demo seed assets from new Studio projects and deduplicated Runtime-synced assets by safe `asset_id` / `visual_asset_id`.
- Extended Studio state sanitization to preserve safe asset ids, feature cards, negative locks, signatures, and safe preview URLs for asset drawer/details restore.
- Strengthened I2I prompt optimization: uploaded image filename summaries now reach Runtime, and generic MiniMax-M3 outputs that miss reference/short-hair/school-uniform locks are replaced by a traceable guardrail fallback.
- Simplified image and video node prompt bars by hiding unimplemented operation-mode controls.
- Browser evidence covered asset fix prefill, asset drawer/detail restore, live MiniMax I2I optimization, live MiniMax I2I generation, and video first-frame guard behavior.

Verification:

```text
tests/test_api_runtime_prompt_memory_loop.py tests/test_api_runtime_studio_state.py tests/test_web_studio_static.py: 31 passed
tests/test_web_studio_static.py: 14 passed after video UI cleanup
node --check touched Studio JS: passed
py_compile touched Runtime modules: passed
```

Boundary: live MiniMax I2I generation is provider/runtime evidence, not human acceptance. It improved hair/uniform preservation but still showed identity/background drift.

## 2026-06-13 - Browser QA Hardening Follow-up

- Fixed project isolation after Claude walkthrough: project switch no longer reads the unscoped legacy canvas key as a runtime fallback; legacy keys are migrated once and removed.
- Replaced native `window.prompt` / `window.confirm` project/director flows with in-app modals.
- Normalized legacy `NARRATOCUT_ALLOW_REMOTE_*` provider gates to `AFS_ALLOW_REMOTE_*` in the registry and MiniMax/Kling plan fallbacks.
- Skipped `company_gateway` aggregate services in ProviderRegistry so local full provider configs do not block concrete adapters.
- Split prompt optimization into T2I expansion and I2I edit modes, surfaced `optimization_mode` to Studio, and removed user-facing raw provider/gate error text.
- Flushed Studio state immediately after image upload so refresh restores safe preview URLs.

Verification:

```text
Focused static/provider/optimizer tests: 17 passed, 1 warning
Studio JS node --check for touched files: passed
Browser QA report: runs/browser_qa_hardening_1781302404.json status=passed
MiniMax image API smoke: succeeded, provider_calls_started=true
Kling I2V preflight: ready, secrets_printed=false
git diff --check: passed with CRLF notices only
```

Boundary:

- Live LLM optimization and one MiniMax image generation were used as runtime verification only.
- Kling was preflighted but no live I2V job was submitted in this slice.
- No provider secrets or raw provider payloads were written to tracked files.

## 2026-06-13 - LLM Optimizer Runtime Fallback Fix

- Fixed the remaining Studio prompt optimization 422 when the external provider config has blank legacy LLM default model refs.
- Added provider-side legacy defaults for descriptorless OpenAI-compatible LLM services: MiniMax falls back to `MiniMax-M2.7-highspeed`, DeepSeek falls back to `deepseek-chat`.
- Prompt optimization now skips MiniMax Anthropic-style OpenAI-compatible 404s and continues to the next registry LLM service.

Verification:

```text
tests/test_provider_adapter_registry.py tests/test_api_runtime_prompt_memory_loop.py: 31 passed, 1 warning
Runtime 8790 restarted with external provider config and AFS_ALLOW_REMOTE_LLM/IMAGE/VIDEO=true
POST /projects/debug-optimizer/prompt-optimizations: 200 OK, provider_calls_started=true, llm_enhancement.status=applied
Kling provider preflight: ready, secrets_printed=false
Registry descriptor check: minimax_image, kling_i2v, deepseek_llm, minimax_llm ready
```

Boundary:

- No provider secret or raw provider response was written to tracked files.
- No live image or Kling video job was submitted in this fix.
- The live LLM optimization call is runtime verification, not human acceptance.

## 2026-06-13 - Provider Service Alias Fix

- Fixed Studio prompt optimization when the active provider config exposes `minimax_llm` instead of `minimax_m3`.
- Added LLM service fallback in Runtime prompt enhancement: explicit request -> `minimax_m3` -> `minimax_llm` -> other registry LLM services.
- Mapped legacy descriptorless `provider=minimax`, `capability=llm` services to the OpenAI-compatible LLM adapter under the existing `AFS_ALLOW_REMOTE_LLM` gate.

Verification:

```text
tests/test_provider_adapter_registry.py tests/test_api_runtime_prompt_memory_loop.py: 29 passed, 1 warning
Studio optimizer/model JS node --check: passed
External provider config registry check: minimax_image ok, minimax_llm ok, kling_i2v ok, minimax_m3 absent by design
```

Boundary:

- No live LLM, image, or video provider call was made in this fix.
- Existing running Runtime processes must be restarted to pick up the alias fallback.

## 2026-06-13 - Kling I2V Preflight And Project Persistence

- Added Runtime project listing and image asset public listing for Studio project selection and drawer rehydration.
- Persisted safe Runtime preview URLs in Studio state and rejected non-runtime preview URLs.
- Added project-scoped Studio local cache, topbar project selector/new-project action, and preview hydration from saved uploads.
- Split context resolver responsibilities into subgraph, asset arbitration, and text-channel modules while keeping the old facade import.
- Added shared provider dispatch retry helper for image/video reuse.
- Extended ProviderDescriptor to v0.2 video fields and added `kling_i2v` registry adapter wiring on top of existing Kling modules.
- Added Runtime video generation submit/poll/cancel/preview routes with explicit first-frame asset id, candidate_count=1, video gate, quota counter, and safe manifest.
- Added Studio video node path for explicit first/last frame marking and Kling I2V submit.
- Added safe Kling provider preflight tool and video descriptor addendum.
- Added a narrow legacy descriptor inference path for descriptorless Kling local configs so the existing external secret file can be used without copying credentials into the repo.

Verification:

```text
Project persistence focused: 4 passed
Provider registry focused: 19 passed
Runtime video focused: 4 passed
Resolver/keyframe/visual asset focused: 18 passed
Keyframe focused: 11 passed
Studio static: 12 passed
Combined focused set: 63 passed
Full pytest: 868 passed
Studio JS node --check for all apps/studio/src JS files: passed
Project browser QA: passed on 127.0.0.1:8791/studio/
External Kling secret preflight: ready, secrets_printed=false, gate disabled
```

Live state:

```text
Repo-local configs/providers.local.json only exposes MiniMax services.
For Kling, use AFS_PROVIDER_CONFIG pointing at the external `.secrets` provider config supplied by the operator.
Preflight against that file is ready; AFS_ALLOW_REMOTE_VIDEO is still disabled in the current shell.
```

Boundaries:

- No live Kling submit was run.
- No provider secret, provider raw response, signed URL, local absolute media path, or media bytes were written to tracked files or API responses.
- Fake async video remains contract verification only.

## 2026-06-13 - MVP Hardening 001

- Added provider-facing `user_prompt_plain` and backend section-header stripping so human-readable prompt sections do not leak into image provider prompts.
- Capped generate-mode full-card asset injection at 3 characters and 1 scene; over-limit assets degrade to signature-only and are traceable in `excluded_assets`.
- Changed context subgraph traversal so `reference` edges do not consume the normal 3-hop budget, with a separate 6-reference-edge loop guard.
- Upgraded `visual_asset` to v0.2 with `supersedes_asset_id` and deterministic same-label arbitration by version terminal or newest `server_recorded_at`.
- Added `resolver_version`, `vocabulary_hash`, and `feature_card_hash` metadata to context bundles.
- Added one readiness/network retry around image provider dispatch and writes `retry_count` into keyframe safe manifests.
- Removed non-image local preview placeholders from Studio; non-image sends are disabled with explanatory copy, and fake cost numbers are hidden.
- Added readonly visual-asset detail popovers, fixed/retired drawer distinction, asset badge invalid-state correction, drawer search, Chinese fixed-asset action titles, and shortcut panel entries for `?`, `Ctrl+L`, and `Ctrl+D`.

Verification:

```text
Backend focused hardening set: 33 passed, 1 Starlette/httpx warning
Studio static: 12 passed
Changed Studio JS node --check: passed
Full pytest: 855 passed, 1 Starlette/httpx warning
maintenance_audit: failed=0, warning=2 existing doc/oversized warnings
git diff --check: passed with Windows CRLF notices only
Browser light QA: `/studio/` loaded with no console errors; visible page no longer exposes `asset_fix`, `fix visual asset`, local-preview text, or `.bar-cost`. Current browser state had no asset badge, so readonly asset-detail clicking remains static-test covered until a seeded asset state is used.
```

Boundaries:

- No live provider call or human acceptance was run in this slice.
- Kling/video, S2 feature-card LLM extraction, S3 storyboard schema, and legacy package retirement remain out of scope.

## 2026-06-13 - Studio MVP Usability P0

- Switched the Studio prompt optimizer product path to remote-required LLM enhancement. Local deterministic assembly remains backend-internal for tests and non-Studio fallback, but the Studio UI no longer silently shows it as an optimization result.
- Persisted local Windows user env gates for this machine: `AFS_ALLOW_REMOTE_IMAGE=true`, `AFS_ALLOW_REMOTE_LLM=true`, and `AFS_PROVIDER_CONFIG=D:\Projects\AgentFlowStudio\configs\providers.local.json`; video, ASR, and download gates remain untouched.
- Fixed Studio state persistence so transient runtime bundle details such as `lastContextBundle.trace_summary` are pruned before safety scanning, while fixed `visualAssets` can persist on nodes.
- Updated node actions so image-node retry uses the real generation path and node menus expose direct asset marking from the canvas.
- Improved runtime client error detail propagation and image gate blocked copy, so provider/gate failures are visible instead of turning into generic request errors.

Verification:

```text
Focused prompt/state/static tests: 4 passed
Prompt/state/static related suite: 21 passed
Changed Studio JS node --check: passed
Full pytest: 844 passed, 1 Starlette/httpx warning
```

Boundaries:

- No live provider call was run as part of this code change.
- Runtime/browser verification is still not human acceptance.

## 2026-06-12 - MVP Closeout Live A/B/C

- Ran gate-closed Studio browser QA successfully after tightening the QA selector for multiple temporary-unlock buttons.
- Ran live MiniMax A/B/C through the Provider Gateway using the local `mmx_cli` token-plan backend and `AFS_ALLOW_REMOTE_IMAGE=true`; LLM/ASR/video/download gates stayed unset.
- Live A/B/C succeeded with one generated image per arm. A had no asset context, B used the resolver path without fixed asset injection, and C used fixed asset feature/locks plus one subject reference image.
- Visual observation: C materially improved identity, red coat, short black hair, and left-brow marker compared with A/B, but the brow scar wording produced an over-literal black cross-like mark and should be refined before broad internal testing.
- Evidence is under ignored `runs/studio_asset_context_live_comparison_20260612_final/`; closeout summary is `docs/handoff/AFS-MVP-CLOSEOUT-20260612.md`.
- Non-claims: live A/B/C is provider smoke and asset-semantics evidence only; it is not human acceptance, business validation, or durable-memory promotion.

中文摘要：本文件只保留当前阶段的短记录和验证入口，不再承载旧 Web、旧 Workbench 或历史浏览器 QA 的长流水。当前判断以 Studio、Runtime Service、知识库、创作智能体和 provider gate 为主线；测试通过只代表工程验证，不代表人工验收、商业验证或长期记忆晋升。后续如果某条记录不再支持当前 MVP、真实模型接入或维护收口，应直接删除，避免把过期资料继续带入主线。

当前状态：本轮收口已经把旧 Workbench、旧静态 Web、过期前端对接包和旧浏览器 QA 记录移出主线，同时补上创作意图控制智能体、关键帧生成 gate、Studio 静态入口和 OpenAPI 契约。后续记录只写影响当前落地的验证结果、阻塞项和真实模型接入证据，不再追加无明确后续用途的过程叙事。

Status: short current-session log. Historical long narratives are not current
product documentation.

中文当前说明：本文件当前只作为工程维护流水账，不承担业务验收、模型效果判断或长期公司规则晋升。每条记录都应服务于后续接手者快速判断“这轮到底改变了什么、验证了什么、还剩什么风险”。如果某项工作只产生了本地缓存、临时运行产物或 provider 原始响应，它不能被写成产品能力完成；如果某项证据还没有经过人工验收，也不能被写成业务有效。当前阶段的重点是把 Studio 主线、Runtime Service、provider gate、固定资产、图谱上下文和维护清理统一到一条可落地的 MVP 链路上。历史分发线、旧 Workbench、旧 memory UI、旧候选记忆流程只保留为 legacy 或审计背景，不再作为新任务入口。后续每次接入真实模型前，都应先确认本地配置没有进入 tracked 文件，provider gate 按能力单独开启，生成媒体只落在 ignored runtime/evidence 目录，并在报告中明确区分工程验证、provider smoke、人工验收和业务验证。

## 2026-06-12 - Provider Gateway v0.1

- Extended the provider descriptor with `capabilities`, optional `account_pool_id`, and `rate_limit_hint`.
- Added local account pool selection with deterministic priority ordering, disabled-account filtering, and credential-env presence checks without reading or persisting secret values.
- Kept MiniMax image on the unified `ProviderRegistry.dispatch(...)` path and preserved descriptor-driven prompt budget / reference slots.
- Added OpenAI-compatible LLM dispatch to the registry and moved Runtime prompt enhancement away from legacy `ModelGateway.from_config_path`.
- Added a fake async video adapter to validate `submit -> poll -> normalize` lifecycle without live video provider calls.
- Replaced provider adapter and config docs with readable contracts and expanded `configs/providers.example.json` to cover image, LLM, fake video, descriptors, and account pools.

Verification so far:

```text
tests/test_provider_adapter_registry.py: 11 passed
Focused provider/keyframe/resolver/prompt set: 42 passed, 1 Starlette/httpx warning
Full pytest: 838 passed, 1 Starlette/httpx warning
Studio JS node --check: passed 35 files
maintenance_audit: failed=0, warning=1 existing oversized-files warning
git diff --check: passed with Windows CRLF notices only
```

Boundaries:

- Provider gates remain closed except mocked dispatch paths inside tests.
- No live image, LLM, ASR, video, or download provider call was made.
- Fake video adapter is a lifecycle contract test only, not provider smoke.
- This is not human acceptance, business validation, or durable-memory promotion.

## 2026-06-12 - Project Inventory And Direct Cleanup 001

- Added reusable project inventory / cleanup tooling with tracked, ignored, and untracked-unignored classification.
- Protected local provider config, local model weights, raw source media, and media evidence as report-only.
- Generated `docs/maintenance/AFS-PROJECT-INVENTORY-20260612.md` and machine reports under ignored `data/reports/project_inventory/`.
- Executed low-risk cache cleanup. Across cleanup and post-verification cleanup passes, 14,452 cache targets were deleted, saving about 30.24MB.
- Confirmed `configs/providers.local.json`, `configs/models.yaml`, `data/models/faster-whisper`, and `data/raw/demo_zombie/input.mp4` remained in place.
- Recorded remaining Windows ownership/ACL blocker: `data/processed/pytest-basetemp` is ignored pytest cache but cannot be fully deleted by the current user.
- Removed the extra deep-review helper code after using its output; maintenance should not accumulate one-off audit tooling.
- Deleted the unreferenced tracked empty package `agentflow_studio/asset_manager/__init__.py`.
- Deleted six obsolete `AFS-PRODUCTION-MEMORY-ASSET-*` handoff files superseded by fixed `visual_asset` and graph-scoped resolver work.
- Removed Production Memory short aliases from the default CLI product surface; legacy long `production-memory-loop-*` commands remain hidden compatibility while `agentflow/memory` is still tested.
- Deep local review covered 12,791 local files, 3.46GB, 755 project text files, and 86,993 text lines; 80 exact duplicate media/evidence groups represent about 827MB theoretical reclaimable space once a canonical evidence-retention rule exists.

Verification so far:

```text
tests/test_project_inventory_cleanup.py: 3 passed
```

Boundaries:

- Provider gates remain closed.
- No model weights, provider local config, source media, or unique evidence artifacts were deleted.
- Duplicate media evidence was not deleted without a canonical run retention rule.
- This is not human acceptance, business validation, or durable-memory promotion.

## 2026-06-12 - Studio Mainline Cleanup 001

- Updated project authority docs so `/studio/` + Runtime Service + fixed assets/context resolver/provider-gated evidence is the current MVP line.
- Marked the subtitle/text distribution chain as legacy/optional rather than current MVP.
- Hid Runtime v02 list/import/source-assets/content-cards/canvas-draft routes by default behind `AFS_ENABLE_LEGACY_RUNTIME_V02=true`.
- Marked `agentflow/memory` as read-only legacy for Studio/Runtime work; added a static guard against new Studio/Runtime imports.
- Audited the named `*_sop` cleanup targets with `git ls-files`; only `agentflow_studio/compliance/__init__.py` was tracked and unreferenced, so only that stub was deleted.
- Created `BACKLOG.md` for follow-up maintenance debt: oversized file split and Kling adapter v0.2.

Verification:

```text
Cleanup/static focused tests: 15 passed, 1 Starlette/httpx warning.
Full pytest: 828 passed, 1 Starlette/httpx warning.
Studio JS node --check: 35 files passed.
maintenance_audit.py: 0 failed checks, 1 oversized-files warning.
git diff --check: clean except Windows CRLF notices.
```

Boundaries:

- No broad deletion of `agentflow/memory`.
- No live provider gate was opened.

## 2026-06-12 - Director Compiler v1

- Added deterministic backend `Director Compiler v1` for `DirectorSetup2D`.
- Extended director setup with `activeCameraId`, `activeSubjectIds`, and subject-level `visual_asset_id`.
- Changed user prompt assembly and context resolver to consume compiler output rather than frontend readout text.
- Backend compiler reads visual asset signatures by id from the Runtime visual asset store; frontend-provided signatures are ignored.
- Updated Studio director defaults so empty lists remain empty and the old bedroom prop/modifier template no longer repopulates after deletion.
- Changed Studio “生成提示词片段” to confirmed append-only behavior; it no longer overwrites the node prompt.

Verification:

```text
Director compiler/API/context/static focused set: 24 passed, 1 Starlette/httpx warning.
Changed director JS node --check: passed.
```

Boundaries:

- Frontend `directorPromptSummary` is now a UI summary only, not the authoritative compiler.
- No live provider gate was opened.

## 2026-06-12 - Provider Adapter v0.1

- Added `provider_descriptor.v0.1` to service config and documented the adapter contract in `docs/provider_adapter_contract.md`.
- Added `ProviderRegistry.dispatch(capability, service_id, request)` and a MiniMax image adapter wrapper with the standard `validate -> translate -> submit -> poll -> normalize` lifecycle.
- Changed Runtime keyframe generation to use the registry instead of importing MiniMax smoke directly.
- Moved keyframe prompt length and reference image slot limits behind provider descriptors; MiniMax remains configured as one subject reference image slot.
- Kept gate-closed Runtime paths config-free and no-network.

Verification:

```text
Provider/keyframe/resolver focused tests: 22 passed, 1 Starlette/httpx warning.
MiniMax smoke regression: 9 passed.
py_compile for provider adapter, Runtime keyframes, context resolver, budget: passed.
```

Boundaries:

- No live provider gate was opened.
- Kling/video adapter is expressible by the contract but not implemented in this slice.

## 2026-06-12 - AFS Asset Context S1

- Created isolated branch/worktree `codex/afs-asset-context-s1`.
- Added `visual_asset v0.1` Runtime storage and promote/list/retire APIs.
- Stopped prompt-background placeholder pollution: `Primary character` / `Primary scene` no longer create records, and extracted context stays candidate-only.
- Added `context_subgraph v0.1` and `context_bundle v0.1`; prompt optimization and keyframe generation now share the resolver when a subgraph is supplied.
- Split optimize/generate views: optimize injects only connected or label-matched signatures, generate consumes only connected fixed assets.
- Added request-level temporary lock overrides and unconditional negative-lock injection for non-overridden locks.
- Kept no-subgraph keyframe requests on the old `asset_refs` path for compatibility.
- Added `generation_comparison_report v0.1` with fixed A/B/C arm definitions.
- Added one-click connect for named unconnected assets, request-level temporary unlock, and reproducible gate-closed browser QA in `tools/studio_asset_context_browser_qa.py`.
- Browser QA drives upload -> fixed asset -> optimize warning -> one-click connect -> temporary unlock -> generate -> A/B/C report and writes `runs/studio_asset_context_browser_qa_report.json`.
- Added `tools/studio_asset_context_live_comparison.py` as the S1 A/B/C evidence runner. It writes a gate-closed readiness report by default and requires `AFS_ALLOW_REMOTE_IMAGE=true`, `--allow-live-provider`, provider config, and a real `--reference-image` or explicit `--sample-reference-output` before any image provider call can start.
- Added `tools/studio_asset_context_sample_reference.py` to write a deterministic non-provider PNG reference for reproducible provider smoke setup.
- Added `docs/handoff/AFS-ASSET-CONTEXT-S1-COMPLETION-AUDIT.md` to keep the current pass/block state explicit until live MiniMax evidence is available.
- Added Studio single-canvas fixed-asset confirmation panel, `context_subgraph` request building, asset connection status display, and "本次携带" bundle summary.

Verification so far:

```text
Focused Runtime/Web set: 34 passed, 1 Starlette/httpx warning.
Full pytest: 798 passed, 1 Starlette/httpx warning.
Studio changed JS node --check: passed.
Browser QA script: passed with provider gate closed; report records browser API POST proxy via FastAPI TestClient due local Chrome POST hang.
Live comparison runner gate-closed readiness: passed with ignored provider config path supplied; provider_calls_started=false.
Live comparison gate-safety preflight: simulated `AFS_ALLOW_REMOTE_IMAGE=true` without `--allow-live-provider`; blocked with `live_provider_flag_missing`, provider_calls_started=false.
Maintenance audit: passed with 0 warnings.
git diff --check: passed with Windows CRLF notices only.
```

Boundaries:

- Provider gates remain closed in local verification.
- No provider raw response, media bytes, local absolute paths, signed URLs, or secrets were added.
- This is not human acceptance, business validation, provider smoke, or durable-memory promotion.

## 2026-06-12 - MiniMax Text/Image Integration And Reference Flow

- Added gated MiniMax-M3 prompt enhancement for the creative intent agent path; deterministic local prompt assembly remains the fallback when the LLM gate or config is unavailable.
- Added gated MiniMax image-01 keyframe generation and safe candidate preview refs; API responses do not expose provider raw payloads, local absolute paths, signed URLs, media bytes, or secrets.
- Added Studio image upload assets and generated-keyframe reusable assets so connected downstream image nodes can send upstream reference images for image-to-image style tests.
- Kept the Studio user surface product-facing: optimization remains a node action, keyframe sending is image-node scoped, and trace/rule/weight/provider internals stay out of the UI.
- Local provider keys remain environment-only through `MINIMAX_API_KEY`; tracked config files contain examples and placeholders only.

Boundaries:

- Provider smoke is not human acceptance, business validation, video validation, or durable-memory promotion.
- Video generation remains closed.

## 2026-06-12 - AFS Studio v0.2 Delivery Polish

- Created isolated branch/worktree `codex/afs-studio-v02-delivery-polish-001` because the main checkout was occupied by a parallel MiniMax integration branch.
- Reframed the user-facing Studio surface into AFS Studio 创作图谱: flow-native starters for script-to-storyboard, character turnaround, 2D director board, keyframe prompt, and 5s video prompt.
- Added safe Runtime Studio state API: `GET /projects/{project_id}/studio-state` and `PUT /projects/{project_id}/studio-state`; only meta, viewport, nodes, semantic edges, visible assets, and safe summaries are persisted.
- Added frontend Runtime save/restore with localStorage fallback and visible save status: 已保存 / 保存中 / 同步中 / 本地暂存.
- Added lightweight undo/redo for meaningful canvas edits while excluding high-frequency pan/zoom/drag/prompt typing from history bloat.
- Upgraded visible assets: local preview and director saves create typed asset cards; asset drawer supports 设为参考, 用于当前节点, and 从画布定位.
- Added semantic edge types: generation, director, and reference; director/reference edges have distinct line styles and labels.
- Director board saves now upsert a `director_setup` asset and mark downstream edges as director constraints when applied to connected nodes.
- Prompt optimizer remains input-anchored and product-facing; result actions now give replace/append/copy feedback and source chips stay limited to 影视结构, 项目风格, 角色/场景设定, 导演台布置.
- Fixed narrow viewport horizontal overflow and split asset drawer CSS into `assets.css` to keep maintenance audit clean.

Verification:

```text
Runtime-hosted browser QA on http://127.0.0.1:8807/studio/: desktop director starter/modal path passed; mobile overflow false.
Focused tests: 27 passed, 1 Starlette/httpx warning.
Full pytest: 772 passed, 1 Starlette/httpx warning.
apps/studio JS node --check: passed.
maintenance_audit: passed.
git diff --check: passed with Windows CRLF notices only.
```

Boundaries:

- Provider gates remain closed.
- No image/video/media bytes were generated.
- This is not human acceptance, business validation, provider smoke, or durable-memory promotion.

## 2026-06-12 - AFS Studio UI Polish + 2D 导演台 Prompt 联动

- 修复 Studio 左上角重叠：抽屉展开时项目身份只由抽屉承载，顶栏从 `var(--drawer-w)` 右侧开始；抽屉收起时才显示 compact 项目 pill。
- 将导演台占位壳改成二维顶视图布置板：对象列表、网格画布、相机视锥、灯光光束、人物朝向、道具形状和右侧参数面板均可见。
- 导演台布置保存为节点本地 `directorSetup`；导演台节点展示机位 / 主体 / 灯光摘要，并可驱动相连图片或视频节点。
- Prompt 优化会从当前导演台节点或最近上游导演台节点提取安全版 `director_setup`；优化浮层显示用户可懂的“导演台布置”来源 chip。
- 后端用户版六段提示词已消费导演台上下文：人物站位、道具空间、机位/FOV/构图、灯光、运动连续性和光源/机位/空间冲突负面约束。
- 修复从底部 dock 添加节点时新节点落入 dock 安全区的问题：菜单仍从 dock 弹出，但节点出生点改为当前画布可视中心。
- 拆分导演台字段控件到 `apps/studio/src/panels/director-fields.js`，并将导演台 prompt API 测试移到 `tests/test_api_runtime_director_setup_prompt.py`，让本轮触达文件回到维护阈值内。
- 将 AgentFlow local AgentOps contract 示例的 `doc_path` 从已删除旧维护文档改到当前 `docs/company_operating_model.md`。

验证：

```text
Full pytest: 767 passed, 1 Starlette/httpx warning
Focused Studio / prompt / contract set: 21 passed
apps/studio JS node --check: passed
Runtime-hosted browser QA: passed
repository_retention_review manual_review_required_count: 0
git diff --check: passed with Windows CRLF notices only
maintenance_audit: 仅剩既有 human-facing Markdown 中文覆盖 warning；oversized_files 已通过
```

边界：

- Provider gate 仍关闭。
- 未生成图片/视频字节，也未保存 provider 原始响应。
- 这不是 human acceptance、business validation、provider smoke 或 durable-memory promotion。

## 2026-06-14 - Loop 005 Closeout Baseline Fix

- Moved three local review/input Markdown files out of the repository root to `D:\Projects\AgentFlowStudio-local-inputs\20260614`, because they are not formal repository ledgers and should not affect repository retention review.
- Generalized repository retention policy: root-level untracked Markdown files are classified as `local_workspace_input` instead of relying on hard-coded `AFS-*` filename prefixes.
- Fixed Studio `Failed to fetch` when the page is opened from a local static/dev port such as `8796`: `runtime-client.js` now falls back to the local Runtime Service at `http://127.0.0.1:8790`, while still using same-origin when served from Runtime and allowing explicit local overrides.
- Navigated the in-app browser from stale `http://127.0.0.1:8796/studio/` to Runtime-hosted `http://127.0.0.1:8790/studio/`; browser console warnings/errors were empty after reload.

Verification:

```text
tests/test_repository_retention_review.py tests/test_web_studio_static.py: 24 passed
pytest -q: 386 passed, 527 deselected, 2 warnings
pytest -m legacy -q: 527 passed, 386 deselected, 1 warning
Studio JS node --check: 37 files passed
tools/maintenance_audit.py: failed=0, warnings only
git diff --check: passed
```

Boundaries:

- This is runtime/browser verification, not human creative acceptance.
- Moved local input files are outside the repository and were not committed.
- Provider creative quality scoring remains a human-role QA task.

## 2026-06-12 - Creative Intent Agent And Keyframe Gate

- Added deterministic `creative_intent_control_agent_v1` trace for prompt optimization.
- Added hard / strong / soft constraint layering, three internal candidates, multi-axis scores, deterministic selected candidate, and provider translation metadata.
- Treated `node_parameters` as hard controls in prompt assembly and trace.
- Added English `user preference:` extraction so lower-priority preferences can be suppressed when they conflict with professional/node constraints.
- Added `POST /projects/{project_id}/keyframe-generations`.
- Keyframe generation is gated by `AFS_ALLOW_REMOTE_IMAGE`; with the gate closed it writes only safe JSON artifacts and starts no network/provider call.
- Added repo-safe engineering summary: `docs/architecture/AFS_CREATIVE_INTENT_CONTROL_AGENT_ENGINEERING_SUMMARY.zh-CN.md`.
- Added private algorithm design note under `10-Startup/70-Projects/AgentFlow-Studio/30-agent-infrastructure/creative-intent-control-agent-v1.zh-CN.md`.
- Deleted stale Web/Workbench handoffs, old Web superpowers plans/specs, stale Web maintenance ledgers, and old Web archive files instead of archiving them.

Verification so far:

```text
tests/test_api_runtime_creative_agent_keyframes.py: 3 passed
prompt/runtime/studio focused set: 25 passed
apps/studio JS node --check: passed
```

Boundaries:

- No real provider call was made.
- No image/video bytes were generated through Runtime.
- This is not human acceptance, business validation, or durable-memory promotion.

## 2026-06-12 - MVP Follow-up Live Comparisons

- Implemented `tools/studio_asset_context_followup_comparisons.py` for the two runbook follow-up groups: character+scene A/B/C and lock-conflict locked/unlocked live runs.
- Added deterministic observatory scene reference generation to `tools/studio_asset_context_sample_reference.py`.
- Added focused tests for gate-closed no-call behavior, dual-asset C-arm context, temporary lock override capture, and scene PNG generation.
- Ran live MiniMax image follow-up with only `AFS_ALLOW_REMOTE_IMAGE=true`.
- Group 2 first run succeeded for A/B/C; C included both character and scene assets, used one character subject reference, and kept the scene in the text channel.
- Group 3 retry succeeded; locked output kept black short hair despite red-long-hair prompt, while temporary unlock produced red long hair and recorded the override in trace.
- One immediate Group 2 rerun hit a provider/CLI safe readiness block; preserved as provider intermittency evidence, not resolver failure.

Evidence:

```text
runs/studio_asset_context_followup_20260612_group2_success/
runs/studio_asset_context_followup_20260612_group3_retry/
runs/studio_asset_context_followup_group3_retry_report_20260612.json
docs/handoff/AFS-MVP-FOLLOWUP-LIVE-COMPARISONS-20260612.md
```

Verification:

```text
tests/test_studio_asset_context_followup_comparisons.py: 3 passed, 1 existing Starlette/httpx warning
py_compile follow-up tools: passed
git diff --check: passed with Windows CRLF notices only
```

Boundaries:

- Image provider gate only; LLM/ASR/video/download gates remained closed.
- Live output is provider smoke and asset-semantics evidence, not human acceptance or business validation.

## 2026-06-11 - AFS Studio Hard Cleanup

- Retired old Workbench/static memory-workbench user routes.
- Current frontend entry is `/studio/`, backed by `apps/studio/`.
- Deleted old UI source, old UI-specific tests, old Workbench browser QA tools, and old frontend integration docs.
- Prompt optimizer contract moved to `docs/architecture/AFS_NODE_PROMPT_OPTIMIZER_CONTRACT.zh-CN.md`.
- Verified earlier in this branch: full pytest, maintenance audit, `git diff --check`, Runtime-hosted `/studio/` browser QA, and `/workbench/` 404.
