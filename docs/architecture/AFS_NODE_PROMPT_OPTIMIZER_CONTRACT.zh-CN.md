# AFS 节点提示词优化契约

日期：2026-06-11

本文定义 AFS Studio 节点输入位调用提示词优化的最小契约。用户只看到“优化”按钮和锚定在输入框附近的结果浮层。专业规则、trace、记忆装配、provider 状态和 safe manifest 都留在 Runtime Service 边界之后。

## Runtime 入口

```text
POST /projects/{project_id}/prompt-optimizations
```

前端只提交安全节点上下文：

- `node_id`：画布节点 id，可为空。
- `node_type`：`text`、`image`、`video`、`audio`、`script`、`director`。
- `prompt_text`：用户在节点输入框中写下的原始描述。
- `generation_target`：`prompt`、`script`、`image`、`keyframe`、`video`、`audio`。
- `target_platform`：v1 默认 `short_video`。
- `style`：项目风格、节点风格和低权重用户偏好摘要。
- `asset_refs`：只允许安全 artifact id，不传本地路径、媒体字节或 signed URL。
- `director_setup`：导演台节点可传 2D 机位、主体、灯光、阻挡和运动结构。

## 节点映射

| 节点 | node_type | generation_target | 优化重点 |
|---|---|---|---|
| 文本 | `text` | `prompt` | 创作意图、主体、场景、镜头方向 |
| 图片 | `image` | `image` / `keyframe` | 角色一致性、构图、灯光、美术、负面约束 |
| 视频 | `video` | `video` | 首尾帧、素材引用、运动、时间推进、镜头连续性 |
| 音频 | `audio` | `audio` | 旁白语气、停顿、重音、音色、节奏、音效边界 |
| 脚本 | `script` | `script` | beat、分镜交接、角色动作、短视频节奏 |
| 导演台 | `director` | `video` / `keyframe` | 2D 空间、机位、灯光、人物阻挡、运动方向 |
| 视频合成 | `video_merge` | no prompt by default | 默认不显示优化动作；后续有“合成意图 prompt”时再接入 |

## 前端使用字段

普通用户浮层只消费：

- `original_prompt`
- `optimized_prompt`
- `prompt_sections`
- `ui_surface`
- `provider_calls_started`

允许展示的状态文案：

- 已按影视结构优化
- 已结合项目风格
- 已参考角色/场景设定
- 已用本地优化
- 已完成优化

普通用户 UI 禁止展示：

- 工程 gate、诊断、任务中心和服务内部术语。
- 知识规则 id、权重、match reason、trace 内部字段和 safe manifest。
- 记忆确认流程或隐藏资产内部字段。
- 本地绝对路径、signed URL、provider 原始响应或媒体字节。

## 装配优先级

```text
professional_knowledge_base
-> script_character_scene_assets
-> user_preferences
```

用户偏好只能作为低权重风格信号，不能覆盖专业规则、节点目标、角色身份、场景连续性、导演台空间关系或 provider-off 安全边界。

## 验收边界

- v1 默认不启动真实 LLM、image、video 或 audio provider。
- trace 和 safe manifest 是工程证据，不是普通 UI。
- 浏览器验收只检查节点输入、优化、替换、追加、复制和零 provider 请求。
