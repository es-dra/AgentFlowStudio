# AFS 节点提示词优化契约

日期：2026-06-11

本文档定义 LibTV 式画布中节点输入位调用后台提示词优化的最小契约。普通用户只看到节点内的“优化”动作和结果浮层；知识库、trace、记忆状态、provider gate 和安全 manifest 都留在后台。

## 入口

Runtime API：

```text
POST /projects/{project_id}/prompt-optimizations
```

前端只提交当前节点的安全上下文：

- `node_id`：画布节点 id，可为空。
- `node_type`：`text`、`image`、`video`、`audio`、`script`、`director`。
- `prompt_text`：用户在节点输入框内写下的原始描述。
- `generation_target`：`prompt`、`script`、`image`、`keyframe`、`video`、`audio`。
- `target_platform`：第一版默认为 `short_video`。
- `style`：项目风格、当前节点风格和低权重用户偏好的合并描述。
- `asset_refs`：只允许安全 artifact id，不传本地路径、媒体字节或 signed URL。
- `director_setup`：仅导演台节点可传 2D 人物、灯光、机位、运动方向结构。

## 节点映射

| 节点 | node_type | generation_target | 优化重点 |
|---|---|---|---|
| 文本 | `text` | `prompt` | 创作意图、主体、场景、镜头方向 |
| 图片 | `image` | `image` / `keyframe` | 角色一致性、构图、灯光、美术、负面约束 |
| 视频 | `video` | `video` | 首尾帧/素材引用、运动、时间推进、镜头连续性 |
| 音频 | `audio` | `audio` | 旁白语气、停顿、重音、音色、节奏、音效边界 |
| 脚本 | `script` | `script` | beat、分镜交接、角色动作、短视频节奏 |
| 导演台 | `director` | `video` / `keyframe` | 2D 空间、机位、灯光、人物阻挡、运动方向 |
| 视频合成 | `video_merge` | 默认无 prompt 输入 | 默认不显示优化按钮；只有后续新增“合成意图 prompt”时再接入 |

## 返回使用

前端普通浮层只使用：

- `original_prompt`
- `optimized_prompt`
- `prompt_sections`
- `ui_surface`
- `provider_calls_started`

前端可以展示的状态文案仅限：

- 已按影视结构优化
- 已结合项目风格
- 已参考角色/场景设定
- 已用本地优化
- 已完成优化

前端普通 UI 禁止展示：

- Provider、Runtime、Gate、预检、诊断、任务中心。
- 知识库、rule id、weight、match_reason、trace、safe manifest。
- 候选记忆、确认/拒绝、隐性资产、durable memory。
- 本地绝对路径、signed URL、provider 原始响应、媒体字节。

## 后台优先级

Prompt Assembly 固定按以下顺序选择上下文：

```text
professional_knowledge_base
-> script_character_scene_assets
-> user_preferences
```

用户偏好只能作为低权重风格倾向，不能覆盖专业规则、当前节点目标、角色身份、场景连续性、导演台空间关系或 provider-off 安全边界。

## 验收边界

- 第一版不启动真实 LLM、image、video、audio provider。
- API 返回 trace 和 safe manifest 是工程证据，不是普通用户 UI。
- 浏览器验收只检查普通 UI 是否能输入、优化、替换、追加、复制、应用，并确认 provider requests 为 0。
