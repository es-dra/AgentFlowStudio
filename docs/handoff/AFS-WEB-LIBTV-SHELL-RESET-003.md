# AFS-WEB-LIBTV-SHELL-RESET-003

## Status

Implemented in branch `codex/afs-web-refoundation-vertical-001`.

## What Changed

- Replaced the user-facing Workbench shell with a LibTV-style dark creator product shell.
- Ordinary navigation is now only `首页`, `创作画布`, and `资产库`.
- Removed user-path exposure of old engineering pages and words such as project memory, generation gates, diagnostics, provider, Runtime, CommandHub, and ProductionBoard.
- `/workbench/` now opens a creator portal with hero cards, recent projects, inspiration cards, and template entries.
- `开始创作` opens a full-screen canvas with left project rail, center node canvas, bottom node dock, and right node settings panel.
- The default canvas shows the AFS creative flow: script input, storyboard, character turnaround, scene asset, keyframe, director desk, video clip, and final composition.
- The visible asset library only shows explicit reusable assets: characters, scenes, keyframes, video, audio, and director setup assets.
- Director Desk is now a first-class canvas node with a 2D lighting layout, reference area, camera/subject/light controls, and user-facing output actions.
- Prompt optimization is exposed as a small creator action in the right panel with professional prompt sections.
- Internal diagnostics are debug-only through `Alt+D` or `?debug=1`.

## Browser QA Evidence

Runtime-hosted QA was run against:

```text
http://127.0.0.1:8799/workbench/
```

Evidence:

```text
data/processed/runs/libtv_shell_reset_003_browser_qa/browser_qa_report.json
data/processed/runs/libtv_shell_reset_003_browser_qa/screenshots/desktop-home.png
data/processed/runs/libtv_shell_reset_003_browser_qa/screenshots/desktop-canvas.png
data/processed/runs/libtv_shell_reset_003_browser_qa/screenshots/desktop-director.png
data/processed/runs/libtv_shell_reset_003_browser_qa/screenshots/desktop-prompt-optimizer.png
data/processed/runs/libtv_shell_reset_003_browser_qa/screenshots/desktop-assets.png
data/processed/runs/libtv_shell_reset_003_browser_qa/screenshots/mobile-home.png
data/processed/runs/libtv_shell_reset_003_browser_qa/screenshots/mobile-canvas.png
data/processed/runs/libtv_shell_reset_003_browser_qa/screenshots/mobile-director.png
data/processed/runs/libtv_shell_reset_003_browser_qa/screenshots/mobile-prompt-optimizer.png
data/processed/runs/libtv_shell_reset_003_browser_qa/screenshots/mobile-assets.png
```

QA result: `passed`.

Covered:

- Desktop and mobile home portal.
- Desktop and mobile creation canvas.
- Director Desk node creation and right panel sync.
- Prompt optimizer panel.
- Visible asset library.
- Default debug entry hidden.
- `Alt+D` debug toggle.
- No user-visible forbidden engineering terms in checked surfaces.
- No horizontal page overflow in checked surfaces.
- No console or page errors.

## Boundaries

- No MiniMax, image, video, or other live provider call was started.
- No secret, provider key, signed URL, local private media, provider raw response, or generated media bytes were committed.
- This is runtime/browser verification, not human acceptance or business validation.

## Next Recommended Slice

Keep the current product shell stable and move next into real user flow depth:

1. Make script upload/paste create editable storyboard cards in the canvas.
2. Let visible assets be applied to the selected node without leaving the canvas.
3. Add a simple generation queue receipt for every button that currently registers a local intent.
4. Only after the user manually accepts the shell, run a separate MiniMax LLM gate smoke for prompt/storyboard generation.
