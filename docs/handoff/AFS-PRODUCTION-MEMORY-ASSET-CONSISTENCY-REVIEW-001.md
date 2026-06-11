# AFS-PRODUCTION-MEMORY-ASSET-CONSISTENCY-REVIEW-001

中文摘要：本文作为资产一致性后端链路的历史证据保留，当前用途是帮助理解安全 artifact、候选证据和一致性检查如何进入 Runtime 流程。它不代表当前 Studio UI 入口，也不声明人工验收、商业验证或 durable memory。若后续资产一致性逻辑被新 Runtime 测试和当前文档完全覆盖，本文件应直接删除。

保留理由：资产一致性仍可能影响人物、场景和关键帧连续性，所以本文暂时作为工程证据存在。后续维护时，只引用其中仍能支撑当前测试、接口和安全边界的部分；不要恢复旧 UI，不要把候选反馈当强记忆。真实 provider 接入前，所有一致性结论都必须通过新的 keyframe 流程重新验证。

Status: implementation handoff for Node 5 of the non-Web Production Memory
asset loop.

## Scope

This slice records explicit cross-scene or cross-shot consistency observations
against projected profile context:

```text
asset profile context projection
  + sanitized consistency review fixture
  -> asset consistency review
```

It does not add Web adaptation, provider execution, free-form Markdown parsing,
Company KB writes, durable memory writes, automatic feedback events, automatic
profile updates, promotion decisions, human acceptance, or business
validation.

## Added Artifacts

- `agentflow_production_memory_asset_consistency_review_fixture`
- `agentflow_production_memory_asset_consistency_review`

## Added CLI

```powershell
python -m apps.cli.main production-memory-loop-review-asset-consistency --help
```

Inputs:

- `--asset-profile-context-projection`
- `--consistency-review-json`
- `--reviewed-at`
- `--output`

Outputs:

- `asset_consistency_review.json`
- `asset_consistency_review.md`

## Contract Rules

- Only profile refs from `asset_profile_context_projection.included_refs` can
  produce consistency findings.
- Unknown or blocked profile refs become `blocked_findings`.
- `cannot_judge` is neutral.
- Review dimensions, results, failure attributions, and suggested next states
  reuse the first asset-feedback taxonomy.
- The review fixture may be `json_fixture` or `markdown_derived_fixture`, but
  this node does not parse free-form Markdown.
- This review is evidence only:
  - `creates_asset_feedback_event: false`
  - `creates_profile_update_candidate: false`
  - `creates_promotion_decision: false`
  - `writes_long_term_memory: false`
  - `writes_company_kb: false`

## Verification

Verification to run for this branch:

```powershell
python -m pytest tests/test_production_memory_asset_consistency_review.py -q
python -m pytest tests/test_production_memory_asset_consistency_review.py tests/test_production_memory_asset_profile_context_projection.py tests/test_production_memory_asset_profile_promotion_versioning.py tests/test_production_memory_asset_profile_update_candidate.py tests/test_production_memory_asset_feedback_intake.py tests/test_production_memory_asset_profile_readiness.py -q
python -m pytest tests/test_contract_examples.py tests/test_cli_command_registry_boundaries.py -q
python -m apps.cli.main --help
python -m apps.cli.main production-memory-loop-review-asset-consistency --help
python -m py_compile agentflow\memory\production_asset_consistency_review.py agentflow\memory\production_asset_consistency_review_render.py apps\cli\production_memory_asset_consistency_review_command.py apps\cli\command_registry.py
python -m pytest
git diff --check
```

## Next Node

Next deterministic node:

```text
Node 6 Web Read-Only Asset Cockpit
```

The Web cockpit should remain read-only. It can render profile readiness,
feedback intake, update candidates, promotion/versioning, context projection,
and consistency review artifacts, but it must not scan directories, persist
browser state, execute providers, or create Loulan-specific inspectors.
