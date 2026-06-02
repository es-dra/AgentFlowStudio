# AFS-PROVIDER-OPERATOR-STAGING-REVIEW-001 - Provider / Operator Staging Review

Status: reviewed as a separate staging candidate, not mainline product surface.

This review covers the hidden provider/operator slice after the provider config
bridge hardening. It does not stage, commit, approve live provider use, or
promote generated media.

No remote provider calls were made. Structure verification, mocked runtime
verification, provider smoke, human acceptance, business validation, and durable
Memory promotion remain separate.

## Scope

Reviewed paths:

- Hidden CLI: `apps/cli/kling_video_command.py`,
  `apps/cli/minimax_image_command.py`, `apps/cli/memory_demo_commands.py`,
  and the hidden registrations in `apps/cli/support_command_registry.py`.
- Provider config bridge: `agentflow_studio/model_gateway/company_secrets.py`.
- Kling runtime: `agentflow_studio/model_gateway/kling_*.py`.
- MiniMax runtime: `agentflow_studio/model_gateway/minimax_image_*.py` and
  `agentflow_production/posterflow/minimax_provider.py`.
- Operator runbook script:
  `tools/run_memory_advantage_recording_016.ps1`.
- Tests: provider smoke helpers, Kling/MiniMax tests, PosterFlow provider
  tests, and `tests/test_recording_016_script.py`.

## Review Result

| Area | Result | Notes |
|---|---|---|
| Default product surface | pass | `apps.cli.main --help` keeps `memory-video-pipeline-*` visible and hides direct provider/demo commands. |
| Provider config | pass | No machine-local Company `.secrets` default remains. Provider config is explicit through `--provider-config`, `-ProviderConfig`, or `AFS_PROVIDER_CONFIG`. |
| Capability gates | pass | Image and video use separate gates: `AFS_ALLOW_REMOTE_IMAGE` and `AFS_ALLOW_REMOTE_VIDEO`. |
| RECORDING-016 script | fixed in this pass | Live path now requires provider config before calling Kling I2V; dry-run still makes no provider call. |
| Secrets scan | pass | High-risk key/token/private-key patterns and the old local Company `.secrets` path did not match in reviewed paths. |
| File size | pass | Reviewed code, tests, script, and this doc stay under the 300-line target. |

## Staging Decision

The provider/operator slice may be staged only as a separate support slice after
final verification, not bundled into the mainline product surface.

Allowed in that slice:

- hidden provider CLI command modules and support registry hidden registrations;
- provider runtime adapters and mocked tests;
- provider config bridge hardening;
- RECORDING-016 script and runbook wording;
- no-call or mocked test helpers that use fake keys.

Not allowed in that slice:

- provider config JSON files;
- `.env`, `.dev.vars`, cookies, tokens, signed URLs, or real API keys;
- generated media, source keyframes, task outputs, or anything under
  `data/processed/`;
- claims that provider smoke is human acceptance, business validation, or
  durable Memory runtime proof.

## Residual Risk

- Live provider behavior was not verified in this pass; quota, API-region
  behavior, and provider terms remain outside this no-call review.
- `tools/run_memory_advantage_recording_016.ps1` still depends on an ignored
  local source keyframe path for the RECORDING-016 evidence workflow. That is
  acceptable for a preserved operator runbook, but it is not a portable product
  command.
- Direct provider commands should stay hidden until protocol-driven
  `memory-video-pipeline-*` live execution replaces them.

## Verification

Fresh checks for this pass:

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests/test_recording_016_script.py -q
# 2 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests/test_kling_video_request_plan.py tests/test_kling_video_smoke.py tests/test_kling_video_t2v_smoke.py tests/test_kling_video_curl_smoke.py tests/test_kling_video_task_recovery.py tests/test_minimax_image_smoke.py tests/test_posterflow_provider.py tests/test_recording_016_script.py -q
# 44 passed

.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests/test_agentflow_roadmap_docs.py -q
# 16 passed

[System.Management.Automation.Language.Parser]::ParseFile(...)
# PowerShell parse ok

.\.venv\Scripts\python.exe -B -m apps.cli.main --help
# hidden provider/demo commands absent from default help

rg sensitive-pattern scan over reviewed paths
# no matches

git diff --check
# no whitespace errors; CRLF normalization warnings only
```
