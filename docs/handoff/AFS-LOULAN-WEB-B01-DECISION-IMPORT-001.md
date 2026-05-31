# AFS-LOULAN-WEB-B01-DECISION-IMPORT-001

Status: static Web visibility for Loulan B01 decision imports implemented.

## Scope

When a selected file has:

```text
artifact_type: agentflow_loulan_promotion_decisions
import_summary: {...}
```

the Memory Workbench now treats it as a B01 import view rather than only a
generic decision template.

## UI Surfaces

| Surface | Behavior |
|---|---|
| Bundle summary | shows `B01 decision import` and imported-ready / pending / skipped counts |
| Protocol controls | shows `B01 decision import` with no-acceptance detail |
| Next pass | prefixes status with `Decision import` |
| Artifact inspector | shows `source_block_id`, `imported_ready`, `pending`, and `skipped_local_items` |
| Timeline | labels the node `B01 Decision Import` |

## Boundary Evidence

- The Web slice is read-only static selected-file rendering.
- It does not edit decision files, persist browser changes, run context
  projection, call providers, copy media, or infer acceptance.
- Imported decisions still require decision intake and context bundle gates
  before any next-pass context can be used.

## Verification Snapshot

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_memory_loulan_decision_context_static.py -q
# 5 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_web_memory_loulan_decision_context_static.py tests\test_web_memory_loulan_package_static.py tests\test_web_memory_loulan_human_review_static.py tests\test_web_memory_static_structure.py tests\test_web_memory_sample_static.py -q
# 16 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain -q
# 742 passed

.\.venv\Scripts\python.exe -B tools\staging_preflight.py --repo-root .
# passed

git diff --check
# passed; CRLF normalization warnings only
```

## Next Work

- After the operator fills B01 decisions and reruns the import bridge, select
  the imported decision JSON in the Memory Workbench alongside the package,
  review pack, intake report, and context projection artifacts.
- Keep the UI read-only unless a separate browser persistence/editing task is
  explicitly scoped.
