# AgentFlow Artifact Map

The AgentFlow artifact map is a cross-module registry draft. It records which
module owns an artifact, which module may consume it, and whether the artifact
is a source, derived output, review surface, or candidate signal.

This is a contract-layer document only. It does not implement a registry
service.

## Registry Rules

- Every artifact map document must have `schema_version`.
- Machine-facing artifact names stay in English.
- Human-facing descriptions may be localized.
- Raw feedback and derived feedback signals must remain separate.
- Candidate memory is not promoted memory.
- Markdown reports are review views, not strong contract sources.
- Generated media, local run outputs, and private paths must not be committed
  as official examples.

## Artifact Classes

| Class | Meaning | Examples |
| --- | --- | --- |
| source | Human, project, or external input. | `creative_brief.json`, source video |
| contract | Machine-readable artifact contract. | `production_handoff.json`, `run_manifest.json` |
| decision | Auditable selection or promotion decision. | `router_decision.json`, promotion decision |
| derived | Generated from other artifacts in one run. | `feedback_signal_log.json` |
| candidate | Proposed reusable signal awaiting review. | `memory_candidates.json` |
| report | Human-readable review surface. | `production_report.md`, `package_report.md` |
| media | Local generated or source media file. | `final_video.mp4`, clips |

## Current Cross-Module Flow

```text
project_manifest.example.json
-> creative_brief.json
-> NarratoStudio workflow
-> production_handoff.json
-> production_report.md
-> router_decision.json
-> skill_invocation.json
-> skill_result.json
-> future production execution layer
-> media / clip plan / final video
-> NarratoCut workflow
-> finished_package_manifest.json
-> package_report.md
-> review_report.json
-> feedback.jsonl
-> feedback_signal_log.json
-> memory_candidates.json
-> future promotion decision
```

The production execution layer in the middle is not implemented in this
repository.

## Minimal Registry Entry

An artifact map entry should include:

- `artifact_id`: stable id inside the project.
- `artifact_type`: machine-readable type.
- `module_owner`: owning module.
- `artifact_class`: source, contract, derived, candidate, report, or media.
- `path`: project-relative path or run-relative path.
- `produced_by`: workflow, skill, human, or external system reference.
- `consumed_by`: modules or workflows expected to read it.
- `source_refs`: upstream artifact ids.
- `status`: draft, available, superseded, or archived.

See [`../examples/agentflow/artifact_map.example.json`](../examples/agentflow/artifact_map.example.json).
