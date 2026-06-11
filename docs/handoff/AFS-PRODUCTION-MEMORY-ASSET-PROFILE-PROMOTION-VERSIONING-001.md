# AFS-PRODUCTION-MEMORY-ASSET-PROFILE-PROMOTION-VERSIONING-001

中文摘要：本文保留资产 profile 晋升与版本记录的后端证据，但当前 MVP 不做用户可见的记忆审核和长期记忆自动晋升。任何 profile promotion 都只能作为受控、安全、可追踪的工程证据，不能等同于人工验收或公司知识库 active rule。后续若当前 Runtime contract 已覆盖其用途，应删除而不是归档。

执行标准：profile 版本只能记录安全摘要、决策依据和关联 artifact，不能保存素材字节、provider raw、secret 或本地绝对路径。晋升必须有人类决策或明确规则支持；测试通过、provider smoke 成功或模型输出好看，都不能自动构成长期记忆。当前阶段只把这些内容作为后端证据链参考。

Status: implementation handoff for Node 3 of the non-Web Production Memory
asset loop.

## Scope

This slice reviews one
`agentflow_production_memory_asset_profile_update_candidate` and records an
explicit local project profile decision:

```text
asset profile update candidate
  -> asset profile promotion decision
  -> optional asset profile version
```

It does not add Web adaptation, provider execution, Company KB writes, durable
memory writes, human acceptance, or business validation.

## Added Artifacts

- `agentflow_production_memory_asset_profile_promotion_decision`
- `agentflow_production_memory_asset_profile_version`

## Added CLI

```powershell
python -m apps.cli.main production-memory-loop-review-asset-profile-update-candidate --help
```

Inputs:

- `--asset-profiles`
- `--asset-profile-update-candidate`
- `--decision promoted|merged|rejected|expired|blocked`
- `--rationale`
- `--reviewer-role`
- `--decided-at`
- `--output`

Outputs:

- `asset_profile_promotion_decision.json`
- `asset_profile_promotion_decision.md`
- `asset_profile_version.json` and `.md` only when the decision applies a
  version.

## Contract Rules

- Source update candidate must be `candidate_only` before `promoted` or
  `merged` can apply a version.
- `rejected`, `expired`, or `blocked` decisions record review state but do not
  create a version.
- Supported patch operation is whitelisted `add_unique`.
- Unsupported patch operation or path fails before versioning.
- The source profile and update candidate are not mutated.
- Generated profile versions keep:
  - `writes_long_term_memory: false`
  - `writes_company_kb: false`
  - `profile_status: promoted`
  - `supersedes_profile_id`
  - `version_change_summary`
  - source evidence refs
  - explicit local profile decision refs
- This is local project profile versioning only; it is not durable Memory OS
  storage and not Company KB promotion.

## Verification

Verification run for this branch:

```powershell
python -m pytest tests/test_production_memory_asset_profile_promotion_versioning.py -q
python -m pytest tests/test_production_memory_asset_profile_promotion_versioning.py tests/test_production_memory_asset_profile_update_candidate.py tests/test_production_memory_asset_feedback_intake.py tests/test_production_memory_asset_profile_readiness.py -q
python -m pytest tests/test_contract_examples.py tests/test_cli_command_registry_boundaries.py -q
python -m apps.cli.main production-memory-loop-review-asset-profile-update-candidate --help
python -m py_compile agentflow\memory\production_asset_profile_promotion.py agentflow\memory\production_asset_profile_promotion_contract.py agentflow\memory\production_asset_profile_promotion_render.py agentflow\memory\production_asset_profile_promotion_utils.py apps\cli\production_memory_asset_profile_promotion_command.py apps\cli\command_registry.py
python -m pytest
git diff --check
```

Results:

- Focused profile promotion/versioning tests: `11 passed`.
- Adjacent asset promotion/update/feedback/readiness suite: `38 passed`.
- Focused contract examples and CLI registry suite: `26 passed`.
- CLI help shows `--decision` as required.
- CLI no-provider smoke wrote ignored promotion decision and profile version
  artifacts.
- Changed Python files compiled.
- Full suite on Python 3.13.5: `955 passed`.
- `git diff --check`: exit 0 with LF-to-CRLF warnings only.
- Security audit: `PASS`; no blocking secret/private-path/media leak found in
  this slice.
- Spec review: prior blockers fixed; stale version outputs are removed when a
  later non-version decision writes to the same output directory.

## Next Node

Next deterministic node:

```text
Node 4 Asset Profile Context Projection
```

Node 4 should consume `agentflow_production_memory_asset_profile_version` as
the authority for context inclusion. Do not include a profile only because the
promotion decision says `eligible_by_explicit_profile_version`; also check the
version `profile_version_applied`, `usable_for_next_context`, embedded profile
`context_eligibility`, blockers, superseded IDs, and missing refs.

Web cockpit remains deferred until profile feedback, update candidate,
promotion/versioning, and context projection are deterministic.
