# AgentFlow Studio Contributor Onboarding

This document is the short entry for new technical contributors. It points to
current project rules instead of duplicating the full handoff history.

## Clone And Update

Clone once:

```powershell
git clone https://github.com/es-dra/AgentFlowStudio.git
cd AgentFlowStudio
```

Later updates:

```powershell
git fetch origin
git pull --ff-only
```

Do not repeatedly reclone unless the local checkout is intentionally discarded.

## Collaborator Model

Development uses GitHub collaboration:

- Maintainer invites the developer as a repository collaborator.
- Developer works in their own local checkout.
- Developer creates a branch per task.
- Developer opens a PR or hands off a reviewed branch.
- Maintainer reviews and merges.

Do not share one local working directory across people.

## Required Reading

Start from:

```text
AGENTS.md
docs/company_operating_model.md
docs/GFR_EXECUTION_PROJECTION.md
docs/AOS_CURRENT_STATE.md
docs/README.md
```

Historical trackers, devlogs, and handoff archives are not startup context. Use
Git history or a targeted restored reference only when a task needs specific
historical evidence. Do not make old loop records the default read scope.

For software engineering standards, also read the installed CompanyOS docs:

```text
CompanyOS/full-stack/engineering-standard.md
CompanyOS/full-stack/api-contract.md
CompanyOS/full-stack/frontend-boundary.md
CompanyOS/full-stack/release-checklist.md
```

## Branch Rule

Do not develop directly on `master`.

```powershell
git checkout -b feature/<short-task-name> origin/master
```

For non-trivial work, use a separate worktree if the current checkout is dirty
or the task touches Runtime, Studio Web, provider adapters, contracts, schemas,
or broad cleanup.

## Local-Only Material

Never commit:

- `.env` or local config;
- provider keys or tokens;
- signed URLs;
- raw provider responses;
- generated media bytes unless a project policy explicitly allows it;
- customer material;
- real costs;
- private Company OS source material.

## Current Product Boundary

The current product entry is `/studio/`.

Runtime Service is the frontend/backend boundary. Frontend code should consume
safe Runtime APIs, OpenAPI, safe manifests, stable IDs, and summaries. It
should not depend on CLI internals, provider secrets, local absolute paths, raw
provider responses, signed URLs, or media bytes.

## Verification

Baseline commands:

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main --help
.\.venv\Scripts\python.exe -m apps.cli.main version
.\.venv\Scripts\python.exe -m pytest
git diff --check
```

Maintenance or cleanup tasks also run:

```powershell
.\.venv\Scripts\python.exe tools\maintenance_audit.py
```

If a command cannot run, record why and state the residual risk.

## Feedback To CompanyOS

Reusable process lessons should become feedback candidates, not automatic
Company OS rules. Put project-local evidence in focused current AFS docs first;
maintainers decide what moves back to private COS or public CompanyOS.
