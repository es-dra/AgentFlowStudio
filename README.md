# NarratoCut

NarratoCut is an AI narrative-to-promo video workflow system for short dramas, animated dramas, and novel-promo content.

The first MVP focuses on one reproducible production chain:

```text
subtitle/text -> hooks -> scripts -> clip_plans -> vertical videos -> metadata package
```

This is a clean-room project. The previous AVP workspace is treated as reference material only, not as a codebase to migrate.

## Current Scope

NarratoCut starts as a CLI-first, schema-first, workflow-first system. The early implementation avoids a full web app, database, SaaS features, multi-agent runtime, and async task queue.

## Project Layout

```text
apps/                 CLI, API, and future web entrypoints
narratocut/           Core Python package
workflows/            YAML workflow definitions
prompts/              Auditable prompt templates
configs/              Example configuration files
examples/             User-facing demo inputs
data/                 Local runtime data; generated files are ignored
docs/                 Architecture and operating notes
tests/                Automated tests and fixtures
```

## Model Gateway Boundary

`narratocut.model_gateway` is the internal adapter layer. New API, LiteLLM, DeepSeek, Qwen, or other OpenAI-compatible services are external model gateways/endpoints. NarratoCut does not vendor or copy New API code.

Remote LLM calls are disabled by default. Set `NARRATOCUT_ALLOW_REMOTE_LLM=true` only when real provider calls are intended.

## Quick Start

Recommended Python version: 3.12. The project currently declares `>=3.11,<3.13`; Python 3.13 is not recommended yet because ASR, video, and model-adjacent dependencies often lag the newest runtime.

```powershell
cd D:\Projects\NarratoCut
python -m apps.cli.main --help
python -m apps.cli.main version
```

After editable install:

```powershell
pip install -e .[dev]
ncut --help
ncut version
pytest
```
