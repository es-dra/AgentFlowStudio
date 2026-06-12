# AFS-DIRECTOR-COMPILER-V1 Handoff

Branch: `codex/afs-director-compiler-v1`

## Scope

- Added deterministic backend Director Compiler v1.
- Extended `DirectorSetup2D` with `activeCameraId`, `activeSubjectIds`, and
  subject `visual_asset_id`.
- Replaced user-prompt director readout with compiler output.
- Added resolver integration so generation companion text includes compiled
  director sections.
- Updated Studio director panel:
  - default setup no longer includes bedroom props/modifiers;
  - empty lists stay empty;
  - missing objects can be added from the object list;
  - active camera/subjects are explicit;
  - subject can bind a visual asset id;
  - prompt fragment action confirms and appends instead of overwriting.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_web_studio_static.py tests/test_runtime_director_compiler.py tests/test_api_runtime_director_setup_prompt.py tests/test_api_runtime_context_resolver.py
node --check apps/studio/src/director-data.js
node --check apps/studio/src/panels/director-shell.js
node --check apps/studio/src/panels/director-fields.js
```

Results:

- Focused Runtime/Web set: 24 passed.
- Changed director JS syntax checks: passed.

## Boundaries

- Frontend preview is only a UI summary. Runtime compiler remains authoritative.
- No provider gate was opened.
- Browser QA for live interaction remains useful after cleanup branch because this
  slice was verified with static/Runtime tests only.
