# AFS 导演台 V2 合同交接

日期：2026-06-23 by Codex
分支：`codex/director-stage-v2-contract-20260623`
Worktree：`C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\director-stage-v2-contract-20260623`

## 范围

- 新增一层低冲突的 Runtime 侧导演台 V2 合同和确定性编译器基础。
- 没有修改 Studio 前端、分镜、关键帧、资产弹窗或 context resolver 主链路。
- Provider gate 保持不变，没有调用远程 LLM、图片或视频 provider。

## 变更文件

- `apps/api/runtime_director_compiler_v2.py`
- `tests/test_runtime_director_compiler_v2.py`
- `docs/handoff/AFS-DIRECTOR-STAGE-V2-CONTRACT-20260623.md`

## 合同边界

- 新合同入口是 `apps/api/runtime_director_compiler_v2.py` 中的 `DirectorSceneBlockingV1`。
- 编译入口是 `compile_director_scene_blocking`。
- V2 编译器消费 `camera`、`subjects`、`props`、`lights`、`stage`、`exports`。
- `safe_exports` 只暴露 `screenshot_artifact_id` 和 `thumbnail_artifact_id`，不暴露本地素材字节或 provider 原始响应。
- `visual_asset_signatures` 中的后端资产签名优先于前端传入的 subject signature，避免前端伪造资产语义。
- 如果缺少 V2 blocking 且传入 `fallback_setup`，编译器会委托现有 `compile_director_setup`，并标记 `trace_summary.fallback_source = director_setup_2d`。

## TDD 证据

- Red 1：V2 模块不存在时，`tests/test_runtime_director_compiler_v2.py` 以 `ModuleNotFoundError` 失败。
- Green 1：加入最小合同和编译器骨架后，空 blocking 测试通过。
- Red 2：语义测试因 camera、subjects、props、后端资产签名未编译而失败。
- Green 2：加入确定性编译逻辑后，V2 语义测试通过。
- Red 3：fallback 测试因缺少 `fallback_setup` 参数支持而失败。
- Green 3：委托 V1 编译器后，fallback 测试通过。

## 验证

- 修改前基线：`pytest tests\test_runtime_director_compiler.py -q` -> 5 passed。
- V2 聚焦：`pytest tests\test_runtime_director_compiler_v2.py -q` -> 5 passed。
- V1 + V2 聚焦：`pytest tests\test_runtime_director_compiler.py tests\test_runtime_director_compiler_v2.py -q` -> 10 passed。
- CLI help：`python -m apps.cli.main --help` -> passed。
- CLI version：`python -m apps.cli.main version` -> `0.1.0`。
- 完整 pytest：`python -m pytest` -> 607 passed / 520 deselected / 2 existing warnings。
- 空白差异检查：`git diff --check` -> passed。

## 尚未完成

- V2 还没有接入 Runtime request models、Studio save/load state、OpenAPI、关键帧上下文或 provider 流程。
- 本轮没有实现 Three.js 舞台、截图 artifact 写入器或浏览器视觉验证。
- 本轮不声明 human acceptance、provider smoke 或 business validation。
