# AFS Web Workbench 发布候选验收包

日期：2026-06-10
分支：`codex/afs-landing-prep-web-plan-001`
当前 head：以 `git log -1 --oneline` 为准；本验收包跟随分支更新，不固定单个提交。
验收对象：Runtime Service 托管的 `/workbench/` 中文创作工作台 release candidate

## 定位

本验收包用于判断当前 Web Workbench 是否已经达到“接入真实 provider 前，可以先由人完整试用并确认体验方向”的状态。

它不是 provider smoke、不是 business validation、不是 durable memory promotion，也不是最终商业化界面验收。

## 前置条件

- Runtime Service 已在本机运行，当前浏览器地址为 `http://127.0.0.1:8790/workbench/`。
- provider 默认关闭；不要在本轮验收中配置或提交 provider secret。
- 只使用 safe summary、safe manifest、safe artifact ref，不导入本地私有媒体字节。
- 验收重点是产品路径和交互体验，不是模型质量。

## 必须验收的主路径

1. 打开 `/workbench/`，确认首屏是中文工作台，而不是工程调试面板。
2. 连接 Runtime Service，能看到项目入口和工作区导航。
3. 从项目列表打开一个项目，优先使用列表里的“验收演练项目”或当前 QA 项目 `proj_stage7_rc_1781016167554`。
4. 检查项目列表：主标题应是项目目标、项目类型或中文归一标题，不应把 raw `project_id`、乱码标题或内部 Stage 7 命名作为主标题。
5. 进入素材库，确认素材/参考只展示摘要，不展示本地绝对路径或媒体字节。
6. 生成或加载画布草稿，确认画布节点、节点状态、右侧检查器和底部操作区能联动。
7. 切换到分镜台，确认镜头序列、当前镜头、安全预览、引用/阻塞事实和审片入口可理解。
8. 切换到审片室，执行一次保留 / 修改 / 拒绝类审片决定。
9. 执行首轮素材检查，记录反馈，再执行下一轮验证。
10. 切换到项目记忆，确认它展示的是“候选复用状态”和“下一轮约束”，没有声称已进入 durable memory。
11. 切换到任务中心，确认任务、阻塞原因和 Provider 预检是独立工作区，不再压在创作主界面上。
12. 打开设置/诊断，确认内部 id、action、job、artifact ref 只在诊断层出现。
13. 在 1366x768、1440x900 和移动宽度下快速查看页面，确认没有严重错位、按钮不可见或文本溢出。

## 通过标准

- 用户能用“项目 -> 素材 -> 画布 -> 分镜 -> 审片 -> 记忆 -> 任务”的心智完成一轮操作。
- 主界面默认语言是中文，不需要理解 `project_id`、`job_id`、`artifact_id` 或 action 枚举才能继续。
- 首屏项目列表不把历史演练 id、乱码标题、英文 demo 文案或内部 Stage 7 命名暴露为用户主标题。
- 诊断信息存在，但不压过创作工作流。
- Provider Gate 明确显示阻塞和预检状态，没有暗示已经调用真实模型。
- 所有关键动作都有可见的成功、失败、阻塞或禁用反馈。
- 主路径体验接近常规画布/影视创作工具的低学习成本，而不是要求用户理解 AFS 内部工程对象。

## 不通过时的记录格式

每个问题按下面格式记录，便于下一轮直接修复：

```text
位置：
操作：
预期：
实际：
严重度：blocker / major / minor
截图：
是否涉及安全边界：是 / 否
```

## 当前工程证据

- Stage 7 QA 项目：`proj_stage7_rc_1781016167554`。
- 可视化演示索引：`docs/frontend_integration/AFS_WEB_RC_DEMO_INDEX.zh-CN.html`。
- 浏览器 QA：console error `0`，主视图可见英文 `false`，主视图内部 id 泄漏 `false`，文字溢出 `0`。
- 人工验收前演练：刷新 `/workbench/` 后自动连接 Runtime Service，8 个工作区均可切换；console error `0`，列出的英文残留/内部 id/本地路径残留 `0`，文字溢出 `0`。
- 2026-06-10 浏览器主路径复核：`tools/workbench_vertical_flow_browser_smoke.py` 已适配中文多工作区外壳，最新项目 `proj_browser_vertical_1781030891` 达到 `ready_for_next_round`，Provider 调用仍未启动。
- 2026-06-10 PM 复核补充：Create 视图不再暴露 `completed_with_blocks` 或英文 project-materials blocker；这些可见泄漏已纳入 smoke 硬断言，且 RuntimeStore 已覆盖损坏 `artifact_index.json` 的本地恢复路径。
- 2026-06-10 视口工作台复核：页面不再作为整页长报表滚动；当前应用壳锁定在视口内，导航区和工作区分别内部滚动，Projects/Create/Jobs/Settings 在 917x791 浏览器下页面高度均等于视口高度。
- 2026-06-10 工作区主任务优先复核：Projects 首屏先显示项目中心与项目操作，Assets 首屏先显示素材库，Settings 首屏先显示高级诊断与活动时间线，不再把通用生产状态面板置于诊断页顶部。
- 2026-06-10 首屏中文体验复核已纳入自动 smoke 硬断言：`old_project_ids_visible=false`，`question_mark_runs=0`，`stage_rc_visible=false`，`toast_errors=[]`；旧英文 projection 文案扫描命中 `0`。
- 主路径计数：素材 `1` 个，画布节点 `4` 个，分镜镜头 `3` 个，项目风格偏好 `1` 条，任务 `6` 个，Provider blocker `4` 个。
- 截图：
  - `data/processed/runs/workbench_live_demo/qa/stage7-rc-1440x900-diagnostics.png`
  - `data/processed/runs/workbench_live_demo/qa/stage7-rc-1366x768.png`
  - `data/processed/runs/workbench_live_demo/qa/stage7-rc-390x844.png`
  - `data/processed/runs/workbench_live_demo/qa/acceptance-rehearsal-auto-connect-clean-1440x900.png`
  - `data/processed/runs/workbench_browser_smoke/browser_evidence/workbench-ready-for-next-round.png`
- 结构化证据：`data/processed/runs/workbench_live_demo/qa/stage7-rc-browser-qa.json`。

## 当前边界

- 没有真实 provider 调用。
- 没有写入 secret、signed URL、本地私有素材、provider 原始响应或生成媒体字节。
- Runtime verification 不等于 human acceptance。
- Provider smoke 不等于 business validation。
- 反馈和候选记忆不自动晋升为 durable memory。
- 本演练仍不等于人工验收结论。

## 验收后的下一步

如果人工验收通过：

1. 固定当前 Web release candidate，补最后的提交前代码审查。
2. 按 capability gate 单独准备 provider smoke，不复用本轮 QA 结论。
3. provider smoke 只验证真实模型接入链路，不宣称商业效果。
4. smoke 通过后，再进入提交、合并、推送和分支清理。

如果人工验收不通过：

1. 先按问题严重度修复 blocker 和 major。
2. 重新跑浏览器主路径、focused tests、maintenance audit 和 diff check。
3. 更新本验收包或 QA 账本中的残留风险。
