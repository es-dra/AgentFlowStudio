# AFS AOS Current State

Last updated: 2026-07-08.

This file is the compact startup surface for AgentFlow Studio under AOS v1.
Long trackers, devlogs, and handoff archives are not active startup state. Use
Git history or a targeted restored reference only when a task needs a specific
historical record.

## Product Line

AgentFlow Studio is an Agent-native production operating layer for AI content
production.

Current user-facing product surface:

```text
/studio/ canvas -> Runtime Service -> prompt optimization -> fixed visual assets
  -> graph context resolver -> provider-gated keyframe/image evidence
```

Current stage: local internal testing and hardening. Do not claim SaaS readiness,
public release readiness, provider QA, generated-media QA, human acceptance, or
business validation from repository/document changes.

## Local Repo Surface

This file is not a live repository status probe. Run fresh commands before
making claims or choosing a worktree:

```powershell
git status --short
git branch --show-current
git rev-parse HEAD
git rev-parse --abbrev-ref --symbolic-full-name '@{u}'
```

If a broad cleanup is already dirty, finish or isolate it before starting
product/runtime work. Do not mix unrelated product changes into a large
governance or deletion diff unless that is the explicit task.

## Startup Packet Shape

For substantial AFS work, compile or internally apply:

```text
AOS Startup Packet
  -> Goal Contract
  -> Task Packet
  -> Evidence target
  -> Runtime Surface Vector when local/GitHub/server/process/provider state can drift
  -> Integration Queue route
  -> Improvement Queue route
```

Minimum task fields:

```text
target outcome
read scope
write scope
forbidden scope
provider/tool gates
verification route
non-claims
stop conditions
closeout shape
```

## Scale-Up Policy

The compact architecture is not limited to narrow tasks. Larger work should
scale by adding bounded temporary lanes under one accountable main control
thread:

```text
main control thread
  -> worker lane: implementation or cleanup slice
  -> evaluator lane: user-facing/runtime/provider/quality/deletion-risk verdict
  -> integration queue: merge, defer, retire, verify, or escalate
```

Lane requirements:

```text
lane target
read/write/forbidden scope
verification command
evidence artifact or finding shape
stop condition
return route to main control
```

Do not revive permanent role threads. Use workers and evaluators as temporary
resources selected by the Goal Contract.

## Runtime Surface Vector

Before claiming runtime readiness, deployment freshness, provider readiness, or
server state, compile a fresh Runtime Surface Vector covering:

```text
local repo branch/head/dirty/stash
GitHub default branch/unexpected branches/open PRs
server /opt main runtime
server /home working surface
/test worktrees and processes
systemd units
listening ports and process cwd/cmd
provider gates
runtime health and auth boundary
```

This document does not contain a fresh server, GitHub, provider, or runtime
health check.

## Current Drift Risks

Treat these as known drift classes until a fresh Runtime Surface Vector proves
otherwise:

- remote branches can reappear after cleanup;
- masked service units can be inactive while independent processes still listen;
- server `/opt` main runtime and `/home` working surfaces can diverge;
- `/test` worktrees or processes can remain active;
- provider gates can be closed while docs imply provider readiness;
- governance docs can update while runtime state remains stale.

## Default Verification

For docs/projection-only changes:

```powershell
git diff --check
```

For normal code changes:

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main --help
.\.venv\Scripts\python.exe -m apps.cli.main version
.\.venv\Scripts\python.exe -m pytest
git diff --check
```

For maintenance/cleanup with broad blast radius:

```powershell
.\.venv\Scripts\python.exe tools\maintenance_audit.py
```

## Non-Claims

This file is structure and startup-surface evidence only. It does not prove:

- AFS runtime readiness;
- server deploy freshness;
- provider smoke;
- generated-media quality;
- human acceptance;
- business validation;
- public/legal readiness;
- durable memory promotion;
- COS active-rule promotion.

## Documentation Surface

Active project documentation should stay limited to current state, current
architecture, contracts, and verification routes. Historical loop documents
should be deleted from the working tree when Git history preserves them and no
active test or contract needs the file.
