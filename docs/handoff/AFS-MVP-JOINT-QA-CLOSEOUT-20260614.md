# AFS MVP Joint QA Closeout - 2026-06-14

## Claim Level

This run is AI role pre-acceptance plus provider smoke where the provider
actually ran. It is not human acceptance, business validation, or durable memory
promotion.

External evidence root: `20260614-afs-mvp-joint-qa` under the local evidence
workspace. The repository stores this safe summary only.

## Scope

- Branch/worktree: `codex/afs-mvp-joint-qa-closeout`.
- Product entry: Runtime-hosted `/studio/`.
- Provider scope: LLM, MiniMax image, Kling I2V.
- Excluded scope: ASR and external downloads.
- Added role: frontend UI reviewer.

## 2026-06-15 Final Update

The previous MiniMax image B blocker has been cleared by a B-only live retry
with `candidate_count=1`. Per user direction, image and video gates were opened
for Runtime 8790; ASR remained closed. MiniMax image live smoke succeeded and
registered one reusable image asset. Kling I2V preflight, submit, poll, Runtime
preview, and offline inspection succeeded with `candidate_count=1`.

The final readiness audit reports `recommended`, seven role checks passed, zero
provider blockers, and `human_acceptance_claim=not_claimed`.

## Verification Summary

| Layer | Result | Evidence |
|---|---|---|
| Gate-closed focused tests | Passed, 53 tests | `gate_closed_focused_pytest_after_tool_patch_retry.txt` and rerun output |
| Default pytest | Passed, 396 tests | Final rerun output after readiness audit |
| Legacy pytest | Passed, 527 tests | Final rerun output after readiness audit |
| Studio JS syntax | Passed, 37 files | `studio_node_check.txt` and rerun output |
| Product browser smoke | Passed | `gate_closed_8790_ui_smoke_corrected_report.json` |
| LLM prompt optimization smoke | Passed with two prompt optimization manifests | `live_llm_browser_runtime/*prompt_optimization_safe_manifest.json` |
| MiniMax image smoke | Passed: A/C comparison evidence plus B-only retry and direct image gate-open smoke | `live_minimax_image_comparison_report.json`, `minimax_b_only_live_retry_20260615.json`, `user_image_gate_open_live_smoke_20260615.json` |
| Kling I2V smoke | Passed: earlier recovery evidence plus direct video gate-open preflight/submit/poll/preview/offline inspection | `live_kling_i2v_startup_config_report.json`, `live_kling_i2v_startup_config_recovery_poll_report.json`, `live_kling_i2v_video_inspection.json`, `user_video_gate_open_preflight_20260615.json`, `user_video_gate_open_live_smoke_20260615.json`, `user_video_gate_open_live_smoke_ffprobe_20260615.json` |
| Frontend UI reviewer | Failed first pass, passed after responsive shell fix | `frontend_ui_reviewer_after_fix2_report.json` |
| AI role pre-acceptance | Recommended for user human-acceptance decision; not human acceptance | `ai_role_pre_acceptance_summary.json`, `afs_mvp_joint_qa_readiness_audit_final_20260615.json` |
| Continued blocker preflight | Passed deterministic hardening checks; startup-config Kling and MiniMax preflights reached ready with command-scoped gates; final image/video gate-open preflights passed | `kling_provider_preflight_after_blocker_hardening.json`, `kling_provider_preflight_startup_secrets_config_gate_open.json`, `minimax_image_provider_preflight_startup_secrets_config_gate_open.json`, `minimax_image_provider_preflight_image_video_gate_open_20260615.json`, `kling_provider_preflight_image_video_gate_open_20260615.json`, `gate_closed_live_comparison_after_arm_block_summary.json` |
| Readiness audit | Recommended, zero provider blockers, seven role checks passed, no human acceptance claim | `afs_mvp_joint_qa_readiness_audit_final_20260615.json` |
| Final verification | Passed with warnings only where already classified | default pytest 404 passed / 527 deselected; legacy pytest 527 passed / 404 deselected; Studio JS 37 files passed; maintenance audit failed=0; `git diff --check` exit 0 |

## Findings

### Fixed

- Mobile and narrow Studio shell clipped the project controls and starter cards.
  The drawer width now shrinks on small screens, topbar controls clamp to the
  remaining canvas width, and starter cards stack inside the visible canvas.
- `tools/studio_asset_context_browser_qa.py` no longer hardcodes screenshot
  output into repo `runs/`; screenshots default next to the external report.
- Browser QA reports now expose prompt optimization provider-call counts for
  future LLM smoke evidence.
- Runtime API example-contract and legacy provider-validation tests now clear
  local provider gates/config before asserting deterministic gate-closed
  behavior, so developer-machine live config cannot alter those expectations.
- Kling preflight now reports structured blocker IDs. The initial no-cost
  preflight classified the video blocker as `provider_service_missing`; after
  using a safe external provider-config shape, startup-config preflight reached
  `ready` with `secrets_printed=false`.
- Generation comparison arm evidence now includes safe `blocks` and
  `retry_count`; the live-comparison runner summarizes per-arm `block_ids` and
  `retry_count`, so future MiniMax arm B failures no longer collapse into an
  opaque `blocked` status.
- Added a no-cost readiness audit tool that aggregates the external evidence
  root into seven role checks and provider blockers. The current audit status is
  `needs_fixes`, with one provider blocker and no human acceptance claim.
- Kling Runtime I2V was recovered without a second submit: the first live submit
  succeeded, a later poll hit a transient `ConnectError`, TDD added a poll-once
  httpx-to-curl fallback, and poll-only recovery of the already submitted job
  returned a safe `video/mp4` Runtime preview. Offline inspection recorded a
  5.04s H.264 vertical video and a safe midframe thumbnail.
- MiniMax image preflight now separates the old B-arm `mmx_cli`
  authentication/configuration blocker from the current external REST config:
  command-scoped image gate-open preflight is `ready`, with effective backend
  `rest_api`, model `image-01`, `config_source=AFS_PROVIDER_CONFIG`, and
  `secrets_printed=false`.
- Studio now distinguishes stale Runtime preflight 404 from provider failure:
  Runtime client errors carry status and route, and the generation flow tells
  the user to restart the 8790 Runtime Service when a branch-local preflight
  route is missing.
- MiniMax B-only retry succeeded with no fixed asset, no subject reference, one
  candidate, safe manifest success, and no persisted provider raw or secret
  values. This cleared the last readiness-audit provider blocker.
- The asset-context browser QA proxy now closes image/video/ASR gates while
  allowing an explicit `--allow-live-llm` mode for the prompt-optimization path.
  A post-fix live-LLM rerun reached the first optimize and then hit an upstream
  SSL EOF on the second re-optimize; no image/video provider call was started by
  that QA path and it was not retried further.

### Open P1 / Blockers

- None for provider readiness after the B-only live retry and direct
  image/video gate-open smokes.
- Residual non-blocking risk: the asset-context browser QA path depends on live
  LLM for prompt optimization. A post-fix rerun saw an upstream SSL EOF during
  the second LLM re-optimize. This is recorded as a transient provider-path risk,
  not an image/video readiness blocker.

### Human-Scored Quality Risks

- MiniMax arm A generated a male subject for a `Lin Wan` prompt without a fixed
  reference.
- MiniMax arm C preserved a female red-coat/black-hair identity with the fixed
  asset, but the brow scar was visually too heavy and needs human scoring.
- Kling first-frame fidelity and motion adherence now have provider-smoke
  evidence. AI visual inspection of the extracted midframe found the synthetic
  portrait composition, black hair, red clothing, and gray-blue background
  broadly preserved, with no visible text or watermark. This remains
  pre-acceptance evidence and still needs human creative scoring.

## Seven-Role Pre-Acceptance

| Role | AI pre-acceptance result |
|---|---|
| Ordinary internal tester | Passed runtime basics: create, reload, switch, and browser flow. |
| Creative director | Needs human scoring; image quality has clear risks. |
| Asset manager | Passed runtime asset carry/exclusion evidence with quality notes. |
| Video QA | Passed provider-smoke path after poll-only recovery; human creative scoring still required. |
| Safety/release QA | Needs fixes before release recommendation because MiniMax image B remains open. |
| Runbook paths 1-6 | Partial-to-passed for path 6 provider smoke; final runbook acceptance remains user-only. |
| Frontend UI reviewer | Passed after responsive shell fix. |

## Recommendation

AI recommendation is now `recommended` for the user's human-acceptance decision.
The deterministic tests, Runtime/browser evidence, MiniMax image provider
smoke, Kling I2V provider smoke, B-only retry, and readiness audit have no open
P0/P1 provider blocker. This is still not human acceptance, business validation,
or durable-memory promotion. Human acceptance still requires the user to run the
runbook and score creative quality.
