# AFS MVP Follow-up Live Comparisons - 2026-06-12

中文摘要:本交接记录内测前第 2、3 组真实 MiniMax image 补测。第 2 组验证"人物 + 场景双资产"同时生效,且场景在不占用主体参考图位时仍能通过文本通道约束画面。第 3 组验证"锁定默认压制用户冲突文本"和"本次临时解除只影响当前生成"。

## Scope

- Image gate only: `AFS_ALLOW_REMOTE_IMAGE=true`.
- LLM, ASR, video, and external download gates were not opened.
- Local ignored provider config: `configs/providers.local.json`.
- Provider backend: MiniMax image through local `mmx_cli` token-plan path.

## Implementation

- Added `tools/studio_asset_context_followup_comparisons.py`.
- Extended `tools/studio_asset_context_sample_reference.py` with a deterministic observatory scene reference image.
- Added `tests/test_studio_asset_context_followup_comparisons.py`.
- Updated the A/B/C runbook so Group 3 requires both locked and temporary-unlocked live runs.
- Updated the feature-card template with follow-up observations.

## Group 2 - Character + Scene Assets

Stable evidence copied from the first successful run:

```text
runs/studio_asset_context_followup_20260612_group2_success/
```

Important files:

- `runs/studio_asset_context_followup_20260612_group2_success/group2_success_evidence_manifest.json`
- `runs/studio_asset_context_followup_20260612_group2_success/runtime_evidence/`
- `runs/studio_asset_context_followup_20260612_group2_success/group2_character_scene/A/candidate_001.jpg`
- `runs/studio_asset_context_followup_20260612_group2_success/group2_character_scene/B/candidate_001.jpg`
- `runs/studio_asset_context_followup_20260612_group2_success/group2_character_scene/C/candidate_001.jpg`
- `runs/studio_asset_context_followup_20260612_group2_success/visual_observation_summary.json`

Result:

- A/B/C all succeeded in the first run.
- C included both fixed assets in the context bundle.
- C used exactly one subject reference image, assigned to the character asset.
- Scene asset entered the text channel only.

Codex visual observation, not human acceptance:

- A showed a broken dome/ruin, but no reliable Lin Wan identity.
- B showed cold observatory mood and a human silhouette, but identity and red coat were weak.
- C showed short black-haired woman, red trench coat, observatory/telescope structure, and cold blue palette. The scar avoided the earlier black cross-like failure but remains more prominent than ideal.

## Group 3 - Lock Conflict And Temporary Unlock

Stable evidence:

```text
runs/studio_asset_context_followup_20260612_group3_retry/
```

Important files:

- `runs/studio_asset_context_followup_group3_retry_report_20260612.json`
- `runs/studio_asset_context_followup_20260612_group3_retry/runtime_evidence/`
- `runs/studio_asset_context_followup_20260612_group3_retry/group3_lock_conflict/locked/candidate_001.jpg`
- `runs/studio_asset_context_followup_20260612_group3_retry/group3_lock_conflict/temporary_unlocked/candidate_001.jpg`
- `runs/studio_asset_context_followup_20260612_group3_retry/visual_observation_summary.json`

Result:

- Locked run succeeded and emitted lexical conflict warnings for red/long hair versus black/short hair locks.
- Locked output kept black short hair and red trench coat despite the visible prompt asking for red long hair.
- Temporary-unlocked run succeeded and recorded the hair lock override in `context_bundle.temporary_lock_overrides`.
- Temporary-unlocked output shifted to red long hair, confirming the override changes only this provider prompt.

## Provider Intermittency

One immediate Group 2 rerun was blocked by the provider/CLI safe error after the first success. The blocked rerun is preserved as evidence:

```text
runs/studio_asset_context_followup_group2_final_report_20260612.json
```

This is treated as provider intermittency, not resolver failure, because:

- The first Group 2 run completed all three arms successfully.
- The blocked rerun still shows B succeeded and C had the correct bundle before provider submission failed.
- The failure reason is a safe provider/CLI readiness error, not a context validation error.

## Verification

```text
.\.venv\Scripts\python.exe -m pytest tests\test_studio_asset_context_followup_comparisons.py -q
.\.venv\Scripts\python.exe -m py_compile tools\studio_asset_context_followup_comparisons.py tools\studio_asset_context_sample_reference.py
git diff --check
```

Focused result: `3 passed`, one existing Starlette/httpx warning. `git diff --check` has Windows CRLF notices only.

## Non-Claims

- Live outputs are provider smoke and asset-semantics evidence only.
- Codex visual observation is not human acceptance.
- This is not business validation.
- Generated images remain ignored runtime evidence, not durable memory.
- Image authorization does not authorize LLM, ASR, video, or external download.
