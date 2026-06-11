# AFS Studio v0.2 交付级体验打磨 001

日期：2026-06-12

执行角色：前端交互设计师 + Runtime/API 集成 + QA 门禁

## 摘要

本分支把 Studio 从“Alpha 画布骨架”推进到“内部交付 MVP”的体验阶段。用户侧表达不再围绕竞品节点形式，而是统一为 **AFS Studio 创作图谱**：仍以无限画布为主体验，但新增安全保存恢复、显性资产复用、语义连线、提示词副驾驶反馈，以及二维导演台对下游提示词的联动。

本轮没有打开任何真实 provider gate，没有生成图片、视频或媒体字节，也没有写入长期记忆。

## 已落地

- 新增安全的 Studio state Runtime API：
  - `GET /projects/{project_id}/studio-state`
  - `PUT /projects/{project_id}/studio-state`
- Runtime 只保存安全前端状态：
  - `meta`
  - `viewport`
  - `nodes`
  - `edges`
  - `order`
  - `assets`
- Runtime 明确拒绝：
  - provider secret
  - 本地绝对路径
  - signed URL
  - provider raw
  - media bytes
  - trace
  - hidden memory
  - knowledge weights
- 前端新增 Runtime 保存/恢复，Runtime 不可用时回退 `localStorage`。
- 顶栏显示保存状态：`已保存 / 保存中 / 同步中 / 本地暂存`。
- 新增轻量 undo/redo，覆盖有意义的图谱编辑；平移、缩放、拖动、逐字输入不进入历史栈，避免撤销链路被噪声污染。
- 空画布 starter 改为 AFS 流程入口：
  - 上传剧本生成分镜
  - 创建角色三视图
  - 布置二维导演台
  - 生成关键帧提示词
  - 生成 5s 视频片段提示词
- 显性资产抽屉升级：
  - 本地预览和导演台保存会生成类型化资产卡。
  - 资产卡图片优先，文字降低密度。
  - 支持 `设为参考`、`用于当前节点`、`从画布定位`。
- 连线增加语义：
  - `generation`：普通生成依赖。
  - `director`：导演台约束。
  - `reference`：参考关系。
- 导演台保存后会生成 `director_setup` 显性资产。
- 导演台应用到相连节点时，下游边会标记为导演台约束，后续提示词优化可读取导演台上下文。
- 提示词优化仍只在输入位出现，不新增记忆确认页。
- 优化结果操作增加反馈：替换、追加、复制都有可见状态变化。
- 优化来源 chip 只显示用户可理解的内容：
  - 影视结构
  - 项目风格
  - 角色/场景设定
  - 导演台布置
- 修复窄屏横向溢出。
- 拆出 `apps/studio/styles/assets.css`，避免 `shell.css` 超过维护阈值。

## 验证

```text
Runtime-hosted browser QA:
- http://127.0.0.1:8807/studio/
- desktop: 导演台 starter -> 导演台节点 -> 打开二维导演台，通过
- mobile: 横向溢出 false

Focused tests:
- 27 passed, 1 Starlette/httpx warning

Full pytest:
- 772 passed, 1 Starlette/httpx warning

Other gates:
- apps/studio JS node --check: passed
- tools/maintenance_audit.py: passed
- git diff --check: passed with Windows CRLF notices only
```

## 边界

- provider gate 仍然关闭。
- 没有真实图片或视频生成。
- 没有保存 provider 原始响应。
- 没有保存本地私有素材路径。
- 没有保存媒体字节。
- 这不是 human acceptance。
- 这不是 business validation。
- 这不是 provider smoke。
- 这不是 durable-memory promotion。

## 后续建议

- 用一个真实剧本做人工体验验收，检查用户是否能无指导完成一次“剧本 -> 分镜 -> 导演台 -> 关键帧提示词”的路径。
- 增加更深的浏览器 QA：节点拖拽、端口连线、连接导演台后的 prompt 优化、资产附加、刷新恢复。
- 用户确认后，再决定是否把本分支合入主线，然后继续真实图片 provider smoke。
