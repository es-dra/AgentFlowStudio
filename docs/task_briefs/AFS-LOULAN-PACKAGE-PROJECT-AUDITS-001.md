# AFS-LOULAN-PACKAGE-PROJECT-AUDITS-001 Task Brief

## Goal

Expose Loulan project-level audit gates from `project_manifest.json` in the
AFS no-call package and Web Memory Workbench package review.

## Non-Goals

- Do not call image, video, LLM, ASR, or download providers.
- Do not copy media files.
- Do not infer B01 approval or apply decisions.
- Do not write durable Memory or Company memory.

## Write Scope

- `agentflow/memory/loulan_package.py`
- `apps/web/memory-workbench-loulan-package.js`
- `apps/web/memory-workbench-inspector.js`
- `apps/web/memory-workbench-loulan-package-inspector.js`
- `examples/agentflow/loulan_memory_package.example.json`
- focused tests and project records

## Acceptance Criteria

- Package JSON includes `project_audits.manifest_reference` and
  `project_audits.text_encoding`.
- Package Markdown report shows both statuses.
- Web package review surfaces the audit statuses in bundle, protocol, and
  inspector views.
- Real Loulan probe remains blocked by B01 human review and promotion gates.
- No provider/media/secret/absolute-path leakage is introduced.

## Verification

```powershell
pytest tests\test_loulan_memory_package.py tests\test_web_memory_loulan_package_static.py tests\test_loulan_memory_package_registry.py -q
python -m apps.cli.main loulan-memory-package --project-root D:\Projects\LoulanSceneAssets --created-at 2026-06-01T08:40:00+08:00 --output data\processed\runs\loulan_memory_package\local_probe_project_audits
```

## Status

Implemented and verified locally. See
`docs/handoff/AFS-LOULAN-PACKAGE-PROJECT-AUDITS-001.md`.
