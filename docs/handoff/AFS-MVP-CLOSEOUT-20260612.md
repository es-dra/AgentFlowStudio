# AFS MVP Closeout Evidence - 2026-06-12

中文摘要：本记录是 MVP 内测前收尾证据。当前主线 `master` 已与 `origin/master` 同步；工程测试、gate-closed 浏览器 QA、以及用户授权 image gate 下的真实 MiniMax A/B/C 均已跑通。真实出图使用本机 `mmx_cli` token plan，不读取、不提交、不展示 provider secret。

## Fresh Evidence

- Git health: `git fsck --no-progress` returned only dangling trees; no corrupt, missing, bad, or fatal object signal.
- Git status before closeout work: `master...origin/master`, clean.
- Focused static/runtime tests: `35 passed`, one existing Starlette/httpx warning.
- Studio JS syntax: all `apps/studio/src/**/*.js` passed `node --check`.
- Browser QA: `tools/studio_asset_context_browser_qa.py --report runs/studio_asset_context_browser_qa_report_20260612_closeout.json` passed.
- Browser QA report: `provider_calls_started=false`, `included_asset_count=1`, `temporary_lock_override_count=1`, `context_indicator_visible=true`, `comparison_status=blocked`.
- Browser screenshot: `runs/studio_asset_context_browser_qa.png`.
- Full pytest: `838 passed`, one existing Starlette/httpx warning.
- Maintenance audit: failed=0, warning=1 existing oversized-files warning.
- `git diff --check`: passed with Windows CRLF notice only.

## Live A/B/C Evidence

Authorized gate scope:

```text
AFS_ALLOW_REMOTE_IMAGE=true
AFS_ALLOW_REMOTE_LLM unset
AFS_ALLOW_REMOTE_ASR unset
AFS_ALLOW_REMOTE_VIDEO unset
```

Runner:

```powershell
.\.venv\Scripts\python.exe tools\studio_asset_context_live_comparison.py --provider-config configs\providers.local.json --allow-live-provider --sample-reference-output runs\studio_asset_context_sample_reference_20260612_closeout.png --report runs\studio_asset_context_live_comparison_report_20260612_final.json
```

Result:

- `runner_mode=live_provider`
- `comparison_status=succeeded`
- `provider_gate.status=ready_not_run`
- `provider_calls_started=true`
- Arm A: succeeded, 1 image, no reference image, no fixed asset injection.
- Arm B: succeeded, 1 image, resolver path, fixed asset injection disabled.
- Arm C: succeeded, 1 image, resolver path, fixed asset injection enabled, 1 subject reference image, 1 included fixed asset.

Ignored evidence directory:

```text
runs/studio_asset_context_live_comparison_20260612_final/
```

Important files:

- `runs/studio_asset_context_live_comparison_report_20260612_final.json`
- `runs/studio_asset_context_live_comparison_20260612_final/generation_comparison_report.json`
- `runs/studio_asset_context_live_comparison_20260612_final/A/candidate_001.jpg`
- `runs/studio_asset_context_live_comparison_20260612_final/B/candidate_001.jpg`
- `runs/studio_asset_context_live_comparison_20260612_final/C/candidate_001.jpg`
- `runs/studio_asset_context_live_comparison_20260612_final/visual_observation_summary.json`

## Visual Observation

Codex visual inspection, not human acceptance:

- A generated a male figure in dark clothing on a rainy rooftop. It failed Lin Wan identity, red trench coat, and character locks.
- B generated a young woman in a red trench coat with cinematic rain. It captured the broad prompt but missed short hair and the left-brow scar.
- C generated a young woman with short black hair, red coat, and a visible left-brow marker. The fixed asset package materially improved identity/wardrobe/lock visibility, but the scar was over-literal as a thick black cross-like mark.

Interpretation:

- C is materially better than A and better than B for identity, wardrobe, and visible lock adherence.
- Feature-card wording for `left brow scar` should be refined before broad internal testing, for example toward a subtler “small natural scar above the left eyebrow, not painted makeup or symbol.”

## Local Config Note

The local ignored `configs/providers.local.json` uses MiniMax `execution_backend=mmx_cli`. During closeout it was aligned with Provider Gateway v0.1 by adding the MiniMax image descriptor and `minimax_image_pool`, then preserving CLI-token-plan semantics by not requiring `credential_env` for the `mmx_cli` account path. The file remains ignored and is not committed.

## Non-Claims

- Browser/runtime verification is not human acceptance.
- Live A/B/C output is provider smoke and asset-semantics evidence, not business validation.
- Codex visual observation is not user approval.
- Generated images are ignored runtime evidence, not durable memory.
- Image authorization does not authorize LLM, ASR, video, or external download.
