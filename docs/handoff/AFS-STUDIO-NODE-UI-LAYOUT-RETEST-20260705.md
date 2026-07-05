# AFS Studio Node UI Layout Retest

Date: 2026-07-05
Branch: `zhaowei`
Scope: `/studio/` canvas node card layout only

## User Feedback

Latest screenshots showed two UI problems after the first node resize pass:

- Large empty text nodes looked like a small centered island inside a huge card.
- Default/smaller text nodes could let intent rows escape the card, including
  the text-to-music option.

## Fix

This pass treats the issue as a node layout design problem rather than a font
scaling problem.

- `canvas-view.js` assigns layout classes from the bounded rendered node frame:
  `empty-tool-node`, `compact-node`, `roomy-node`, and `tall-node`.
- Default/compact empty text nodes use a denser tool-list layout so all seven
  intent rows remain inside the card.
- Wide empty nodes switch to a balanced two-column action grid at 420px+ width.
- Node body overflow is controlled again so intent rows do not draw outside the
  card border.
- Typography remains normal tool UI size; it is not scaled with node size.

## Files

- `apps/studio/src/canvas-view.js`
- `apps/studio/styles/node-resize.css`
- `tests/test_studio_interaction_layer.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`

## Verification

```text
python -m pytest tests\test_studio_interaction_layer.py tests\test_web_studio_static.py tests\test_web_studio_frontend_wave.py tests\test_web_studio_prompt_script_static.py -> 60 passed
npm.cmd run check:studio-js -> JS syntax check passed: 122 files
git diff --check -> passed
```

## Server Retest Points

- Create a default text node. All intent rows should remain inside the card.
- Confirm the text-to-music option is visible.
- Resize the node wider than about 420px. Intent rows should switch to two
  columns.
- Resize taller/wider. Text should keep normal tool UI size rather than scaling
  up.
- Runtime/API/provider behavior is intentionally unchanged.
