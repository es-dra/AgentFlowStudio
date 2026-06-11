# AFS-WEB-CANVAS-EXPERIENCE-002 Browser QA

Runtime URL: `http://127.0.0.1:8798/workbench/`

Seeded project: `proj_runtime_demo`

Provider state: gate closed, no provider calls started.

## Covered Path

1. Opened Workbench home.
2. Entered Create.
3. Closed starter mode into the real Runtime canvas.
4. Verified real `.libtv-node` cards render.
5. Hovered a node and verified `.studio-node-actions`.
6. Clicked a node and verified the inspector opens.
7. Ran local prompt optimization and verified `.prompt-optimizer-panel`.
8. Opened Assets and verified `.visible-asset-shelf` and `.visible-asset-card`.
9. Opened Add Node -> Director Desk and verified `.director-desk-board`.
10. Selected Fill Light and verified `.director-light.fill-light.selected`.
11. Repeated mobile canvas visibility at `390x844`.

## Evidence

- `data/processed/runs/workbench_canvas_experience_qa/desktop-home.png`
- `data/processed/runs/workbench_canvas_experience_qa/desktop-canvas.png`
- `data/processed/runs/workbench_canvas_experience_qa/desktop-assets-prompt.png`
- `data/processed/runs/workbench_canvas_experience_qa/desktop-director.png`
- `data/processed/runs/workbench_canvas_experience_qa/mobile-canvas.png`

Console errors: `0`.

