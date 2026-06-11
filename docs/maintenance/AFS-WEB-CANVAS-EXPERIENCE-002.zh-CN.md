# AFS-WEB-CANVAS-EXPERIENCE-002 维护记录

## 范围

本轮把 AFS Web 的画布体验推进到可操作的专业创作工具 v1：

- 画布节点增加 hover、selected、linked、dimmed、dragging、connecting 和状态 chip。
- 新增 SVG 连接层，支持 connected edge 与 pending edge 的视觉反馈。
- 显性资产架展示人物三视图、场景、关键帧、视频片段、音频和导演台资产。
- 新增 2D 顶视图导演台，覆盖画面参考、房间、人物、相机、Key/Fill/Back Light、反光板、柔光布、遮光旗和道具。
- 新增本地提示词优化器，把普通描述拆成专业提示词包。
- 修复移动端真实 canvas card 被旧执行骨架样式隐藏的问题，窄屏改为单列节点流。

## 维护边界

- 未接入真实 MiniMax 调用；本轮只实现本地 deterministic prompt optimizer。
- 未提交用户提供的 token，未在文档、前端、日志或测试中回显任何 key。
- 未提交 provider 原始响应、signed URL、本地私有媒体路径或生成媒体字节。
- 显性资产只展示 safe summary / thumbnail ref；隐性资产不在主 UI 展现。

## 验证

- 新增红测先失败，随后通过。
- Focused Workbench tests: `21 passed`。
- Runtime-hosted browser QA: desktop + mobile passed，console errors `0`。
- QA 截图目录：`data/processed/runs/workbench_canvas_experience_qa/`。

## 剩余风险

- 节点拖拽和连线当前是本地 UI 意图，不持久化到 Runtime canvas graph。
- 导演台保存按钮目前是安全占位动作，尚未写入真实 `director_setup_asset` registry。
- 提示词优化器 v1 只有规则库，LLM 增强仍需独立 provider-gated slice。

