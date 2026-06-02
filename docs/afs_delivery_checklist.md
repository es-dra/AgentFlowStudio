# AgentFlow Studio v0.1.0 Delivery Checklist

AgentFlow Studio `v0.1.0` is the first deliverable distribution-side module of
AgentFlow Studio. It is a local-first CLI/Agent MVP for short-video highlight
selection, slicing, packaging, reporting, and review.

## Definition Of Done

- `origin/master` contains the previous delivery branch content, and stale
  merged remote branches have been removed.
- README and architecture docs state that AgentFlow Studio is a distribution-side
  module of AgentFlow Studio.
- Recommended product workflows are documented:
  - `workflows/video_to_finished_package_local_asr.yaml`
  - `workflows/video_script_to_finished_package_local_asr.yaml`
- Recommended agent skills are documented:
  - `skills/short_highlight_package.skill.yaml`
  - `skills/video_script_highlight_package.skill.yaml`
- `run_manifest.json` includes an artifact map and `artifact_index`.
- `review_report.json` includes `quality_level` and `delivery_status`.
- `package_report.md`, `review_report.json`, `quality_report.json`, and
  delivery readiness reports are the official handoff artifacts.
- Project, feedback, platform profile, and asset lifecycle contracts are
  documented and include examples with `schema_version`.
- The golden sample path is documented and has explicit local dependency
  requirements.
- Full verification passes:
  - `pytest`
  - `python -m compileall apps agentflow agentflow_studio agentflow_production tests`
  - `git diff --check`
  - `python -m apps.cli.main --help`
  - `python -m apps.cli.main version`
- `v0.1.0` tag is created and pushed after the verified commit lands.

## Out Of Scope

- Web UI or desktop UI.
- AgentFlow Production production-side workflow.
- AgentFlow Router runtime.
- AgentFlow Memory runtime.
- Hosted API, database, queue, SaaS deployment, or multi-user permissions.
- Automatic platform publishing.
- Timeline editor, transition templates, or multi-track editing.
- Real OCR frame extraction/provider integration.
- Mature multimodal highlight detection.

## Known Limitations

- Highlight selection is deterministic and text-first; it is suitable for MVP
  review, not a final claim of viral/editorial maturity.
- Local ASR quality depends on the configured faster-whisper model and source
  audio quality.
- Audio boundary evidence is advisory and does not replace manual clip review.
- Platform profiles are examples and are not automatically enforced by
  workflows.
- `project_manifest.json` and `feedback.jsonl` are contracts only; no runtime
  manager writes or consumes them yet.
- The golden sample requires ignored local media and model cache files.

## Release Meaning

`v0.1.0` means:

```text
Local-first CLI/Agent MVP for distribution-side short highlight packaging.
```

It does not mean:

```text
Full AgentFlow Studio platform, Web UI product, or mature creative-selection engine.
```
