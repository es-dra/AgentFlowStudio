# Director Compiler v1

Director Compiler v1 is a deterministic backend compiler for Studio 2D director
setups. The frontend passes structure only; prompt semantics are compiled on the
Runtime side.

## Input

`DirectorSetup2D` accepts:

- `activeCameraId`: camera id that should drive the shot language.
- `activeSubjectIds`: subjects that participate in the shot.
- `subjects[].visual_asset_id`: optional fixed visual asset id. The frontend may
  pass ids only, not signatures, feature cards, or locks.

If `activeCameraId` is missing, the compiler defaults to the first camera and
writes a warning. If `activeSubjectIds` is empty, all subjects are compiled.

## Output

`DirectorCompileResult v1` includes:

- `sections[]`: Chinese cinematography sections for subject blocking, camera and
  shot scale, lighting, spatial props, motion continuity, and negative
  constraints.
- `warnings[]`: deterministic warnings, including shot/geometry conflicts.
- `active_camera_id`
- `active_subject_ids`
- `asset_refs_used[]`
- `trace_summary`

## Rules

- Camera-subject geometry is translated into shot language. Raw coordinate/FOV
  readouts are not prompt language.
- Distance and FOV infer a shot scale; conflicts with manually selected shot
  scale produce warnings.
- Light position, temperature, softness, and intensity are translated into
  photographic language.
- Props are described by relative subject position when possible.
- Visual asset signatures are read by backend id from the visual asset store.
  Frontend-provided signatures are ignored.

## Frontend Boundary

`directorPromptSummary` is a UI summary only. It is safe for previews and panel
labels, but it is not the authoritative prompt compiler.
