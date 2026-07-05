# AFS Studio 画布节点尺寸调整修复交接

日期：2026-07-05
分支：`zhaowei`
范围：`/studio/` 前端画布节点交互

## 问题

服务器拉取 `32f488f` 后，提示词输入框可调整的问题已处理，但画布上的各类节点卡片仍无法调整大小。

原因是上一轮修复只恢复了 `textarea` 的原生 resize；节点卡片虽然已有持久化字段 `node.w` / `node.h`，渲染也读取这些字段，但画布输入层没有节点 resize handle 和 pointer session。

## 修复

- 在每个 Studio canvas node 右下角增加 `.node-resize-handle`。
- 在 `canvas-input.js` 中优先识别 resize handle，避免被误判为节点拖拽或端口连线。
- 新增 `interaction/node-resize.js`，按 viewport scale 把屏幕拖拽转换为画布世界坐标，写回 `node.w` / `node.h`。
- 节点尺寸采用 12px 网格吸附，并设置最小/最大尺寸边界。
- 折叠节点隐藏 resize handle，避免折叠态误操作。
- 展开态节点同步为明确高度，使用户拖拽后的高度可见且可持久化。
- 新增 `styles/node-resize.css`，保持既有 canvas 样式文件不过度膨胀。

## 修改文件

- `apps/studio/index.html`
- `apps/studio/src/canvas-view.js`
- `apps/studio/src/canvas-input.js`
- `apps/studio/src/interaction/node-resize.js`
- `apps/studio/styles/node-resize.css`
- `apps/studio/styles/interaction-motion.css`
- `tests/test_studio_interaction_layer.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`

## 验证

```text
python -m pytest tests\test_studio_interaction_layer.py -q -> 14 passed
python -m pytest tests\test_web_studio_static.py tests\test_web_studio_frontend_wave.py tests\test_web_studio_prompt_script_static.py -> 45 passed
npm.cmd run check:studio-js -> JS syntax check passed: 122 files
git diff --check -> passed
```

## 服务器复测重点

部署后打开 `/studio/`，新建或选中任意 text/image/video/script/director 等节点，把鼠标移动到节点右下角，拖动细小的斜角 resize handle。

预期：

- 节点宽度和高度会随拖拽变化。
- 松开鼠标后尺寸保留。
- 刷新页面或重新进入同一项目后，节点尺寸仍保留。
- 折叠节点不显示 resize handle。
- 节点不能缩小到默认安全尺寸以下，避免文字和按钮溢出边框。
- 放大节点时，节点内部仍保持工具型 UI 的正常字号；空状态内容在更宽节点中居中，不会被拉成过大的文字面板。
- text 节点的全部意图选项都可见，包括 `文字生音乐`。

## 2026-07-05 截图复测补充

服务端复测发现：节点缩小时内容会溢出到边框外；随后按比例放大内部文字的方案又导致 UI 过重，并且 `文字生音乐` 选项会被挤掉。

补充修复：

- resize 最小尺寸改为按各节点类型默认尺寸计算，不再允许 text/image/video/script 等节点小于默认安全框。
- 渲染层使用 `boundedNodeFrame(node)`，兼容旧项目里已经保存过的过小节点尺寸。
- 移除粗暴的内部字体放大方案，保持节点卡片为工具型 UI。
- `node-resize.css` 让空状态内容在大节点中保持正常字号并居中，移除 body 裁剪，保证全部意图行可见。

补充验证：

```text
python -m pytest tests\test_studio_interaction_layer.py tests\test_web_studio_static.py tests\test_web_studio_frontend_wave.py tests\test_web_studio_prompt_script_static.py -> 60 passed
npm.cmd run check:studio-js -> JS syntax check passed: 122 files
git diff --check -> passed
```

## 边界

- 未修改 Runtime Service / API contract。
- 未打开 LLM/image/video/ASR provider gate。
- 未触发 provider call。
- 未读取或写入 secret、signed URL、本地媒体字节或 Company OS 私有源内容。
- 本次只修复“画布节点卡片大小无法调整”。提示词输入框 resize 已由上一轮修复覆盖；上传 422、固定资产自动复用、关键帧本地编辑仍是独立问题。
