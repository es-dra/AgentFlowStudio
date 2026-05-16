# AGENTS.md

## Mission

NarratoCut is an AI narrative-to-promo video workflow system.

Current MVP chain:

```text
subtitle/text -> hooks -> scripts -> clip_plans -> videos -> metadata
```

## Operating Rules

- Do not migrate code from `D:\Projects\AVP` unless the user explicitly asks.
- Do not commit secrets, provider keys, signed URLs, cookies, tokens, or private credentials.
- Do not commit large media files or generated runtime artifacts.
- Do not call remote LLMs unless `NARRATOCUT_ALLOW_REMOTE_LLM=true`.
- Prefer schema-first design for workflow inputs, outputs, and intermediate artifacts.
- New features should include focused tests or a clear reason when tests are deferred.
- Keep files focused. Ideal file length is 300 lines or less.
- Keep `workflow_engine` responsible for execution order.
- Keep `harness` responsible for task contracts, evidence, and gates.

## Local Configuration

- Use Python 3.12 for local development. Do not switch the project to Python 3.13 until media, ASR, and model dependencies are verified.
- Commit only example configuration files.
- Use `configs/models.yaml` for local model settings; it is ignored by git.
- Keep `configs/models.example.yaml` as the committed template.
- Use `.env` or `.dev.vars` only locally; both are ignored.

## Verification

Before claiming a change is complete, run the relevant verification command. For Phase 0 bootstrap, use:

```powershell
python -m apps.cli.main --help
python -m apps.cli.main version
pytest
```
