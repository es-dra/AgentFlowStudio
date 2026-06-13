# AFS 浏览器 QA 加固记录 - 2026-06-13

## 范围

本切片修复 Claude 小白走查实锤的问题，并由 Codex 接管真实 Studio 浏览器路径做循环测试。目标不是减少真实 provider 调用，而是尽快暴露数据污染、死控件、语义错位、provider 失败、资产携带失真和视频链路问题。

本记录只声明 runtime/browser verification，不声明 human acceptance、business validation 或 durable memory promotion。

## 已修复的问题

- 项目切换不再长期 fallback 到无命名空间的 `afs_studio_canvas_v2`。旧 key 只做一次性迁移并删除，切换项目时先清空内存状态，再从项目命名空间和 Runtime `studio-state` 恢复。
- 新建项目从原生 `window.prompt` 改为页面内 modal；创建成功后即时切换 URL、active project、项目下拉和空画布。
- 导演台追加提示词从原生 `window.confirm` 改为页面内确认 modal。
- Provider registry 与 MiniMax/Kling plan 层把旧 `NARRATOCUT_ALLOW_REMOTE_*` gate 归一为 `AFS_ALLOW_REMOTE_*`；`.env.example` 也已移除旧 gate 前缀。
- Registry 跳过 `company_gateway` 聚合占位服务，避免它阻断 `minimax_llm`、`minimax_image`、`kling_i2v` 等真实 adapter。
- 提示词优化按 T2I/I2I 分流：无参考图时使用文生图扩写模板，有上传/连线/asset_refs 时使用图生图最小变更模板，并在优化弹窗展示模式。
- 上传图片成功后立即 flush Studio state 到 Runtime，避免刷新后丢预览。
- 图像生成/优化失败的用户文案不再直接暴露 gate 变量名、provider service id 或内部状态；技术细节留在折叠详情。
- 项目下拉默认折叠 smoke、QA、debug 项目；当前项目始终可见，并提供“显示全部”开关。
- 新项目首个节点编号从 1 开始。
- 新建节点会避让现有节点，不再默认落在重叠区。
- 图片节点底部只保留模型选择、优化、生成三类当前有效控件。
- 视频节点底部只保留 Kling I2V 当前可用控件；未实现模式和候选数量入口隐藏。
- Runtime 同步 fixed visual assets 时保留安全字段、缩略图和特征卡摘要；资产抽屉刷新后仍能展示 fixed/retired 状态。
- 资产抽屉“用于当前节点”对 fixed visual asset 写入 `node.params.visualAssets`，让节点 badge、context_subgraph 和 resolver 使用同一字段。
- 资产只读弹窗展示签名、特征卡、锁定项、状态、来源节点，并确认不暴露本地路径、Bearer token、signed URL 或 provider raw。
- `lastContextBundle` 改为安全摘要持久化，刷新后仍能看到“本次携带”和“本次已解除锁定”；`trace_summary`、provider prompt 等细节仍不进 Studio state。
- 生成成功/失败、视频轮询成功/失败后主动 flush Runtime save，减少 debounce 丢最终状态的风险。
- 视频节点可以从资产抽屉把现有 image asset 显式设为首帧或尾帧；不会隐式使用最后上传图。
- 视频节点只从 `lastVideoPreviewUrl` 恢复 `<video>` 预览，普通 image preview 不会被误当作视频源。
- Prompt bar 在视频节点 `generating + lastVideoJobId` 时执行继续轮询，不再误触发第二次付费 submit；状态完成后按钮恢复为“生成”。

## 浏览器 QA 回合记录

### 回合 1：小白项目路径

- Studio shell 可加载。
- 页面内新建项目 modal 可出现并切换项目。
- 新项目初始为空画布。
- 旧无命名空间 canvas key 不再污染新项目。
- T2I 优化返回 200，弹窗显示文生图模式。
- 上传按钮可以触发文件选择器。
- Runtime 上传图片返回 200，刷新后预览可复显。
- 切换到另一个新项目后不会泄漏旧画布；旧项目再切回时节点仍存在。

证据：

```text
runs/browser_qa_hardening_1781302404.json
runs/browser_qa_hardening_1781302404.png
```

### 回合 2：I2I 和资产面板

- 空 UI 项目的项目下拉、drawer 标题、URL 与 Runtime active project 保持一致。
- 新项目不再注入 demo placeholder assets。
- I2I 优化会向 Runtime 传入安全上传图摘要。
- 当远程 LLM 忽略参考图或漏掉短发/校服锁定时，guardrail fallback 会替换优化结果，并在 safe manifest 记录 `guardrail_fallback_used=true`。
- MiniMax 图生图返回 safe preview；输出比早期失败样例更接近短发和蓝白校服，但身份、姿态、背景仍有漂移。

证据：

```text
runs/asset-panel-studio-loop-asset-1781306621.png
runs/drawerasset-dedup-studio-loop-drawerasset-1781307169.png
runs/i2i-opt-guardrail2-studio-loop-i2iopt-1781307866.png
runs/i2i-gen-studio-loop-i2igen-1781307999.png
runs/video-clean2-studio-loop-video-clean-1781308277.png
```

### 回合 3：Kling I2V 异步链路

- `KlingVideoAdapter` 不再把通用 adapter plan 字段直接透传给 legacy smoke。
- Studio 视频 submit 变成真正异步：`registry.submit()` 返回 `submitted`，后续由 `registry.poll()` 完成。
- Runtime video routes 对 provider adapter 异常写 safe manifest，不再直接 HTTP 500。
- poll 对 `running` 做可恢复处理。
- 真实 Kling I2V submit/poll 成功，preview endpoint 返回 `video/mp4`。

证据：

```text
project: studio-loop-kling-async-081724
job: studio-loop-kling-async-081724-video_generation-81f3015bb2c8
POST /video-generations: 200 submitted
poll #1: running
poll #2: succeeded
preview content-type: video/mp4
ffprobe: h264, 1924x1076, 24fps, duration 5.041667s
safe manifest: provider_raw_response_stored=false, provider_urls_persisted=false, media_bytes_returned_by_api=false
runs/kling-async-studio-loop-kling-async-081724.png
runs/kling-async-081724-first.png
runs/kling-async-081724-last.png
```

### 回合 4：视频恢复和预览播放器

- Studio state 允许安全持久化 `firstFrameImageAssetId`、`lastFrameImageAssetId`、`lastVideoJobId`、`lastVideoPreviewUrl`、`quotaOverrideConfirmed`。
- 刷新后视频节点可继续轮询。
- 成功 poll 后节点预览使用 Runtime safe video preview endpoint。
- 视频结果用 `<video controls>` 渲染，不再走图片预览组件。

证据：

```text
project: studio-loop-kling-async-081724
job: studio-loop-kling-async-081724-video_generation-e2d8ab654542
poll menu after refresh: visible
poll result: succeeded
DOM preview: videoCount=1, imageCount=0
runs/kling-poll-ui-video-preview-20260613.png
```

### 回合 5：新项目资产语义

- Runtime fixed visual asset 刷新后保留 `asset_type`、`image_asset_refs` 和安全缩略图。
- 资产抽屉 correctly 标注人物资产/场景资产。
- 自动预填特征卡从优化结果段落提取更丰富字段，并去重。
- 新 image node 避让已有节点。
- fixed asset 写入当前节点后，节点显示资产 badge。
- 带资产的优化返回 200，面板显示项目资产引用和已连线状态。
- 带资产的生成返回 safe preview，结果显示“本次携带 1 项资产”。

证据：

```text
runs/loop-fresh-asset-drawer-20260613.png
runs/loop-attached-asset-optimize-20260613.png
runs/loop-attached-asset-generation-20260613.png
```

### 回合 6：本次携带和临时解除刷新持久化

- 生成结果 live 状态显示“本次携带 1 项资产”和“本次已解除锁定”。
- 早期保存失败是因为 `lastContextBundle.trace_summary` 被 Studio state 安全扫描拒绝；现已改为只保存安全摘要。
- 刷新后节点仍保留 `lastContextBundle.included_assets` 与 `temporary_lock_overrides` 摘要。
- 请求级 `temporaryLockOverrides` 仍会在生成后清空，不会延续到下一次生成。

证据：

```text
project: studio-1781312384129-vx6iab
job: studio-1781312384129-vx6iab-keyframe_generation-50cfa9ebaa84
node: node_5
refresh result: 本次携带 1 项资产; 本次已解除锁定 keep black short hair
```

### 回合 7：资产设为视频首帧和防重复 submit

- 选中 video node 时，资产抽屉的 image asset 会显示“设为首帧 / 设为尾帧”。
- 点击“设为首帧”后，节点显示 `已设为首帧 img_...`，请求使用明确的 image asset id。
- 视频节点刷新时不会把普通 image preview 恢复为 `<video>` source。
- Prompt bar 在视频生成中状态下执行继续轮询，不再重复 submit；完成后按钮 title 恢复“生成”。
- 最终视频节点显示 safe `<video controls>` 预览，页面控制台无 AFS 业务错误。

证据：

```text
project: studio-1781312384129-vx6iab
node: node_11
latest job: studio-1781312384129-vx6iab-video_generation-0388b268aec4
status: succeeded
preview route: /projects/studio-1781312384129-vx6iab/video-generations/.../preview
safe manifest: provider_raw_response_stored=false, provider_urls_persisted=false, media_bytes_returned_by_api=false
```

## 自动化验证

最终验证结果：

```text
focused pytest:
tests/test_api_runtime_studio_state.py
tests/test_web_studio_static.py
tests/test_api_runtime_video_generations.py
tests/test_provider_adapter_registry.py
tests/test_api_runtime_prompt_memory_loop.py
tests/test_api_runtime_creative_agent_keyframes.py
72 passed, 1 warning

Studio JS:
node --check apps/studio/src/**/*.js
37 files passed

full pytest:
886 passed, 2 warnings

maintenance_audit:
failed=0, warning=2

git diff --check:
exit 0, CRLF notices only
```

## 已知剩余风险

- MiniMax 单参考图加文本护栏仍不足以保证生产级人物身份一致性。当前证据只能说明链路工作、约束有帮助，不能替代 human visual scoring。
- 用多视图人物资产图直接做 Kling 首帧会产生推近和裁切伪影。视频 I2V 更适合使用专门关键帧，而不是三视图资产板。
- 自动化浏览器对本机文件选择和某些文本输入仍有限制；上传/预览通过 Runtime API 与可见 UI 验证，但完整人工文件选择仍需人工验收补一遍。
- 历史项目中已经存在的节点重叠不会被自动重排；新建节点已避让。
- 真实 provider gate 在本机长期打开用于 QA，但这仍是 runtime/provider verification，不是 human acceptance。

## 非声明边界

- 不声明内测人员已验收。
- 不声明生成质量已经达到业务可发布。
- 不声明 provider 输出稳定可复现。
- 不把本轮反馈自动晋升为 durable memory 或公司 active rule。
