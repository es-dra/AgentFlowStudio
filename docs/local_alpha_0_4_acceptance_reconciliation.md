# Local Alpha 0.4 Acceptance Reconciliation

Date: 2026-05-27

Status: reconciled for machine-verified local evidence; not human-accepted and
not business-validated.

## Purpose

This document reconciles the Local Alpha 0.4 runtime, Web operator, and
memory-quality evidence into one acceptance ledger.

It answers one narrow question:

```text
What can AgentFlow Studio currently claim from the Local Alpha 0.4 loop, and
what must remain blocked, pending, or explicitly outside the claim?
```

The answer is split by evidence level. Structure verification, runtime
verification, human acceptance, business validation, provider smoke, and
durable Memory runtime are separate states.

## Overall Status

| Area | Status | Claim boundary |
|---|---|---|
| Scenario package | pass | Runbook, ignored local input policy, and evidence map exist. |
| Runtime verification | pass on this workstation | Real 0.4 workflow produced reviewable ignored package evidence. |
| Web operator path | pass as local operator path | Web defaults and readiness state point to 0.4 evidence without persistence or provider calls. |
| Memory evidence reuse | pass as structural review | Evidence chain is validated without durable memory writes or second-pass execution. |
| Provider smoke | blocked as expected | Image-provider env is unset; no live provider call was made. |
| Human acceptance | not reviewed | No human has accepted the final creative package as product-satisfactory. |
| Business validation | not performed | No customer, market, distribution, or revenue signal is claimed. |
| Durable Memory runtime | not implemented | Candidate and promotion artifacts are evidence only, not long-term memory. |
| Real second-pass run | not executed | Context reuse has a structural contract, not a generated second-pass output. |

## Evidence Inputs

| Lane | Evidence | Status |
|---|---|---|
| `AFS-PROD-LOOP-001` | `docs/local_alpha_0_4_scenario_package.md` | pass |
| `AFS-RUN-PACKAGE-001` | `docs/handoff/AFS-RUN-PACKAGE-001.md` | pass as runtime verification |
| `AFS-WEB-OPERATOR-002` | `docs/handoff/AFS-WEB-OPERATOR-002.md` | pass with follow-up readiness fix |
| `AFS-MEMORY-QUALITY-002` | `docs/handoff/AFS-MEMORY-QUALITY-002.md` | pass as structural traceability review |
| `AFS-POSTER-LIVE-002` | `alpha-smoke --json` provider state | blocked by missing image-provider env |

The real runtime artifacts are under ignored local paths:

```text
data/processed/runs/local_alpha_0_4_product_loop
```

They remain evidence on this workstation. They are not committed deliverables.

## Pass Items

### Structure Verification

- The 0.4 scenario package names the selected workflow, local inputs, output
  directory, expected artifacts, blocked-state rules, and non-claims.
- The Web operator profile defaults to
  `workflows/video_script_to_finished_package_local_asr.yaml`,
  `data/processed/local_alpha_0_4/video_script_local_asr_input.json`, and
  `data/processed/runs/local_alpha_0_4_product_loop`.
- The memory reuse review contract verifies this chain:

```text
runtime evidence
-> feedback source
-> memory candidate
-> promotion decision
-> context bundle
-> second-pass prompt
```

- Rejected or expired promotion decisions cannot pass context reuse review.
- The committed memory reuse example uses logical refs only and declares no
  durable long-term memory write.

### Runtime Verification

Observed 0.4 run evidence on this workstation:

- workflow terminal status: `success`;
- `inspect-run`: `8 passed / 0 failed / 0 warnings`;
- `review-run`: `42 passed / 0 failed / 0 warnings`;
- `package-report`: wrote `package_report.md`;
- package report records package status `succeeded`, review status `passed`,
  quality status `pass`, and final duration `18.59s`;
- final BGM video is `final_video_with_bgm.mp4` under the ignored run
  directory.

This proves the local workflow can produce reviewable package evidence on this
workstation. It does not prove creative fit.

### Web Operator Verification

- Production Mode names the Local Alpha 0.4 operator loop.
- The bridge and static UI show the 0.4 runbook, preferred workflow, input, and
  output defaults.
- A stale-readiness blocker was fixed so passed bridge input-check evidence can
  override static setup reminders after plan evidence exists.
- Browser smoke used a local static server and local bridge only.

### Artifact And Secret Boundary

- Local media, BGM, ASR model cache, input bundle, and generated run artifacts
  stay under ignored paths.
- No `.env`, `.dev.vars`, `configs/models.yaml`, provider key, signed URL,
  cookie, token, local media file, or generated video is committed.
- No private Company knowledge is copied into the repository.

## Blocked Or Pending Items

| Item | State | Next condition |
|---|---|---|
| `AFS-POSTER-LIVE-002` | blocked | Open only if local image-provider env is intentionally configured and `AFS_ALLOW_REMOTE_IMAGE=true`. |
| Human product acceptance | pending | A human reviews the final package and records accept/reject feedback. |
| Business validation | pending / out of 0.4 scope | Real user, market, distribution, or revenue evidence exists. |
| Real second-pass run | pending | A follow-up lane executes a second pass from the context bundle and compares outputs. |
| Durable Memory runtime | not implemented | A separate Memory runtime design and approval exists; current artifacts must not write long-term memory. |
| Web memory summary | pending | A read-only UI lane displays memory reuse review status without promotion or persistence. |
| Memory review CLI | pending | A read-only CLI exposes the reuse validator without writes or provider calls. |

## Non-Claims

Local Alpha 0.4 does not claim:

- hosted SaaS readiness;
- customer, market, revenue, or distribution validation;
- mature creative or editorial quality;
- durable Memory runtime;
- vector store, database, RAG, prefix-cache, or hosted memory quality;
- autonomous Router or skill runtime;
- provider cost-quality optimization;
- successful live image-provider smoke;
- actual second-pass product improvement.

Provider smoke is also not creative-quality validation. A future live image
smoke can only prove provider connectivity and safety gates.

## Acceptance Decision

Local Alpha 0.4 is accepted only as a machine-verified local evidence package:

```text
scenario package: pass
runtime verification: pass on this workstation
Web operator path: pass
memory reuse structural review: pass
provider smoke: blocked as expected
human acceptance: not reviewed
business validation: not performed
durable Memory runtime: not implemented
real second-pass run: not executed
```

This is enough to close the first Local Alpha 0.4 evidence reconciliation lane.
It is not enough to mark the product output, Memory quality, or business loop
as validated.

## Next Queue

Recommended next lanes:

| ID | Scope | Acceptance focus |
|---|---|---|
| `AFS-MEMORY-REVIEW-CLI-001` | Read-only CLI/review command for evidence reuse validation | Broken refs fail; rejected decisions fail; no durable writes; no provider calls; no runtime artifacts. |
| `AFS-WEB-EVIDENCE-SUMMARY-001` | Web displays memory reuse review status summary | UI distinguishes passed, failed, and not reviewed; no promotion, persistence, upload, or directory scan. |
| `AFS-SECOND-PASS-001` | Real second-pass run from accepted context evidence | Compare before/after outputs without claiming product improvement until a human reviews it. |
| `AFS-ACCEPTANCE-FEEDBACK-001` | Human accept/reject capture for the 0.4 package | Human acceptance is recorded separately from machine review and business validation. |
| `AFS-POSTER-LIVE-002` | Optional live image smoke | Remains blocked unless the image-provider gate and local env are intentionally enabled. |

## Refresh Commands

Use focused verification for this acceptance surface:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_agentflow_roadmap_docs.py tests/test_agentflow_asset_memory_validator.py::test_evidence_reuse_review_accepts_local_alpha_0_4_chain_example tests/test_web_production_mode_static.py::test_web_readiness_uses_input_check_after_plan_passes tests/test_video_to_finished_package_local_asr_workflow.py tests/test_alpha_smoke_cli.py
.\.venv\Scripts\python.exe -m apps.cli.main alpha-smoke --json
git diff --check
git status --short --ignored data/models/faster-whisper data/processed data/raw/demo_real_video data/raw/demo_bgm
```
