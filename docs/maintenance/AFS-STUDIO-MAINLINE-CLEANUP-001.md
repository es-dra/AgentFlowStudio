# AFS-STUDIO-MAINLINE-CLEANUP-001

日期：2026-06-12

## 决策

Studio 是当前唯一 MVP 产品主线：

```text
/studio/ canvas -> Runtime Service -> fixed assets/context resolver -> provider-gated evidence
```

短视频分发链仍保留在仓库中作为 legacy/optional 代码，但不再是当前 MVP 口径。

## Runtime v02

legacy Runtime v02 的 list/import/source-assets/content-cards/canvas-draft 等路由默认隐藏。只有显式设置：

```powershell
AFS_ENABLE_LEGACY_RUNTIME_V02=true
```

才会注册旧路由。这样旧测试和兼容路径仍可运行，但默认 OpenAPI 不再暴露旧产品面。

## agentflow/memory

`agentflow/memory` 在 Studio/Runtime 工作中标记为 read-only legacy。本轮不删除它，因为 CLI 和 legacy Runtime harness 仍有大量引用。

新增静态测试要求新的 Studio/Runtime 模块不得 import `agentflow.memory`；当前只允许已有的 `apps/api/runtime_service.py` 与 `apps/api/runtime_events.py`。

## SOP 审计

本轮使用以下命令做 tracked 文件审计：

```powershell
git ls-files agentflow_studio/assembly_sop agentflow_studio/bgm_sop agentflow_studio/cover_sop agentflow_studio/package_sop agentflow_studio/subtitle_sop agentflow_studio/subtitle_burn_sop agentflow_studio/compliance agentflow_studio/*_sop
```

结果：

- 被点名的 `*_sop` 目录没有 tracked 文件。
- 唯一 tracked 清理目标是 `agentflow_studio/compliance/__init__.py`，内容只有一行说明，且没有 tracked 引用。

动作：

- 删除 `agentflow_studio/compliance/__init__.py`。
- ignored `__pycache__` 和本地空目录不作为产品代码删除成果。

## 非目标

- 不广泛删除 `agentflow/memory`。
- 不在本轮拆库或迁移分发链。
- 不改变 provider gate 规则。
