# GFR / AOS Execution Projection

This document explains how Company OS / AOS v1 projects into AgentFlow Studio.
It is not the source rule set. Source rules remain in `10-Startup`.

## Source Control Entry

For substantial AFS work, use the smallest source entry first:

```text
D:\Learning materials\Learning_notes\10-Startup\00-Company-OS\AI-Native-Company-OS-MAP.md
D:\Learning materials\Learning_notes\10-Startup\00-Company-OS\AGENTIC-OPERATING-SYSTEM-V1.md
D:\Learning materials\Learning_notes\10-Startup\00-Company-OS\GFR-Global-Rule-Compiler.md
D:\Learning materials\Learning_notes\10-Startup\70-Projects\AgentFlow-Studio\PROJECT-CAPSULE.md
D:\Projects\AgentFlowStudio\docs\AOS_CURRENT_STATE.md
```

Load additional packs only when the task requires them:

```text
D:\Learning materials\Learning_notes\10-Startup\00-Company-OS\default-context-packs.md
D:\Learning materials\Learning_notes\10-Startup\00-Company-OS\context-pack-index.json
D:\Learning materials\Learning_notes\10-Startup\00-Company-OS\COS-REGISTRY-V0.json
D:\Learning materials\Learning_notes\10-Startup\00-Company-OS\EVIDENCE-LEDGER-V0.json
```

## AOS Runtime Objects

Substantial work should compile or internally apply:

```text
AOS Startup Packet
  -> Goal Contract
  -> Task Packet
  -> Evidence target
  -> Runtime Surface Vector when state can drift
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

For larger work, scale through bounded temporary lanes under one main control
thread:

```text
main control
  -> worker lane contract
  -> evaluator lane contract
  -> integration queue
  -> closeout with separated evidence states
```

Each lane needs a target, scope, evidence target, verification route, stop
condition, and return route. Do not restore permanent role threads or
status-only heartbeat loops.

## Repository Boundary

AFS can store:

- code, tests, schemas, contracts, and runbooks;
- safe manifests and safe summaries;
- current execution state and verification commands;
- public or semi-public engineering notes.

AFS must not store:

- secrets, tokens, cookies, provider keys, or signed URLs;
- provider raw responses, generated media bytes, or private local asset bytes;
- private strategy, real customer data, real costs, contract originals, or
  unpublished partner judgment;
- Company OS candidate rules promoted to active status without human review.

## Evidence Levels

Closeouts must separate these states:

| State | Meaning |
|---|---|
| Structure verification | Files, schemas, static checks, or fixtures have the expected shape. |
| Runtime verification | Runtime Service or Studio ran the target path. |
| Provider smoke | An explicitly gated remote provider path ran. |
| Human acceptance | The creator or target user accepted the result. |
| Business validation | Market, customer, ROI, paid, or distribution evidence supports the claim. |
| Durable memory promotion | Candidate evidence was reviewed and promoted by the human-governed process. |

Provider smoke is not human acceptance. Runtime verification is not business
validation. Candidate memory is not durable memory.

## Runtime Projection Endpoint

`GET /company-os/gfr-projection` may expose only a safe projection for Studio
and Runtime use:

```text
gfr_packet_fields
context_packs
provider_gates
evidence_states
feedback_routes
runtime_recording
non_claim_boundary
```

It must not read raw `10-Startup` source files or expose local absolute paths,
provider secrets, customer material, real costs, contract originals, generated
media bytes, or provider raw responses.

## Failure Signals

Treat these as AOS/GFR startup failures:

- a new task starts from old drafts, old handoffs, or a full historical ledger;
- the goal, read/write scope, gates, verification route, or feedback route are
  unclear before editing;
- provider success is described as human acceptance or business validation;
- repo experience is written directly as an active Company OS rule;
- private strategy, contracts, customer data, costs, or provider raw content are
  written into the repository.

## Verification

For COS/GFR/AOS route changes or AFS projection changes:

```powershell
python "D:\Learning materials\Learning_notes\10-Startup\80-Workflow\ai-native-company-workflow\tools\gfr_audit.py" --root "D:\Learning materials\Learning_notes\10-Startup" --pack-index "D:\Learning materials\Learning_notes\10-Startup\00-Company-OS\context-pack-index.json"
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe "D:\Learning materials\Learning_notes\10-Startup\80-Workflow\ai-native-company-workflow\contracts\scripts\validate_ai_native_contracts.py"
git -C "D:\Projects\AgentFlowStudio" diff --check
```

If code changes are included, also run the focused pytest, Studio JS, Runtime,
or maintenance commands required by `AGENTS.md`.
