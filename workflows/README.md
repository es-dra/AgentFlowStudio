# Workflows

This directory contains YAML workflow definitions for NarratoCut.

## Available workflows

### `mock_roi_to_script.yaml`

Phase 3 demo workflow:

1. `analyze_hooks`
2. `generate_scripts`

Example:

```powershell
.venv\Scripts\ncut run-workflow --workflow workflows/mock_roi_to_script.yaml --input examples/demo_text/story.txt --output data/processed/runs/demo_workflow
```

Generated files are written to the output directory. Runs under `data/processed/` are ignored by git.

### `mock_text_to_slices.yaml`

Phase 6 full mock workflow:

1. `analyze_hooks`
2. `generate_scripts`
3. `generate_clip_plans`
4. `mock_slice`

Example:

```powershell
.venv\Scripts\ncut run-workflow --workflow workflows/mock_text_to_slices.yaml --input examples/demo_text/story.txt --output data/processed/runs/demo_full_mock
```

This workflow writes `hooks.json`, `scripts.json`, `clip_plans.json`, `slice_manifest.json`, and `.txt` mock clips under `clips/`.
