# AgentFlow Studio Skill 目录

本目录保存 agent-readable task contract。它们不是运行时 agent，也不会自行调用模型。

Skill 的作用是告诉 Agent：

- 什么时候使用某条 AFS workflow。
- 必须提供哪些输入。
- 应该读取哪些 artifact。
- 哪些 quality gate 通过后，结果才可继续流转。

## 当前推荐 skill

- `agentflow_production_handoff.skill.yaml`：从 creative brief 生成结构化 production handoff。
- `video_to_real_clips.skill.yaml`：从源视频生成高亮计划并执行本地真实切片。

旧高亮打包 skill 已退休。当前项目保留纯切片、高亮计划和 Production Memory / Production Handoff 主线，不再维护 finished package 生成 skill。

Agent 应优先读取当前 skill 文件，而不是扫描整个 `workflows/` 目录后自行猜测。
