# AFS Kling Media Retention Rule

中文摘要：Kling 图生视频上线前必须先有本地媒体保留规则。视频文件体积远大于图片，live 验收一旦开始会快速放大 `runs/` 和 evidence 目录。当前规则是：canonical 报告永久保留；非 canonical evidence 超过 30 天可以清理；exact duplicate 只有在 sha、manifest 和场景归属都明确时才删除；本地 provider 配置、模型权重、唯一原始素材和唯一人工验收证据默认只报告不删除。

中文边界：本文只是维护规则，不是成本分析、业务验收或删除授权清单。本切片没有执行大规模媒体删除，首次持续 Kling live 前应单独运行清理并输出 cleanup manifest。

Purpose: prevent Kling I2V live validation from doubling local media bloat while
preserving canonical evidence.

## Rule

- Keep canonical report directories permanently.
- Non-canonical evidence directories older than 30 days may be cleaned.
- Exact duplicate media may be deleted only when SHA, manifest, and scenario
  ownership are all clear.
- Local provider config, model weights, original source media, and unique human
  acceptance evidence are report-only and must not be auto-deleted.

## Current Slice

This slice documents the rule but does not execute broad media deletion. Execute
the cleanup immediately before the first sustained live Kling validation run and
write a cleanup manifest with path, size, reason, and rule id.

## Claim Boundary

This is a local maintenance rule. It is not business validation, provider cost
verification, or human acceptance evidence.
