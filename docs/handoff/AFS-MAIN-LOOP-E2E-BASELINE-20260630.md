# AFS Main Loop E2E Baseline

## Task

- Task ID: `AFS-T41`
- Branch: `codex/afs-goal-mode-main-loop-e2e-20260630`
- Base: `a7d536a4c22412c5f3f77cfcf5da8fb6fbaa3718`
- Mode: provider-closed Runtime E2E regression
- Evidence state:
  `runtime_verified_provider_closed_main_loop_e2e_no_provider_no_acceptance`

This slice keeps AFS positioned as an AI-native manga/video/image content
production workbench. Goal-mode and loop mechanics are engineering controls, not
the product identity.

## Objective

Add the first deterministic Runtime E2E regression for a real benchmark script:

```text
real script -> storyboard/content quality -> fixed asset reuse
  -> production graph -> evidence ledger -> human gate
  -> feedback candidate -> feedback overlay -> keyframe preflight context
```

## What Changed

- Added `tests/test_api_runtime_main_loop_e2e.py`.
- Updated `agentflow/algorithms/human_gate/__init__.py` so human-gate
  `target_id` preserves CJK asset-card candidate suffixes.
- Updated `agentflow/algorithms/fixed_asset_memory/promotion_gate.py` so
  fixed-asset source evidence preserves CJK candidate refs.

## Root Cause

The real baseline script emits candidate IDs such as:

```text
asset_card_candidate:graph_character_林晚
```

The human-gate and fixed-asset source-evidence sanitizers only allowed ASCII
tokens. That silently truncated the CJK suffix to:

```text
asset_card_candidate:graph_character
```

The individual ASCII contract tests passed, but the end-to-end Chinese script
path lost exact candidate binding across Human Gate and Keyframe Context.

## Verification

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_main_loop_e2e.py -q
# 1 passed, 1 warning

.\.venv\Scripts\python.exe -m pytest
# 771 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; existing warning classes only

git diff --check
# passed
```

Maintenance note:

- New test file is 295 lines, under the 300-line ideal threshold.
- Existing maintenance audit warnings remain existing categories:
  `legacy_frozen_surface`, `human_doc_chinese_coverage`,
  `secret_like_fragments` with `high_confidence_count=0`, and
  `oversized_files`.

## Non-Claims

- Not provider smoke.
- Not a live provider call.
- Not generated media.
- Not human creative acceptance.
- Not business validation.
- Not public release or customer validation.
- Not patent/legal decision.
- Not COS active-rule promotion.

## Cleanup Review

- No duplicate Runtime route, OpenAPI path, provider gate, or Studio UI surface
  was added.
- The fix keeps sanitizer changes local to the two evidence-boundary helpers.
- The new E2E test is a regression harness for current main-loop contracts, not
  a parallel product path.

## Next Valid Action

Continue the provider-closed main-loop path with one of:

- Add another real benchmark case that stresses multi-character asset handoff.
- Extend the E2E harness from preflight into blocked local keyframe generation
  bridge evidence.
- Classify and reduce current-wave record/test redundancy before the next
  merge-review threshold.

Do not open provider smoke, video, high-cost generation, external download,
public claims, business validation, human creative acceptance, or COS
active-rule promotion without explicit authorization.
