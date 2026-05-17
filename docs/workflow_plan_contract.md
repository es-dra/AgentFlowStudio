# Workflow Plan Contract

Phase 7.7 adds a static workflow planning contract for NarratoCut.

The planner turns a workflow YAML file and a planned input file into a
reviewable draft:

```text
workflow YAML + input file -> workflow_plan.json
```

It does not execute the workflow, call FFmpeg, call remote LLMs, mutate workflow
YAML, create a run directory, generate business artifacts, or control an agent
runtime.

## Inputs

Required inputs:

- workflow YAML path, such as `workflows/mock_text_to_slices.yaml`
- input file path, such as `examples/demo_text/story.txt`

Optional input:

- static tool catalog path, defaulting to `configs/tool_catalog.yaml`

The tool catalog is used only to enrich step purpose text. The workflow YAML
remains the source of step order, node types, inputs, and expected outputs.

## Output

The planner writes:

```text
workflow_plan.json
```

Example:

```json
{
  "schema_version": "0.1",
  "plan_id": "plan_mock_text_to_slices",
  "status": "draft",
  "workflow": {
    "path": "workflows/mock_text_to_slices.yaml",
    "name": "mock_text_to_slices"
  },
  "input": {
    "path": "examples/demo_text/story.txt",
    "type": "file"
  },
  "steps": [
    {
      "step_id": "analyze_hooks",
      "tool": "analyze_hooks",
      "purpose": "Analyze a UTF-8 source text file and produce hook candidates.",
      "inputs": ["input_text_file"],
      "expected_outputs": ["hooks.json"],
      "execution_status": "not_started"
    }
  ],
  "artifacts": {
    "expected": [
      "run_manifest.json",
      "trace.json",
      "quality_report.json",
      "hooks.json"
    ]
  },
  "constraints": [
    "draft_only",
    "no_execution",
    "no_ffmpeg",
    "no_file_mutation_except_plan_output"
  ],
  "risks": [],
  "notes": [
    "This is a draft plan only. It does not execute the workflow."
  ],
  "created_by": "ncut draft-plan"
}
```

Paths in the plan use `/` separators for stable cross-platform consumption.

## Status Rules

The first version uses two statuses:

- `draft`: workflow YAML was parsed and converted into a plan
- `invalid`: workflow YAML was missing, invalid, or failed schema validation

CLI exit behavior:

- `draft`: exit code 0
- `invalid`: exit code 1

## CLI

Generate a static plan:

```powershell
.venv\Scripts\ncut draft-plan --workflow workflows/mock_text_to_slices.yaml --input examples/demo_text/story.txt --output data/reports/workflow_plan.json
```

Expected output shape:

```text
Workflow plan: data/reports/workflow_plan.json
Status: draft
Steps: 4
Execution: not started
```

`data/reports/workflow_plan.json` is a runtime report unless intentionally
promoted as a committed example.

## Boundary

`draft-plan` is a planning contract, not an executor.

Allowed:

- read workflow YAML
- read static tool catalog
- write one `workflow_plan.json`

Not allowed:

- execute workflow nodes
- call FFmpeg
- call remote LLMs
- modify workflow YAML
- create run directories
- write `run_manifest.json`, `trace.json`, or `quality_report.json`
- create video, script, hook, clip plan, or slicing artifacts
- run autonomous agents
