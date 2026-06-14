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
- Provider scope: LLM, MiniMax image, Kling I2V attempt.
- Excluded scope: ASR and external downloads.
- Added role: frontend UI reviewer.

## Verification Summary

| Layer | Result | Evidence |
|---|---|---|
| Gate-closed focused tests | Passed, 53 tests | `gate_closed_focused_pytest_after_tool_patch_retry.txt` and rerun output |
| Default pytest | Passed, 396 tests | Final rerun output after readiness audit |
| Legacy pytest | Passed, 527 tests | Final rerun output after readiness audit |
| Studio JS syntax | Passed, 37 files | `studio_node_check.txt` and rerun output |
| Product browser smoke | Passed | `gate_closed_8790_ui_smoke_corrected_report.json` |
| LLM prompt optimization smoke | Passed with two prompt optimization manifests | `live_llm_browser_runtime/*prompt_optimization_safe_manifest.json` |
| MiniMax image smoke | Partial: A and C succeeded, B blocked after retry | `live_minimax_image_comparison_report.json` |
| Kling I2V smoke | Blocked before provider call by local provider config | `live_kling_i2v_report.json` |
| Frontend UI reviewer | Failed first pass, passed after responsive shell fix | `frontend_ui_reviewer_after_fix2_report.json` |
| AI role pre-acceptance | Needs fixes / inconclusive | `ai_role_pre_acceptance_summary.json` |
| Continued blocker preflight | Passed deterministic hardening checks | `kling_provider_preflight_after_blocker_hardening.json`, `gate_closed_live_comparison_after_arm_block_summary.json` |
| Readiness audit | Needs fixes, no-cost aggregation | `afs_mvp_joint_qa_readiness_audit.json` |

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
- Kling preflight now reports structured blocker IDs. The current no-cost
  preflight classifies the remaining video blocker as
  `provider_service_missing`, with no available video service IDs and
  `secrets_printed=false`.
- Generation comparison arm evidence now includes safe `blocks` and
  `retry_count`; the live-comparison runner summarizes per-arm `block_ids` and
  `retry_count`, so future MiniMax arm B failures no longer collapse into an
  opaque `blocked` status.
- Added a no-cost readiness audit tool that aggregates the external evidence
  root into seven role checks and provider blockers. The current audit status is
  `needs_fixes`, with two provider blockers and no human acceptance claim.

### Open P1 / Blockers

- `P1-KLING-CONFIG-MISSING`: current local provider config exposed no video-like
  service and the Kling credential environment variables were not present.
  Runtime correctly blocked before provider calls started. A real Kling smoke
  needs a local ignored config that includes `kling_i2v` plus valid credential
  environment variables. Continued no-cost preflight now confirms this as
  `provider_service_missing`.
- `P1-IMAGE-B-PROVIDER-READINESS`: MiniMax comparison arm B, the no-reference
  context-subgraph arm, blocked after one retry with a safe provider readiness
  error. Arms A and C succeeded. No extra retry was run because the image-call
  cap was already consumed. Future reruns will expose arm-level `block_ids` and
  `retry_count` in the runner summary.

### Human-Scored Quality Risks

- MiniMax arm A generated a male subject for a `Lin Wan` prompt without a fixed
  reference.
- MiniMax arm C preserved a female red-coat/black-hair identity with the fixed
  asset, but the brow scar was visually too heavy and needs human scoring.
- Kling first-frame fidelity, motion adherence, and stability could not be
  scored because live Kling provider execution did not start.

## Seven-Role Pre-Acceptance

| Role | AI pre-acceptance result |
|---|---|
| Ordinary internal tester | Passed runtime basics: create, reload, switch, and browser flow. |
| Creative director | Needs human scoring; image quality has clear risks. |
| Asset manager | Passed runtime asset carry/exclusion evidence with quality notes. |
| Video QA | Blocked by local provider config before live Kling execution. |
| Safety/release QA | Needs fixes before release recommendation because two P1s remain. |
| Runbook paths 1-6 | Partial: paths 1-5 have evidence; path 6 blocked at provider config. |
| Frontend UI reviewer | Passed after responsive shell fix. |

## Recommendation

Do not claim internal-test acceptance yet. The correct AI recommendation is
`needs fixes / inconclusive` until the Kling config is present and the image B
provider-readiness issue is either reproduced/fixed or classified with stronger
provider evidence. Before the next live retry, rerun the no-cost readiness audit
so the blocker state is explicit. Human acceptance still requires the user to
run the runbook.
