# AFS MVP Closeout Evidence - 2026-06-12

中文摘要：本记录是 MVP 内测前收尾证据。当前主线 `master` 已与 `origin/master` 同步，工程测试和 gate-closed 浏览器 QA 已重新通过；真实 A/B/C 已在用户授权的 image gate 下尝试，但当前本机 shell 缺少 `MINIMAX_API_KEY`，因此在 provider 凭据检查处安全阻塞，未产出真实图片。

## Fresh Evidence

- Git health: `git fsck --no-progress` returned only dangling trees; no corrupt, missing, bad, or fatal object signal.
- Git status: `master...origin/master`, clean before closeout QA; current closeout work only changes QA tooling and this handoff.
- Focused static/runtime tests: `35 passed`, one existing Starlette/httpx warning.
- Studio JS syntax: all `apps/studio/src/**/*.js` passed `node --check`.
- Browser QA: `tools/studio_asset_context_browser_qa.py --report runs/studio_asset_context_browser_qa_report_20260612_closeout.json` passed.
- Browser QA report: `provider_calls_started=false`, `included_asset_count=1`, `temporary_lock_override_count=1`, `context_indicator_visible=true`, `comparison_status=blocked`.
- Browser screenshot: `runs/studio_asset_context_browser_qa.png`.
- Full pytest: `838 passed`, one existing Starlette/httpx warning.
- Maintenance audit: failed=0, warning=1 existing oversized-files warning.
- `git diff --check`: passed with Windows CRLF notice only.

## Live A/B/C Attempt

Authorized gate scope:

```text
AFS_ALLOW_REMOTE_IMAGE=true
AFS_ALLOW_REMOTE_LLM unset
AFS_ALLOW_REMOTE_ASR unset
AFS_ALLOW_REMOTE_VIDEO unset
```

Runner:

```powershell
.\.venv\Scripts\python.exe tools\studio_asset_context_live_comparison.py --provider-config configs\providers.local.json --allow-live-provider --sample-reference-output runs\studio_asset_context_sample_reference_20260612_closeout.png --report runs\studio_asset_context_live_comparison_report_20260612_closeout_r3.json
```

Result:

- `runner_mode=live_provider`
- `provider_gate.status=ready_not_run`
- `provider_calls_started=true`
- all A/B/C arms remained `blocked`
- block reason: provider configuration is not ready because the current shell does not provide `MINIMAX_API_KEY`
- no provider image output was produced
- no human acceptance, business validation, or durable memory promotion is claimed

Local ignored config note: `configs/providers.local.json` was updated locally to include the v0.1 MiniMax image descriptor and `minimax_image_pool` metadata copied from `configs/providers.example.json`. The file remains ignored and is not committed.

## Remaining MVP Gate

The next unblock is not code. Load the MiniMax credential into the shell environment expected by the account pool:

```powershell
$env:MINIMAX_API_KEY = "<local secret>"
$env:AFS_ALLOW_REMOTE_IMAGE = "true"
```

Then rerun the live A/B/C command above and score the generated A/B/C images before sending the MVP to internal testers.

## Non-Claims

- Browser/runtime verification is not human acceptance.
- Provider dispatch reaching credential validation is not live provider success.
- A/B/C is still blocked-env evidence until real image outputs exist.
- Image authorization does not authorize LLM, ASR, video, or external download.
