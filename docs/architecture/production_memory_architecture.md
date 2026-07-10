# Production Memory 遗留契约索引

Production Memory 是已退役的 legacy contract island。它不是当前 Studio MVP
路径，不暴露为可见或隐藏 CLI 产品面，也不是新任务启动上下文。

本文件只保留一个狭窄职责：给仍在 static contract registry 中登记的
Production Memory 示例提供 `doc_path` 锚点。剩余库代码、示例和 legacy 测试
需要在后续独立瘦身 lane 中整体退休。

## 遗留代码面

```text
agentflow/memory/
examples/agentflow/production_memory_loop.example.json
examples/agentflow/*asset*.example.json
```

旧 `apps/cli/production_memory_*` 命令面已经退休。历史 local runbook 和
per-asset-profile 文档已从当前树删除。

## 边界

- candidate memory 不是 durable memory。
- feedback 是 evidence，不是 memory。
- asset reuse 必须有显式 promotion decision。
- context reuse 不得写入 long-term memory。
- 这些 contract 不授权 provider call。
- runtime verification、provider smoke、human acceptance、business validation
  和 CompanyOS/COS active-rule promotion 都是独立证据层。

## 后续退休 lane

后续可以在替换或删除 static contract audit 中仍指向本文件的 registry 条目后，
删除 `agentflow/memory`、相关 legacy tests 和 Production Memory examples。
