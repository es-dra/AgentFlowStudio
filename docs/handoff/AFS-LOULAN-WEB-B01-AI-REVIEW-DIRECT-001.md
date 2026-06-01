# AFS-LOULAN-WEB-B01-AI-REVIEW-DIRECT-001

## Scope

Recognize Loulan B01 AI pre-review files as read-only Memory Workbench
selected-file artifacts.

## What Changed

- Added the `loulan_b01_ai_director_pre_review` contract alias for
  `ai_director_pre_review.json`.
- Added the `loulan_b01_ai_suggested_decision_starting_point` contract alias
  for `ai_suggested_decision_starting_point.json`.
- Extended the Loulan B01 inspector so both files show recommendation counts,
  pending operator decisions, and no-call/no-memory/no-acceptance boundaries.

## Real Probe

Inputs:

```text
D:\Projects\LoulanSceneAssets\reviews\B01-horizontal-pack\ai_director_pre_review.json
D:\Projects\LoulanSceneAssets\reviews\B01-horizontal-pack\ai_suggested_decision_starting_point.json
```

Observed selected-file state:

- `ai_director_pre_review.json`
  - Artifact type: `loulan_b01_ai_director_pre_review`
  - Artifact class: `known_contract`
  - Source role: `Loulan B01 AI director pre-review`
  - Status: `ai_recommendation_only_pending_human_decision`
  - Recommendations: `5`
  - Suggested approve anchors: `3`
  - Suggested repairs: `1`
  - Suggested approve-with-note: `1`
- `ai_suggested_decision_starting_point.json`
  - Artifact type: `loulan_b01_ai_suggested_decision_starting_point`
  - Artifact class: `known_contract`
  - Source role: `Loulan B01 AI suggestion starting point`
  - Status: `suggestion_only_not_human_acceptance`
  - Items: `5`
  - Pending operator decisions: `5`
  - Suggested approve anchors: `3`
  - Suggested repairs: `1`
  - Suggested approve-with-note: `1`

Shared boundary facts:

- Provider calls started: `false`
- Writes long-term memory: `false`
- Human acceptance recorded: `false`

## Verification

```powershell
.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_static_loulan_b01_ai_review.py -q
```

Result: `2 passed`.

## Boundaries

- No provider calls.
- No media generation or media copy.
- No package regeneration required for direct file review.
- No B01 decision apply.
- No context projection.
- No human acceptance recorded.
- No durable Memory write.
