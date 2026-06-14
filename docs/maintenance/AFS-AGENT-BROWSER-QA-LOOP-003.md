# AFS Agent-Led Browser QA Loop 003

Started: 2026-06-13 14:51 +08:00
Branch: codex/afs-agent-browser-qa-loop-003
Scope: browser QA recording only; no product code fixes.
Provider policy: live LLM/image/video calls allowed for purposeful QA, candidate_count=1.
Evidence directory: runs/agent_browser_qa_loop_003/

## Environment Baseline

- Git baseline: master at 4136b40 before branch creation; QA branch `codex/afs-agent-browser-qa-loop-003` created from clean master.
- Runtime: existing service listening on `http://127.0.0.1:8790` (process 36556 at start of run).
- Browser surface: Codex in-app browser, existing Studio tab reused.
- Provider state: shell process env did not include AFS gates because Runtime was started externally; actual LLM/image/video behavior was verified through Runtime calls.
- Write boundary: product code was not changed. This branch only adds this QA report; screenshots and safe summaries are under `runs/agent_browser_qa_loop_003/`.

## Issue Ledger

| ID | Severity | Role/Path | Repro Steps | Actual | Expected | Evidence | Suspected Cause | Suggested Fix | Blocks Beta |
|---|---|---|---|---|---|---|---|---|---|
| QAL003-001 | P1 | Creator / fixed asset conflict | Open `Loop QA Fresh 1781312383942`, select `图片节点 2`, whose prompt requests a young woman with red long hair while it carries fixed asset `Conflict Test Character`; click bottom generate. | No pre-submit confirmation appears. Generation starts immediately. Safe plan shows `subject_reference_asset_id=vas_b20a2c5aa26d`, `reference_image_count=1`, warnings for red/black and long/short. Output remains male/dark-coat identity dominated. | Before paid submit, UI should clearly block or confirm that fixed asset/reference will override the visible prompt, with actions like continue carrying asset, exclude asset for this run, or cancel. | `round2-conflict-submit-click.png`, `round2-conflict-generation-result.png`, `round2-conflict-safe-summary.json` | Conflict warnings are only result/bundle-level, not a pre-submit interlock. Resolver correctly detects conflict, but frontend does not require a choice. | Add pre-submit conflict modal and request-level `temporary_asset_exclusions[]` or equivalent one-run exclusion trace. | Yes, for asset semantic trust. |
| QAL003-002 | P1 | Asset admin / generated image promotion | In fresh project `QALOOP0031781333651144`, run T2I generation, open generated image in canvas and drawer `显性资产`. | Generated image can be viewed, set as reference, used for current node, or located on canvas. No discoverable “固定为人物资产/场景资产” action exists from node result or drawer item. | A generated image candidate should be directly promotable to fixed character/scene asset from the node or drawer, matching the MVP asset workflow. | `round1-generation-result.png`, `round2-assets-tab.png`, `round2-asset-item-click.png` | Promotion action appears only in some node states/asset-bearing nodes, not on fresh generated image candidates. | Add “固定为资产” action to generated image candidate card/detail and node result. | Yes, for asset workflow completion. |
| QAL003-003 | P1 | Asset admin / asset detail trust | In conflict project, click the `1资产` badge on `图片节点 2`. | Detail popover says fixed asset status and signature, but `特征卡` and `锁定项` show `未缓存`; the same generation bundle uses `keep black short hair` locks and emits conflict warnings. No remove/exclude action exists. | Asset detail should display the actual backend-resolved feature card/locks, or clearly label cached summary vs resolver truth. It should also expose node-level remove/exclude affordance. | `round3-asset-badge-detail.png`, `round2-conflict-safe-summary.json` | Popover reads cached node `visualAssets` summary rather than full visual asset store, while resolver reads store by id. | Fetch asset detail by id from Runtime for popover; add “从当前节点移除/本次不携带” actions. | Yes, because users cannot audit what will constrain generation. |
| QAL003-004 | P2 | New user / project switching | Create project named `QALOOP0031781333651144`, switch to `31780`, then inspect project dropdown. | New project disappears from default dropdown because it is folded into “hidden test projects”; clicking “显示全部项目” reveals it. | A newly created active project should remain easy to return to, even if its name matches QA/test heuristics. | `round1-created-project.png`, `round1-show-all-projects.png`, `round1-switch-back.png` | Project filtering classifies names containing QA/loop/test as test projects immediately after switching away. | Keep recently created/current-user projects visible, or make filtering source-based instead of name-based. | No, but confusing during QA/internal use. |
| QAL003-005 | P2 | Video user / video result honesty | Open existing Kling video node in `Loop QA Fresh 1781312383942`. UI preset reads `16:9 · 720P · 5s · 声音`; inspect generated mp4 with ffprobe. | Video preview works, but ffprobe shows only one h264 video stream and no audio stream. UI implies sound. | If provider output is silent, UI should not display “声音” as if audio exists; show audio disabled/unknown until actual audio support is present. | `round4-video-node-preview.png`, `round4-video-ffprobe.json` | Preset label includes sound regardless of output/media stream. | Hide sound label or derive it from descriptor/output stream metadata. | No, but trust/polish issue. |

## Round Notes

### Round 1: 小白路径 / Fresh Project T2I

Project: `QALOOP0031781333651144` (`studio-1781333672108-sso7z5`)

Passed:

- “新建项目” uses an in-page modal, not native `window.prompt`.
- Project creation switched immediately to the new URL and selected project.
- Fresh project canvas was empty; no old nodes leaked into the new project.
- Created keyframe/image node through central onboarding action.
- T2I optimize succeeded and showed mode chip `文生图扩写`.
- T2I image generation succeeded through MiniMax image path; UI showed `已完成` and `本次未携带固定资产`.
- Refresh restored generated preview from Runtime safe endpoint.
- Provider prompt in `keyframe_request_plan.json` had no human display segment headers; `reference_image_count=0`, `context_included_assets=0`.

Evidence:

- `round1-created-project.png`
- `round1-keyframe-node.png`
- `round1-optimize-result.png`
- `round1-generation-result.png`
- `round1-after-reload.png`
- `round1-keyframe-safe-summary.json`

Notes:

- Browser automation text input could not use bulk fill/type because the in-app browser virtual clipboard is unavailable. ASCII keypress input worked. This is a QA tooling limitation, not counted as product issue.
- PowerShell `ConvertFrom-Json` failed on `keyframe_request_plan.json`, but Python `json.loads` succeeded; artifact is valid JSON. This is not counted as product issue.

### Round 2: 图片创作 / Asset Conflict

Project: `Loop QA Fresh 1781312383942` (`studio-1781312384129-vx6iab`)

Findings:

- Existing conflict node carries fixed character asset `vas_b20a2c5aa26d` while visible prompt asks for a young woman with red long hair.
- Result bundle shows warnings, but submit is not gated by any confirmation.
- Re-running generation produced another male/dark-coat identity result.
- Safe summary confirms `subject_reference_asset_id=vas_b20a2c5aa26d` and `reference_image_count=1`.

Evidence:

- `round2-conflict-project-open.png`
- `round2-node2-selected.png`
- `round2-conflict-submit-click.png`
- `round2-conflict-generation-result.png`
- `round2-conflict-safe-summary.json`

### Round 3: 资产语义 / Detail & Promotion

Findings:

- Fresh generated image candidate cannot be promoted from drawer/detail to fixed visual asset.
- Fixed asset badge detail shows status/signature but not actual lock/card data used by resolver.
- No obvious node-level “remove this asset from current node” or “do not carry this run” action.

Evidence:

- `round2-assets-tab.png`
- `round2-asset-item-click.png`
- `round3-asset-badge-detail.png`

### Round 4: 视频路径 / Existing Kling Preview

Passed:

- Existing Kling video node restored and rendered `<video controls>` from Runtime safe preview endpoint.
- Preview source is `/projects/.../video-generations/.../preview`, not provider URL or local path.
- `readyState=4` in browser.

Finding:

- UI says `声音`, but generated mp4 contains no audio stream.

Evidence:

- `round4-video-node-preview.png`
- `round4-video-ffprobe.json`

## Uncovered / Deferred In This Recording Branch

- Did not intentionally fix any issue.
- Did not perform new Kling paid submit in this branch; video path was verified using an existing successful live result.
- Did not run full Round 5 destructive stress after P1 issues were already clear; recommended next QA pass after fixes should include rapid switch, duplicate submit, empty prompt, and refresh mid-job.

## Current Recommendation

Fix order suggested for the next implementation branch:

1. P1 asset conflict pre-submit interlock and one-run asset exclusion.
2. P1 generated image candidate promotion entry.
3. P1 asset detail backed by Runtime asset store and node-level remove/exclude actions.
4. P2 project filtering recent-project visibility.
5. P2 video sound label honesty.
