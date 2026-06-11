# AFS 专业创作提示词知识库

这是 AFS 专业创作提示词知识库的 repo-safe 执行副本，用于 Runtime Service 的节点提示词优化。

主副本位置：

```text
10-Startup/70-Projects/AgentFlow-Studio/knowledgebase
```

运行时副本位置：

```text
agentflow/knowledge
```

## 目标

第一版知识库只服务后台提示词优化，不做用户可见的知识库管理界面。Web 侧仍保持 LibTV 式画布体验，只在节点 prompt 输入处提供优化动作。

知识库规则负责提供可解释、可追踪、可测试的专业提示词结构，覆盖导演意图、摄影语言、镜头调度、灯光设计、美术场景、分镜、短视频脚本、角色一致性、关键帧连续性、视频运动、二维导演台和负面约束。

## 优先级

Prompt Assembly 的上下文优先级固定为：

```text
professional_knowledge_base
-> script_character_scene_assets
-> user_preferences
```

用户偏好只能作为低权重风格倾向，不能覆盖专业硬约束、当前节点目标、角色身份、场景连续性或 provider 关闭边界。

## 文件结构

```text
README.md
registry.json
schema/creative_prompt_rule.schema.json
rules/*.jsonl
examples/*.jsonl
```

每条规则必须有稳定 `rule_id`，并包含适用范围、权重、必要槽位、提示词转换、负面约束、质量检查项和来源引用。Runtime 输出的 `PromptAssemblyTrace` 必须能追溯到实际命中的 rule id。

## 安全边界

- 不写入 secret、token、cookie、provider key 或 signed URL。
- 不写入本地私有素材路径、生成媒体字节或 provider 原始响应。
- 不复制公司私有知识库原文、未公开商业判断、客户信息或内部复盘。
- 不逐字搬运外部指南；只保留短来源引用，并把方法抽象成 repo-safe 规则。
- 不把专家判断变成不可解释黑箱偏好；后续专家意见只能以规则权重、适用场景、反例约束和质量检查项进入。

## 同步要求

主副本与运行时副本必须通过 normalized hash 校验。同步失败时，知识库测试应失败；不得让 Runtime 使用未知版本的规则。