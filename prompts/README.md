# Prompt 模板目录

本目录用于保存可审计的 prompt template。

当前边界：

- prompt 模板是执行投影，不是公司长期记忆。
- 远程 LLM 默认关闭。
- 只有显式设置 `AFS_ALLOW_REMOTE_LLM=true` 后，相关 provider adapter 才允许发起远程 LLM 调用。
- prompt 文件可以引用 `artifact_type`、JSON key、CLI command 等机器契约英文名称。
- prompt 文件不得包含 provider key、cookie、signed URL、客户私密信息或未公开商业判断。
