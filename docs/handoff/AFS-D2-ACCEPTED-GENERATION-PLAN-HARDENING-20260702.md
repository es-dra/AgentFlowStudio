# AFS D2 Accepted Generation Plan Hardening - 2026-07-02

## Status

`implementation_ready_for_evaluator`

Lane D2 hardens the accepted generation plan preview path so bundled fixtures
remain non-acceptance demo evidence, while accepted project plan packets require
project-scoped source evidence plus a matching local human-gate decision.

## Branch And Boundary

Worktree:

```text
C:\Users\chenzy\Documents\Codex\2026-07-02\afs-d2-accepted-generation-plan-hardening
```

Branch:

```text
codex/afs-d2-accepted-generation-plan-hardening-20260702
```

Base:

```text
origin/master=f00fbc6c1404a4c3b812056a0f142626edb75ea8
```

## Implementation Summary

- `POST /projects/{project_id}/accepted-generation-plan-packets/preview` now
  accepts optional `source_artifact_id` and `source_human_gate_id` for
  project-scoped plan evidence.
- Bundled fixture modes always return blocked workflow evidence. Even
  `confirmed_local_fixture` is labeled as `fixture_demo_non_acceptance` and
  cannot return `accepted=true`.
- Project artifact sources can return accepted only when the packet is not
  `repo_local_fixture` evidence and a manifest-linked human-gate decision targets
  the same `accepted_generation_plan_packet` artifact.
- Blocked previews are machine-visible as `job.status=blocked`,
  `preview_status=blocked`, and manifest status `blocked`; HTTP transport still
  returns 200 for a valid preview.
- Project manifests receive safe `accepted_generation_plan_refs` entries with
  preview artifact id, source artifact id, source human-gate id, workflow status,
  and explicit non-claim fields.
- Human gate target support now includes `accepted_generation_plan_packet`.
- Studio copy no longer says a fixture is accepted. The fixture control is
  labeled `Fixture demo (blocked)`, and the accepted title is reserved for
  project artifact step-gate evidence.

## Verification

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_accepted_generation_plan_packet.py tests\test_api_runtime_human_gate.py -q
# 9 passed, 1 warning

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_web_studio_accepted_generation_plan_static.py tests\test_web_studio_human_gate_static.py -q
# 5 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -c "from pathlib import Path; from apps.api.openapi_export import export_openapi_schema; export_openapi_schema(Path('docs/openapi/afs-runtime-service.openapi.json'))"
# regenerated committed OpenAPI snapshot

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_openapi_snapshot.py tests\test_api_runtime_accepted_generation_plan_packet.py tests\test_api_runtime_human_gate.py tests\test_web_studio_accepted_generation_plan_static.py tests\test_web_studio_human_gate_static.py -q
# 16 passed, 1 warning

npm run check:studio-js
# JS syntax check passed: 135 files

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_accepted_generation_plan_packet.py tests\test_api_runtime_human_gate.py tests\test_api_runtime_openapi_snapshot.py -q
# 11 passed, 1 warning

git diff --check
# passed
```

## Deltas

- product_delta: The plan-review workflow now exposes a real local step-gate
  route for project-scoped accepted plan packets.
- quality_delta: Fixture acceptance confusion is removed; blocked workflow state
  is visible to machines and operators.
- governance_delta: Human-gate evidence is required before accepted project plan
  state; manifest refs preserve recovery and evaluator traceability.
- integration_state: implementation ready for evaluator; not merged, pushed,
  provider-smoked, or human-accepted.

## Residual Risks

- Browser QA was not run in this lane; Studio coverage is static plus JS syntax.
- The project-scoped source artifact contract is minimal and should be reviewed
  by evaluator before wider integration.
- Full pytest was not run; focused Runtime, OpenAPI, and Studio checks passed.

## Non-Claims

No provider smoke, live provider call, external download, generated media,
generated-media QA, human creative acceptance, product readiness, business
validation, public/legal/patent readiness, deploy/runtime freshness,
CompanyOS/COS promotion, durable-memory promotion, or final integration claim.

## Closeout Packet

```text
close_state: implementation_ready_for_evaluator
upward_feedback_delivery: local_final_only
worker_local_subagents_used: no
next_owner: evaluator
next_action: evaluate D2 branch for accepted-plan evidence chain hardening
```
