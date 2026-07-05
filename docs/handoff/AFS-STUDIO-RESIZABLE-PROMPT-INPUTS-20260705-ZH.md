# AFS Studio 提示词输入框可调整修复交接

Date: 2026-07-05

Task class: Standard

## 背景

用户在 Web 端测试中反馈：各类节点、提示词输入框大小无法调整，长提示词编辑不便。代码审查确认根因是 `apps/studio/styles/base.css` 中全局 `textarea { resize: none; }` 关闭了原生拖拽调整能力，只有少数局部样式重新打开。

## 改动范围

- `apps/studio/styles/base.css`
- `apps/studio/styles/prompt-bar.css`
- `apps/studio/styles/studio-canvas-maturity.css`
- `apps/studio/styles/modals.css`
- `tests/test_web_studio_static.py`

## 修复内容

- 全局 textarea 默认恢复垂直调整能力，并保留滚动。
- 浮动 prompt bar 的提示词输入框支持垂直调整，最大高度受视口约束。
- 放大编辑窗支持整体双向调整，内部 textarea 支持垂直调整。
- 节点正文编辑器支持更大高度的垂直调整，避免旧的 `text-content-view` 上限压住剧本/资产卡长文本。
- 生成设置面板和资产卡/视觉资产面板的长文本字段支持垂直调整。
- 新增静态回归测试，防止后续再次把 Studio 主要提示词 textarea 锁死。

## 边界

- 未修改 Runtime Service / API contract。
- 未触发 LLM、image、video、ASR provider。
- 未读取或写入 provider raw response、secret、signed URL、生成媒体字节或用户本地素材字节。
- 本修复只解决输入框可调整能力，不声明关键帧局部修改、资产自动复用或上传 422 问题已修复。

## 建议验证

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_static.py tests\test_web_studio_frontend_wave.py tests\test_web_studio_prompt_script_static.py
npm.cmd run check:studio-js
git diff --check
```
