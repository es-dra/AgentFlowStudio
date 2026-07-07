# AFS Studio 场景化提示词升级交接记录

日期：2026-07-07

## 目标

本次改造不是取消模板化提示词，而是在保留专业模板稳定性的基础上，让优化结果按真实使用场景切换：

- 剧本/文本优化保留叙事表达。
- 生图优化保留专业画面结构。
- 图生图局部修改继续保持参考图身份与布局。
- 原创重生 / 降 IP 风险只提取灵感与视觉证据，不复制身份、服装、构图或标志性 IP 线索。
- 视频优化强调首帧、时间推进、动作幅度和镜头连续性。

## 主要改动

- Studio 前端：
  - `apps/studio/src/prompt-bar.js`
    - 资产卡提示词栏新增 `局部修订` / `原创重生` 模式。
  - `apps/studio/src/panels/asset-card-panel.js`
    - 资产卡保存面板新增参考图用途选择。
  - `apps/studio/src/asset-revision-references.js`
    - 新增 `localized_edit` 与 `originalize_ip_safe` 模式。
  - `apps/studio/src/optimizer-contract.js`
    - 将 `reference_transform_mode` 传给 Runtime。
  - `apps/studio/src/node-video-actions.js`
    - 视频请求也携带参考图转换模式。

- Runtime / 算法层：
  - `apps/api/runtime_reference_intent.py`
    - 统一识别局部修订与原创重生模式。
  - `apps/api/runtime_llm_enhancement_instructions.py`
    - 图生图原创重生模式使用独立优化指令。
  - `apps/api/runtime_llm_enhancement_fallback.py`
  - `apps/api/runtime_originalize_prompt_templates.py`
    - LLM 不可用时也能生成原创重生 fallback。
  - `apps/api/runtime_asset_card_revision_prompt.py`
  - `apps/api/runtime_keyframes.py`
    - 原创重生模式不再把 reference #1 当作 primary visual source of truth。
  - `agentflow/algorithms/creative_intent_control/video_prompt.py`
  - `agentflow/algorithms/provider_gate_manifest/video_prompt.py`
    - 视频提示词区分首帧强锚定与原创重生灵感参考。

## 验证

已执行：

```text
npm.cmd run check:studio-js
-> JS syntax check passed: 122 files

bundled Python py_compile changed prompt modules
-> passed

git diff --check
-> passed

function smoke
-> 中文“原创重生 / 降 IP 风险”可识别为 originalize_ip_safe
-> instruction / fallback 文案切换成功
```

未执行完整 pytest：

- 当前本机系统 `python -c` / `python -m pytest` 在受控 PowerShell 下无输出返回 1。
- Codex bundled Python 可执行并通过 `py_compile`，但未安装 `pytest`，且直接导入部分 Runtime 模块会缺少项目依赖如 `yaml`。

## 边界

- 未开启任何 provider gate。
- 未发起远程 LLM / image / video / ASR 调用。
- 未写入素材字节、signed URL、provider 原始响应、secret 或私有知识库内容。
- 本次只改变提示词模式和请求语义，不声明可绕过 provider 政策，不声明法律清权，也不声明人工创意验收通过。
