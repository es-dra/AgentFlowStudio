# AFS Web 重建纵切实施计划

目标：把当前 Workbench 从横向 demo 面收敛为高质量创作工作台，并落地第一条“剧本到分镜”纵切。

架构：Runtime Service 是唯一后端边界。前端增加一个很小的 client/action/render 切片调用 `/provider/script-draft-plan`，再把返回的 safe artifact 显示到画布和 artifact 面板。暂不服务纵切的 LibTV 横向 demo 入口只保留安全占位或弱化展示。

技术栈：Python FastAPI Runtime Service，`apps/workbench/src` 静态 JS 模块，`apps/workbench` CSS 模块，pytest，本地浏览器 QA。

## 1. 文档和清理边界

文件：

- 新增 `docs/maintenance/AFS-WEB-REFOUNDATION-CLEANUP-001.zh-CN.md`
- 新增 `docs/superpowers/specs/2026-06-11-afs-web-refoundation-design.md`
- 新增 `docs/superpowers/plans/2026-06-11-afs-web-refoundation-vertical.md`

任务：

- [x] 改 UI 前先写维护账本。
- [x] 记录保留、收束、隐藏和不做的边界。
- [x] 记录 provider gate 与验证命令。

## 2. 测试先行

文件：

- 修改 `tests/test_web_workbench_foundation.py`

任务：

- [x] 断言 Workbench source 包含 `/provider/script-draft-plan`。
- [x] 断言 `providerScriptDraftPlan` 存在。
- [x] 断言 `run-script-draft-plan` 存在。
- [x] 断言脚本 UI 包含目标输入、时长、风格、反馈和 safe artifact 标签。
- [x] 先运行 focused test，确认实现前失败。

红灯命令：

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests\test_web_workbench_foundation.py::test_workbench_shell_targets_runtime_service_contract tests\test_web_workbench_foundation.py::test_workbench_keeps_frontend_safety_boundary -q
```

结果：实现前失败，缺少脚本纵切前端标记。

## 3. Runtime Client 和 Action

文件：

- 修改 `apps/workbench/src/runtime-client.js`
- 修改 `apps/workbench/src/app-actions.js`
- 修改 `apps/workbench/src/state.js`

任务：

- [x] 增加 `providerScriptDraftPlan(payload)`。
- [x] 增加脚本草案表单状态：目标、时长、风格、反馈 artifact、上一版 artifact。
- [x] 增加 `runScriptDraftPlan()`。
- [x] 成功后选择 `script_storyboard_safe_artifact` 并刷新 Workbench。
- [x] 修正 Runtime-hosted Workbench 在随机端口下的同源请求问题。

## 4. 画布 UI 重建

文件：

- 修改 `apps/workbench/src/render-studio-starter-flows.js`
- 修改 `apps/workbench/styles-studio-starters.css`
- 新增 `apps/workbench/styles-studio-script-vertical.css`

任务：

- [x] 把静态脚本卡替换为可输入的生产 brief 面板。
- [x] 增加目标时长和风格控件。
- [x] 增加主动作 `run-script-draft-plan`。
- [x] 增加分镜 artifact、gate 状态和反馈区域。
- [x] 图片、视频、音频入口继续可见，但明确是后续 provider gate。
- [x] 重跑 focused UI tests。

## 5. 验证和记录

文件：

- 修改 `TASK_TRACKER.md`
- 修改 `DEVLOG.md`
- 新增 `docs/handoff/AFS-WEB-REFOUNDATION-VERTICAL-001.md`

任务：

- [x] 运行 focused Web/API tests。
- [x] 运行浏览器 QA，覆盖 desktop 和 mobile。
- [x] 运行 `maintenance_audit` 并清零本轮引入的 warning。
- [x] 运行 `git diff --check`。
- [x] 按最终结果更新 handoff。
