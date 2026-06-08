# AgentFlow Studio Skill 目录

本目录保存 agent-readable task contract。它们不是运行时 agent，也不会自己调用模型。

Skill 的作用是告诉 Agent：

- 什么时候使用某条 AFS workflow；
- 必须提供哪些输入；
- 应该读取哪些 artifact；
- 哪些 quality gate 通过后，结果才可继续流转。

当前推荐产品 skill：

- `short_highlight_package.skill.yaml`：本地优先的视频高光短内容包。
- `video_script_highlight_package.skill.yaml`：视频 + 脚本的本地优先高光短内容包。
- `agentflow_production_handoff.skill.yaml`：从 creative brief 生成结构化 production handoff。

Agent 应优先读取这些 skill 文件，而不是扫描整个 `workflows/` 目录后自行猜测。
