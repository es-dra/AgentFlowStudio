# AFS Web Provider Smoke Readiness 001

Status: prepared, not executed.

Branch:

```text
codex/afs-landing-prep-web-plan-001
```

## Purpose

This handoff defines the next gate after the Chinese Web Workbench release
candidate: move from deterministic Runtime Service QA to an explicitly
authorized provider smoke.

It does not authorize or start a provider call. It only fixes the command
surface, evidence requirements, and claim boundaries so the next session can
run the smoke without mixing it with human acceptance, business validation, or
durable memory promotion.

## Current State

- Web release candidate exists at `/workbench/`.
- Stage 7 browser QA completed on `proj_stage7_rc_1781016167554`.
- Acceptance packet exists at
  `docs/frontend_integration/AFS_WEB_RELEASE_CANDIDATE_ACCEPTANCE_PACKET.zh-CN.md`.
- Visual demo index exists at
  `docs/frontend_integration/AFS_WEB_RC_DEMO_INDEX.zh-CN.html`.
- Draft PR handoff exists at `docs/handoff/AFS-WEB-RC-DRAFT-PR-001.md`.
- Provider remains closed by default.

## Required Order

1. Human accepts or rejects the Web RC experience using the acceptance packet.
2. If accepted, the user explicitly authorizes the exact provider capabilities.
3. Only then run the live provider smoke with ignored local inputs.
4. Record provider evidence separately from Web QA and human acceptance.

Do not infer provider authorization from Web QA, branch push, PR draft, or
previous deterministic test success.

## Readiness-Only Command

This command creates planning / blocked evidence and does not start provider
calls because it omits `--run-provider-validation`.

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main asset-provider-validation-gate `
  --request-validation `
  --asset-profile-seed examples/agentflow/production_memory_asset_profile_seed.example.json `
  --output data/processed/runs/web_rc_provider_gate_readiness
```

Expected console boundary:

```text
Provider calls: not started
Business validation: not claimed
Human acceptance: not claimed
Writes long-term memory: false
Writes Company KB: false
```

## Live Smoke Template

Use this only after explicit user authorization for image and video provider
capabilities, and only with local ignored config/materials.

```powershell
$env:AFS_ALLOW_REMOTE_IMAGE='true'
$env:AFS_ALLOW_REMOTE_VIDEO='true'

.\.venv\Scripts\python.exe -m apps.cli.main asset-provider-validation-gate `
  --request-validation `
  --run-provider-validation `
  --asset-profile-seed <ignored-or-example-seed.json> `
  --provider-config <ignored-provider-config.json> `
  --project-materials <ignored-project-materials.json> `
  --character-reference-image <ignored-reference-image> `
  --image-service minimax_image `
  --video-service kling_i2v `
  --output data/processed/runs/web_rc_provider_live_smoke
```

The command surface currently treats `minimax_image` as the verified image smoke
adapter id and `kling_i2v` as the video smoke service id. `gpt_image2` must not
be used for this smoke until an AFS adapter is wired and verified; the current
provider gate marks it as unavailable.

## Required Evidence

Collect these artifacts and keep generated runtime outputs out of git:

- console output showing whether provider calls started;
- `provider_validation_report.md`;
- `provider_safe_manifest.json`;
- safe status / blocker summary;
- maintenance audit output after the run;
- focused provider-gate tests if any provider adapter code changed;
- screenshots or Web observations only if the smoke result is surfaced in the
  Workbench.

## Claim Boundaries

Allowed claims after readiness-only command:

- provider gate command surface is available;
- provider calls were not started;
- blocked / planning evidence was written to an ignored runtime directory.

Allowed claims after live smoke, if authorized and successful:

- provider smoke runtime path executed;
- safe manifest and report were produced;
- Workbench can display the safe provider status if separately verified.

Forbidden claims:

- human acceptance;
- business validation;
- model quality approval;
- commercial readiness;
- durable memory promotion;
- Company OS active rule promotion.

## Storage Boundaries

Never commit:

- `.env` or `.dev.vars`;
- provider config with credentials;
- local project materials;
- local reference images;
- generated media bytes;
- provider raw responses;
- signed URLs;
- private absolute paths.

The AFS repo may keep only safe projection documents, tests, runbooks, manifests,
and redacted summaries.

## Close Condition

This readiness item is closed when:

- the handoff is committed;
- `TASK_TRACKER.md` points provider smoke to this handoff;
- `maintenance_audit` remains `failed=0` and `warning=0`;
- `git diff --check` passes.

Company OS feedback: not routed because this is a project-local provider gate
handoff, not a new reusable workflow lesson.
