# AFS Studio Mascot And Edge Disconnect Review Handoff

Date: 2026-06-19
Branch: `codex/studio-sprite-character-redesign-20260619`
Base: `aa74120 feat(beta): record human review decisions`
Current commit: `2034666 polish(studio): add mascot companion and edge disconnect`

## Scope

This branch is a Studio front-end review branch. It improves canvas interaction
quality without changing Runtime API, provider routing, provider gates, auth, or
server deployment behavior.

Implemented changes:

- Replaced the visible `AFS 小精灵` shell with a first-pass cartoon mascot skin.
- Added right-click sprite settings with small / medium / large local size
  preferences.
- Kept sprite chat on the existing Runtime sprite chat boundary.
- Added a natural connection removal path: select an edge, show a compact inline
  disconnect button, and allow Delete / Backspace for the selected edge.
- Added static regression coverage for the mascot and edge disconnect contract.

## Review Gate

Do not merge this branch to `master` or deploy it to `/opt` until the user
accepts the mascot visual direction. The edge disconnect behavior is ready for
normal code review, but the mascot is a product/IP direction choice and still
needs human acceptance.

If the mascot direction is accepted:

1. Rebase this branch on current `origin/master`.
2. Run focused Studio checks and full regression if the rebase touches shared
   front-end code.
3. Merge to local `master`.
4. Push `origin/master`.
5. Sync server `/home/afs-ops/AgentFlowStudio` and `/opt/afs/AgentFlowStudio`
   only after GitHub `master` contains the merge.

If the mascot direction is rejected:

1. Keep the edge disconnect implementation.
2. Revise or replace only the mascot skin and settings copy.
3. Preserve the existing tests or update them to the new accepted visual
   contract.

## Verification Already Run

```text
.\.venv\Scripts\python.exe -m pytest -q
-> 543 passed, 527 deselected, 2 warnings

npm run check:studio-js
-> JS syntax check passed: 94 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
-> failed=0, warnings only

git diff --check
-> passed, with one CRLF normalization warning in apps/studio/src/nodes.js
```

Browser smoke evidence:

- Mascot rendered as `data-sprite-character="mascot"`.
- Large size persisted to `afs_studio_sprite_scale`.
- Old mechanical body was hidden by the mascot skin.
- Real render-chain edge disconnect selected edge `e1`, clicked the inline
  control, removed the edge from state, and cleared selection.
- Console warn/error count was 0.

## Boundaries

- No Runtime API shape changed.
- No provider gate changed.
- No provider config changed.
- No provider call was made.
- No provider raw response, signed URL, local media byte, local path, invite
  code, or secret was added.
- This is local static/browser verification, not human acceptance, not provider
  smoke, and not business validation.

