# AFS Studio Text Optimizer Merge Fix 20260707

## 摘要

本轮从 `origin/zhaowei` 的提交
`8a5db1ee93b22fac0e7777895d1f944fd6d9a16f` 选择性三方移植
Studio 文本/剧本优化回写修复。当前基底是 `master`
`d0a722ac654d918d17a4685c911e06ac823bb850`，工作分支是
`codex/recover-visible-script-optimizer-20260707`。

## 根因

上传剧本或文本节点的可见正文可能存放在 `node.content`，但优化成功后
旧逻辑只写回 `node.prompt`。因此 Runtime 优化可以成功，输入框也可能显示
优化文本，但画布正文仍保留旧内容。另一个触发点是
`nodeBodySignature` 只记录 `content.length`，同长度替换时画布不会感知正文
变化。

## 合并方式

- 未整分支 merge `origin/zhaowei`，因为该分支还包含图片 relay、参考图
  transform、节点 resize 等无关变更，并且与当前 `master` 存在多处冲突。
- 只移植 `8a5db1e` 中与当前故障直接相关的行为：
  - 优化成功后 text/script 节点同步写回 `prompt` 和 `content`。
  - text/script 优化入口使用 `content || prompt` 判空。
  - text/script 展开编辑器优先显示 `content || prompt`。
  - 画布节点签名使用完整 `content`，避免同长度正文替换不刷新。
  - 增加上传剧本正文只在 `content` 时的回归测试。

## 非目标

- 不合并 `zhaowei` 分支中图片节点、参考图、模型 preset、Runtime provider
  relay 或 UI resize 相关提交。
- 不改变远程 LLM、ASR、image、video provider gate。
- 不保存 provider 原始响应、signed URL、本地素材字节、secret 或私有商业判断。
- 不声明 human acceptance、creative quality acceptance 或 business validation。

## 验证

```text
.venv/bin/python -m pytest tests/test_web_studio_prompt_script_static.py::test_text_prompt_optimization_uses_and_updates_visible_content -q
1 passed

.venv/bin/python -m pytest tests/test_web_studio_prompt_script_static.py tests/test_api_runtime_prompt_memory_loop.py -q
55 passed

npm run check:studio-js
JS syntax check passed: 151 files

git diff --check
passed
```

## Runtime 重启

本轮使用 systemd 正式重启两个 Runtime unit：

```text
systemctl restart afs-runtime.service afs-runtime-zhaowei-test.service
```

结果：

- `afs-runtime.service` 8790：新 PID `2405408`，`/health` 返回 `ready`。
- `afs-runtime-zhaowei-test.service` 8792：新 PID `2405410`，`/health` 返回
  `ready`。
- 8790/8792 的 `/studio/src/optimizer.js` 静态路由均包含
  `node.content = text` 和 `isTextContentNode`。
- 8790/8792 的 `/studio/src/canvas-node-body.js` 静态路由均包含
  `node.content || ""`，不再使用 `content.length` 作为正文签名。
