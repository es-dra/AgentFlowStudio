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

## 边界

- 未修改 Runtime Service / API contract。
- 未打开 LLM/image/video/ASR provider gate。
- 未触发 provider call。
- 未读取或写入 secret、signed URL、本地媒体字节或 Company OS 私有源内容。
- 本次只修复“画布节点卡片大小无法调整”。提示词输入框 resize 已由上一轮修复覆盖；上传 422、固定资产自动复用、关键帧本地编辑仍是独立问题。
