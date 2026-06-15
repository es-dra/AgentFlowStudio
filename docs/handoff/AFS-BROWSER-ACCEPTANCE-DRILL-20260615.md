# AFS Browser Acceptance Drill 20260615

## Claim Level

This handoff records an AI/browser pre-acceptance drill. It is not human
acceptance, business validation, durable-memory promotion, or a decision to
enter internal testing.

Claude review was skipped for this round because the local Claude quota was
exhausted. The drill used Codex Browser execution plus deterministic/runtime
evidence.

## Branch And Evidence

- Branch: `codex/afs-browser-acceptance-drill-20260615`
- Runtime entry: `/studio/` on local Runtime 8790 from this worktree
- External evidence root name: `20260615-afs-browser-acceptance-drill`
- Repository evidence policy: this repo stores only safe summaries, test code,
  tracker entries, and this handoff.

Provider gates:

- LLM: opened for prompt optimization smoke
- Image: opened for two planned MiniMax calls, then one additional Path 3
  rerun explicitly authorized by the user
- Video: opened for one Kling I2V submit
- ASR: closed
- External download: closed

Do not store or print provider config paths, secrets, provider raw responses,
signed URLs, local private media bytes, or generated media bytes in repository
files.

## Result

Overall status: AI/browser pre-acceptance `recommended`, pending human
acceptance.

Passed:

- Path 1: project create, switch, refresh, node and prompt persistence
- Path 2: T2I LLM optimization plus MiniMax image generation
- Path 3: reference-backed I2I MiniMax rerun after explicit user approval;
  safe manifest recorded `reference_image_count=1`, `candidate_count=1`, and
  `context_included_asset_count=1`
- Path 4: fixed visual asset promotion, signature, feature card, locks, detail,
  and refresh re-display
- Path 5: fixed asset carry/exclusion passed through the auxiliary browser QA
  runner without opening image/video provider gates on that path
- Path 6: Kling I2V explicit first frame, submit, poll, preview, and reload
  recovery
- Responsive smoke: 1440x950, 768x900, and 390x844 had no page-level horizontal
  overflow or console warn/error logs
- Security smoke: safe manifests did not persist provider raw responses,
  provider URLs, media bytes returned by API, signed URLs, or local absolute
  paths

Residual risks:

- I2I optimizer explicit-edit preservation still needs a regression: the
  earlier optimizer path
  used reference-preserving tone but contradicted requested background/clothing
  edits. The passing Path 3 rerun used the original explicit edit prompt rather
  than relying on that optimized text.
- Human acceptance and creative quality scoring have not been performed by the
  user.

Next action:

The user should run the human acceptance runbook and score MiniMax/Kling
creative quality before deciding whether to enter internal testing.

## Evidence Files

External evidence files:

- `browser_qa_summary.json`
- `provider_smoke_summary.json`
- `readiness_audit.json`
- `studio_node_check_recursive.json`
- `gate_closed_focused_pytest.txt`
- `asset_context_browser_qa.json`
- `path2_after_minimax_t2i_confirmed.png`
- `path3_i2i_after_llm_optimize.png`
- `path3_second_image_call_not_reference_confirmed.png`
- `path3_i2i_reference_before_rerun.png`
- `path3_i2i_reference_carry_confirm.png`
- `path3_i2i_reference_after_rerun.png`
- `path3_i2i_reference_rerun_summary.json`
- `path4_asset_detail_popover.png`
- `path6_after_reload_video_preview.png`
- `ui_desktop_1440x950_final.png`
- `ui_narrow_768x900.png`
- `ui_mobile_390x844.png`

Safe provider IDs:

- Project: `studio-1781460479681-37qe3g`
- T2I image asset: `img_5369204bd11e`
- Fixed visual asset: `vas_d2c98968764c`
- Path 3 reference-backed I2I job:
  `studio-1781460479681-37qe3g-keyframe_generation-c8f9612a06c1`
- Path 3 reference image asset: `img_a0bf51f39e90`
- Kling job: `studio-1781460479681-37qe3g-video_generation-13a94915d320`

## Code Change

`tools/afs_mvp_joint_qa_readiness_audit.py` now recognizes browser-drill
evidence when `browser_qa_summary.json` has artifact type
`afs_browser_acceptance_drill_summary`. In this mode it checks provider smoke
from:

- `runtime_service/**/keyframe_generation_safe_manifest.json`
- `runtime_service/**/video_generation_safe_manifest.json`

The older joint-QA evidence format is preserved. A regression test covers
browser-drill manifests and role gaps.

## Verification

Completed:

```text
focused gate-closed pytest: 58 passed, 1 warning
Studio JS node --check: 37 files passed
tests/test_afs_mvp_joint_qa_readiness_audit.py: 8 passed
readiness_audit.json: recommended, provider_blocker_count=0, passed_role_count=7
pytest -q: 406 passed, 527 deselected, 2 warnings
pytest -m legacy -q: 527 passed, 406 deselected, 1 warning
maintenance_audit.py: failed=0, warnings only
git diff --check: exit 0
```

Continuation verification after the authorized Path 3 rerun:

```text
tests/test_afs_mvp_joint_qa_readiness_audit.py tests/test_api_runtime_keyframe_reference_assets.py: 11 passed, 1 warning
readiness_audit.json: recommended, provider_blocker_count=0, passed_role_count=7
maintenance_audit.py: failed=0, warnings only
git diff --check: exit 0
```

Use the main repository virtualenv if the isolated worktree does not have its
own `.venv`.
