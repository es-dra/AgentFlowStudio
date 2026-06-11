# AFS-PRODUCTION-MEMORY-ASSET-PROFILE-UPDATE-CANDIDATE-001

中文摘要：本文记录资产 profile 更新候选的工程切片。当前规则是 raw feedback、candidate evidence、background context 与 durable memory 必须区分；未经明确确认的候选不能强注入后续生成。本文只保留可追踪 contract 和测试参考，不代表当前 Studio 有记忆管理 UI。

执行标准：更新候选必须说明触发来源、关联节点、影响字段、冲突关系和拒绝条件。专业知识库、节点参数、角色身份和场景连续性优先级高于候选偏好。候选可以帮助下一轮创作智能体排序，但不能直接覆盖 confirmed asset，也不能写入长期记忆或公司知识库。

Status: implementation handoff.

## Scope

This slice adds the second post-test-package deterministic node:

```text
asset feedback event
  -> agentflow_production_memory_asset_profile_update_candidate
```

It turns tester feedback into structured candidate patch operations. It does
not apply the patch, create a profile version, create a promotion decision, or
unlock next-context eligibility.

## Product Surface

CLI command:

```text
production-memory-loop-draft-asset-profile-update-candidate
```

Runtime outputs:

```text
asset_profile_update_candidate.json
asset_profile_update_candidate.md
```

## Contract Boundaries

- `candidate_is_promoted_profile: false`
- `candidate_is_promoted_memory: false`
- `creates_promotion_decision: false`
- `applies_profile_version: false`
- `target_profile_next_context_unlocked: false`
- `writes_long_term_memory: false`
- `writes_company_kb: false`
- `provider_calls_started: false`

`cannot_judge` stays blocked with no patch operations. `kept + no_change`
records `no_update_recommended` with no patch operations. Negative feedback
without structured patch operations records `blocked_missing_patch_ops`.

## Patch Shape

Patch operations are structured:

```text
patch_ops:
  - op
  - path
  - value
  - rationale
  - evidence_refs
```

The first supported operation is `add_unique` for
`/negative_constraints/-` and `/evidence_refs/-`.

## Verification Results

Commands run before handoff:

```powershell
python -m pytest tests/test_production_memory_asset_profile_update_candidate.py -q
python -m pytest tests/test_production_memory_asset_profile_update_candidate.py tests/test_production_memory_asset_feedback_intake.py tests/test_production_memory_asset_profile_readiness.py -q
python -m pytest tests/test_contract_examples.py tests/test_cli_command_registry_boundaries.py -q
python -m apps.cli.main production-memory-loop-draft-asset-profile-update-candidate --help
python -m py_compile agentflow\memory\production_asset_profile_update_candidate.py apps\cli\production_memory_asset_profile_update_candidate_command.py apps\cli\command_registry.py
python -m apps.cli.main production-memory-loop-run-asset-test-package --asset-profile-seed examples/agentflow/production_memory_asset_profile_seed.example.json --output data/processed/runs/production_memory_loop/asset_update_candidate_smoke/package
python -m apps.cli.main production-memory-loop-record-asset-feedback --asset-profiles data/processed/runs/production_memory_loop/asset_update_candidate_smoke/package/asset_profiles.json --asset-profile-readiness data/processed/runs/production_memory_loop/asset_update_candidate_smoke/package/asset_profile_readiness.json --feedback-json examples/agentflow/production_memory_asset_feedback.example.json --output data/processed/runs/production_memory_loop/asset_update_candidate_smoke/feedback
python -m apps.cli.main production-memory-loop-draft-asset-profile-update-candidate --asset-feedback-event data/processed/runs/production_memory_loop/asset_update_candidate_smoke/feedback/asset_feedback_event.json --output data/processed/runs/production_memory_loop/asset_update_candidate_smoke/update_candidate
python -m pytest
git diff --check
```

Results:

- Focused update candidate tests: `10 passed`.
- Adjacent asset profile feedback/readiness suite: `27 passed`.
- Focused contract examples and CLI registry suite: `26 passed`.
- CLI help exposes `production-memory-loop-draft-asset-profile-update-candidate`.
- CLI no-provider smoke wrote ignored asset test package, asset feedback event,
  and asset profile update candidate outputs.
- Changed Python files compiled.
- Full suite on Python 3.13.5: `944 passed`.
- `git diff --check`: exit 0 with LF-to-CRLF warnings only.
- Diff-level sensitive-fragment scan had no added real private paths or
  secrets; remaining matches are rule constants or deliberate redaction-test
  literals.

## Next Work

The next deterministic node should be:

```text
Node 3 Asset Profile Promotion Decision + Profile Versioning
```

Web cockpit adaptation remains deferred until update candidates, explicit
profile promotion/versioning, and context projection are deterministic.
