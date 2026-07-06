# AFS P1 Dirty Owner Holds D1/D4/D3 Patch Manifest - 2026-07-06

top_down_dispatch_id:
`TD-AFS-V02-PRESERVE-P1-DIRTY-OWNER-HOLDS-D1-D4-D3-PATCH-MANIFEST-NO-REMOTE-20260706-001`

bottom_up_feedback_id:
`BU-AFS-V02-PRESERVE-P1-DIRTY-OWNER-HOLDS-D1-D4-D3-PATCH-MANIFEST-NO-REMOTE-20260706-001`

verdict: `PASS_DIRTY_OWNER_MANIFEST_CREATED`

## Scope

This record preserves compact dirty-owner evidence for D1, D4, and D3 before
any later cleanup, archive, branch deletion, or worktree deletion decision.

Accepted posture consumed from readonly evaluator feedback
`BU-AFS-V02-REVIEW-P1-DIRTY-OWNER-HOLDS-D1-D4-D3-CONTENT-DISPOSITION-READONLY-20260706-001`:
D1/D4/D3 dirty contents are superseded for code integration, but exact dirty
patch/blob/status evidence must be preserved before cleanup/archive if that
route is later authorized. D3 branch identity requires special care because its
head is not ancestor-contained in the accepted base.

## Preservation Branch

| Field | Value |
|---|---|
| Branch | `codex/preserve-p1-dirty-owner-holds-20260706` |
| Worktree | `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\preserve-p1-dirty-owner-holds-20260706` |
| Base ref | `origin/master` |
| Base SHA at creation | `26512312eb6c6f311108c97b906667dfbf21b6b9` |
| Remote action | none |
| Provider/runtime/browser/media action | none |
| Source worktree mutation | none; readonly `git status`, `git diff`, `git ls-files`, `Get-FileHash`, and ancestry checks only |

## Hold Summary

| Hold | Branch | Head SHA | Worktree | Dirty summary | Ancestry readback | Classification | Current route |
|---|---|---|---|---|---|---|---|
| D1 | `codex/afs-d1-provider-preflight-hardening-20260702` | `f00fbc6c1404a4c3b812056a0f142626edb75ea8` | `C:\Users\chenzy\Documents\Codex\2026-07-02\afs-d1-provider-preflight-hardening` | 11 modified tracked files, 1 untracked file | head is ancestor of `origin/master` and primary `HEAD` | superseded dirty owner hold; preservation evidence only | keep until CEO/CTO cleanup/archive decision; do not integrate dirty diff |
| D4 | `codex/afs-d4-runtime-log-artifact-hardening-20260702` | `f00fbc6c1404a4c3b812056a0f142626edb75ea8` | `C:\Users\chenzy\Documents\Codex\2026-07-02\afs-d4-runtime-log-artifact-hardening` | 7 modified tracked files, 3 untracked files | head is ancestor of `origin/master` and primary `HEAD` | superseded dirty owner hold; preservation evidence only | keep until CEO/CTO cleanup/archive decision; do not integrate dirty diff |
| D3 | `codex/afs-d3-runtime-readiness-auth-hardening-20260702` | `0be328b672b873727868a4c66539f2a30b752bc3` | `C:\Users\chenzy\Documents\Codex\2026-07-02\afs-lane-d3-f00fbc6c` | 14 modified tracked files, 0 untracked files | head is not ancestor of `origin/master` and not ancestor of primary `HEAD` | superseded dirty owner hold with non-contained branch identity | preserve commit and dirty identity before any archive/delete route |

## Dirty Path Lists

### D1

```text
## codex/afs-d1-provider-preflight-hardening-20260702...origin/master [behind 59]
 M DEVLOG.md
 M apps/api/runtime_generation_comparisons.py
 M apps/api/runtime_generation_preflight.py
 M apps/api/runtime_keyframe_routes.py
 M apps/api/runtime_models.py
 M apps/api/runtime_video_routes.py
 M docs/openapi/afs-runtime-service.openapi.json
 M tests/test_api_runtime_asset_card_revision_legacy_slots.py
 M tests/test_api_runtime_keyframe_reference_assets.py
 M tests/test_api_runtime_video_generations.py
 M tests/test_volc_seedance_video_adapter.py
?? tests/test_api_runtime_provider_submit_preflight.py
```

### D4

```text
## codex/afs-d4-runtime-log-artifact-hardening-20260702
 M DEVLOG.md
 M TASK_TRACKER.md
 M apps/api/runtime_file_logging.py
 M apps/api/runtime_logging.py
 M apps/api/runtime_service.py
 M apps/api/runtime_store.py
 M docs/handoff/INDEX.md
?? apps/api/runtime_log_safety.py
?? docs/handoff/AFS-RUNTIME-LOG-ARTIFACT-LEAKAGE-HARDENING-20260702.md
?? tests/test_runtime_log_artifact_hardening.py
```

### D3

```text
## codex/afs-d3-runtime-readiness-auth-hardening-20260702...origin/master [ahead 1, behind 59]
 M DEVLOG.md
 M apps/api/runtime_info.py
 M docs/handoff/AFS-D3-RUNTIME-READINESS-AUTH-CLAIM-BOUNDARY-HARDENING-20260702.md
 M tests/test_afs_internal_beta_acceptance.py
 M tests/test_afs_internal_beta_preflight_three_end.py
 M tests/test_afs_public_edge_preflight.py
 M tests/test_afs_three_end_status.py
 M tests/test_api_runtime_service.py
 M tools/afs_internal_beta_acceptance_preflight.py
 M tools/afs_internal_beta_preflight_public_edge.py
 M tools/afs_internal_beta_preflight_three_end.py
 M tools/afs_public_edge_preflight.py
 M tools/afs_readiness_claims.py
 M tools/afs_three_end_status.py
```

## Patch Hash Evidence

Patch hashes are SHA-256 hashes of redirected `git diff --binary --no-ext-diff`
output, computed in memory without writing patch files.

| Hold | Unstaged binary diff bytes | Unstaged binary diff SHA-256 | Staged binary diff bytes | Staged binary diff SHA-256 |
|---|---:|---|---:|---|
| D1 | 174435 | `33da197e748b86a3db2d6c53b586aed8b5f41d9909d24a66c1d7d1aa25e65292` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| D4 | 14715 | `09b08d6fe976e991ae64d1bd51a30083d5e4a3d3348e144c5c0ad2aff69ae311` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| D3 | 23362 | `13df5549b354d36b03ddecfebb162a0fb6d51df0f5cf326b647f1ae89fc44971` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

## Current File Blob Hash Evidence

### D1 File Hashes

| Path | Bytes | SHA-256 |
|---|---:|---|
| `apps/api/runtime_generation_comparisons.py` | 14284 | `01876b5f81b0fbfff1d63af5d189daabcb48c3c1c9e3c40f94d3051dceb9b357` |
| `apps/api/runtime_generation_preflight.py` | 11222 | `e010db999ad9a2728e494aea009c0f343416c78240652b13ecc700d2216fa994` |
| `apps/api/runtime_keyframe_routes.py` | 23113 | `50bd331c6d3354e58c6efbeac0696892d9117c68a757dac55cc287ad63752c5f` |
| `apps/api/runtime_models.py` | 14140 | `e8c2e1385848928b64050bb0e540a11e4bfa1e7ff1fbbc24ec5272ef342c3732` |
| `apps/api/runtime_video_routes.py` | 19923 | `3e9ba1a5559f4bbda93fb5b0592fd2ddc25621737c0755b9ba842f16a7f92ed6` |
| `DEVLOG.md` | 490309 | `1f4074ae0272715a45bfb98a0db41f9579e1c3c97a1153a0cfc2e81d2797e80d` |
| `docs/openapi/afs-runtime-service.openapi.json` | 64476 | `5c321c0e1847d21cda56c029f00fbefa048abaf7d701479f316dcb5567a823ef` |
| `tests/test_api_runtime_asset_card_revision_legacy_slots.py` | 5152 | `4ffa7b8b1ddff3ee4453712ef0ac37037f7fc670b75894131069fcf9165e62b8` |
| `tests/test_api_runtime_keyframe_reference_assets.py` | 33585 | `94809aeba87297c2c060bf2db00cc5c560589d96769bdc8a34d2918c4b904535` |
| `tests/test_api_runtime_provider_submit_preflight.py` | 13930 | `c5e95b603fd07c569b7aede06a5bc08bd53605149458ef1955d8f065a47ca26e` |
| `tests/test_api_runtime_video_generations.py` | 42119 | `1d4fc41e1d1b0d68b3b4045590972b45741f801bf3652de38c8a4994e50f6eae` |
| `tests/test_volc_seedance_video_adapter.py` | 20877 | `d6e0bbde68629ed3572643f4eadf45d0c87d152e790e23e35b8ea7da2477215f` |

### D4 File Hashes

| Path | Bytes | SHA-256 |
|---|---:|---|
| `apps/api/runtime_file_logging.py` | 7781 | `ba9179c703c9bbb2dba2850c942d0ca90eb37b9288817a6f73b08d1d00e04dbf` |
| `apps/api/runtime_log_safety.py` | 3037 | `2782818f0f561917825f4fc835c607cfba60e9ab16621efb29d550235de20ede` |
| `apps/api/runtime_logging.py` | 9927 | `397d2c312a79814d108cad94d09a49fde43b5d2e9bc0615c7300a621006770b7` |
| `apps/api/runtime_service.py` | 17622 | `ef0d8625ee2037445301a267be0ba9e6044f593544aedf2ce61340f53a3eb0e6` |
| `apps/api/runtime_store.py` | 13193 | `444da76b3483b5c5a207a48b5fc83539abc82c504237a9e9ebc1e5c6077956b3` |
| `DEVLOG.md` | 489296 | `6a770984e0b5b9025afbcaa79f78eb68cf34115f4434ad08df3e7d091f911b15` |
| `docs/handoff/AFS-RUNTIME-LOG-ARTIFACT-LEAKAGE-HARDENING-20260702.md` | 3024 | `224004dfe4ca144cff05e6ce222335a3736f2a3203b03fdb5b44f1c1691a46b0` |
| `docs/handoff/INDEX.md` | 9819 | `b7a9c2528a835c3d18d35f0eb47bac28b8aa684ed60cd079088a960a588c0914` |
| `TASK_TRACKER.md` | 235627 | `33477263a0390911171d29341d953ac7a00e42f32b9dfb47157c98a2db11c019` |
| `tests/test_runtime_log_artifact_hardening.py` | 7529 | `ac1a5e54f2683336f9f0981b1ce653503c4dce93725f982e112dde2acf3199fb` |

### D3 File Hashes

| Path | Bytes | SHA-256 |
|---|---:|---|
| `apps/api/runtime_info.py` | 7659 | `e1027e673d1f9efaef8621117db1bf75afc3779be1facdccc1d09f81d75e3583` |
| `DEVLOG.md` | 489347 | `c9ed3e5cdbfbd96d5e47f9bcf115f6a499a5c4d3e473036d2ad78b9bd4db9634` |
| `docs/handoff/AFS-D3-RUNTIME-READINESS-AUTH-CLAIM-BOUNDARY-HARDENING-20260702.md` | 2143 | `02fa3fe6c816130b52643879c91e408cf2aa3fc40a04f6caff219b4c5116f4ee` |
| `tests/test_afs_internal_beta_acceptance.py` | 12633 | `0a2c242c35c7c53940729b3ed408016b378a0a6ec44b35a3bb150042814fa534` |
| `tests/test_afs_internal_beta_preflight_three_end.py` | 6884 | `7c14c8ec49cfcb524951e74aa734240fa350165f972e023860d400d68edfa73e` |
| `tests/test_afs_public_edge_preflight.py` | 5736 | `017b6b8ce68f3c03ca3bb0d14a4f631a0817924481df655f241fd1d3cad4b956` |
| `tests/test_afs_three_end_status.py` | 6874 | `d07fc894e018f42442ebaabef60e1a40a20e9128a1835545e8aec264b73037bb` |
| `tests/test_api_runtime_service.py` | 16908 | `e0053a874ee247ee32297c7626501f32bf0d13cdf59c474a59edd8f1e90702eb` |
| `tools/afs_internal_beta_acceptance_preflight.py` | 10395 | `834bc2bcb62ad50ed58c2e11a096caef3987bc861d17bd98d47a2664ba1e88c7` |
| `tools/afs_internal_beta_preflight_public_edge.py` | 3343 | `69a2da9447ccc0800f43263c60c1566f11601fe659c004c4125cd903a83fdad6` |
| `tools/afs_internal_beta_preflight_three_end.py` | 5232 | `3bfee663f2c0630d3714e8cf1429e90276fab9c6ffee4b14c1b83d23f1e70a00` |
| `tools/afs_public_edge_preflight.py` | 11049 | `837d47fd2071425d7267ee9f802cd96384102e389fe5f6b8a5a01b7fb085cd24` |
| `tools/afs_readiness_claims.py` | 626 | `445faaa33f04c993a66bb4be28a8c2f57c91f9cc739f0b17d83dac38894d0ea0` |
| `tools/afs_three_end_status.py` | 9570 | `6975eddceb29ac3766d5520a6686a326342f34f053e278b1120efbb2a1546296` |

## Verification Readback

Readonly evidence commands used:

```text
git -C <source_worktree> status --short --branch
git -C <source_worktree> rev-parse HEAD
git -C <source_worktree> branch --show-current
git -C <source_worktree> diff --name-status --
git -C <source_worktree> diff --cached --name-status --
git -C <source_worktree> ls-files --others --exclude-standard
git -C <source_worktree> diff --binary --no-ext-diff
git -C <source_worktree> diff --cached --binary --no-ext-diff
Get-FileHash -Algorithm SHA256 <dirty_or_untracked_file>
git -C D:\Projects\AgentFlowStudio merge-base --is-ancestor <head> origin/master
git -C D:\Projects\AgentFlowStudio merge-base --is-ancestor <head> HEAD
```

Record verification commands:

```text
git diff --check
git status --short --branch
```

Source worktree untouched evidence:

- D1/D4/D3 were not reset, cleaned, moved, deleted, archived, checked out,
  staged, committed, pulled, pushed, or otherwise modified by this lane.
- Post-record readback repeated the same dirty path lists and the same patch
  hashes shown above.

## Residual Risks

- This manifest stores compact identity evidence only. It does not store full
  patch content, so it proves identity and supports later forensic comparison
  but does not by itself reconstruct a deleted worktree.
- D3 requires extra caution before any branch/worktree archive because its head
  `0be328b672b873727868a4c66539f2a30b752bc3` is not ancestor-contained in
  `origin/master` or the primary checkout head.
- No tests were run for D1/D4/D3 dirty contents; those contents remain
  superseded for code integration.

## Non-Claims

- No cleanup, archive, move, branch deletion, worktree deletion, or source
  worktree mutation.
- No remote push, PR, fetch, pull, source sync, deploy, restart, provider call,
  provider gate mutation, browser QA, Runtime/server action, generated-media QA,
  human/Owner/business/public/legal acceptance, release, package finality,
  CompanyOS/COS/source-KB mutation, durable-memory promotion, or self-archive.
- No claim that D1/D4/D3 dirty diffs should be integrated.

archive_policy: `no self-archive; CEO/CTO must decide cleanup/archive/defer after BU registration and decision-owner consumption`

upward_feedback_delivery: `sent_to_ceo`

post_closeout_next_action:
CEO/CTO should register this manifest, then decide one exact route for each
hold: keep on hold, request an external backup artifact, archive/delete the
worktree after acceptance, or defer with a named owner. No automatic cleanup is
valid in this lane because the task scope explicitly prohibited cleanup,
archive, delete, branch deletion, and Owner acceptance.
