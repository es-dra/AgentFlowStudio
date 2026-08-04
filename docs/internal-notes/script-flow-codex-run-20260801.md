# Script Flow — Codex Session Run (2026-08-01)

Source: separate Codex session on the same local worktree / temp Runtime.
Saved for evidence continuity with `script-flow-findings-20260801.md`.

```text
worktree:     /home/afs-ops/worktrees/afs-agent-working-mode-20260729
branch:       codex/agent-working-mode-20260729
HEAD:         466fe97fe904acaa309ff582e6e4c4e07b4ba8d6
runtime:      http://127.0.0.1:8797
project_id:   proj_last_light_20260801
provider gate: closed (deterministic only; no remote LLM)
```

Session note: dirty worktree already present (`.gitignore`, `docs/internal-notes/`); Codex treated this as runtime-only and did not edit repo files for the run itself.

---

## What Codex ran

1. Startup scan (`pwd`, `git status`, `AGENTS.md` / docs read, health check).
2. Confirmed temp Runtime ready; provider gates closed.
3. Submitted a new Script Truth revision via
   `POST /projects/proj_last_light_20260801/script-revisions`.
4. Ran deterministic M6 preview via
   `POST /projects/{project_id}/m6/script-plan-asset-bible/preview`
   with header `X-Client-Request-ID`.
5. Polled preview run until terminal state.

---

## Identifiers

| Field | Value |
|---|---|
| `source_revision_id` | `scrrev_9f3d686832b74175` |
| `source_revision_digest` | `02674232e5cfe7b78663b63654d4e9acc4e901a43256a08f26657de87a49e3f7` |
| `run_id` | `m6-preview-845622dd85209849cea53c82` |
| status / phase | `preview_ready` / `succeeded` |
| provider | `local_runtime` / `local_deterministic` / `deterministic_contract` |
| `dispatch_count` | `0` |
| Invented M6 script revision | `m6-script-e1fff68b2c36` |

---

## Observed vs expected

| Check | Observed | Expected |
|---|---|---|
| Characters detected | `苏晴没`, `从信封`, `道他可能` | `苏晴`, `老王`, `林悦` |
| Scene labels extracted | `柜台前`, `柜台上`, `礁石上`, `她身边坐下`, `书桌前`, `一叠信纸上` | `老式邮局`, `海边礁石`, `苏晴的房间` |
| Structural validation | **PASS** (`P0: 0`, `P1: 0`, canonical scope PASS) | Real locations + real names |
| Separate M6 script revision invented | **Yes**: `m6-script-e1fff68b2c36` | Reuse Script Truth `scrrev_*` only |

---

## Codex conclusion (verbatim substance)

The bug is still present: deterministic M6 preview structurally passes while extracting meaningless fragments and minting a separate `m6-script-*` revision id instead of using only the Script Truth `scrrev_*` identity.

This reinforces the central finding in `script-flow-findings-20260801.md`:

- `succeeded` / `PASS` is **not** proof of Chinese script comprehension.
- Scene/character extraction can emit fragment junk and still clear validation.
- Dual revision ids (`scrrev_*` vs `m6-script-*`) remain confirmed.

---

## Session friction notes (operational)

- Host had no `python` binary; `python3` worked.
- First preview attempt failed with HTTP 422 until header was exactly `X-Client-Request-ID`.
- OpenAPI schema name for M6 preview request body was not present as `M6ScriptPlanAssetBiblePreviewRequest` in components; request shape was taken from Runtime code/OpenAPI path.

---

## Non-claims

- Local temp Runtime evidence only.
- Not a GitHub / `master` change.
- Not live `/opt` deploy verification.
- Not provider smoke or human acceptance.
