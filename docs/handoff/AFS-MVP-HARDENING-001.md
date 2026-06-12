# AFS-MVP-HARDENING-001 Handoff

中文摘要：本切片在 Kling/I2V 动态阶段前，收口 provider prompt、资产注入、子图跳数、同名资产仲裁、bundle 可复现元数据，以及内测最容易误解的 Studio 控件。

## Implemented

- Provider prompt 段头剥离：后端新增 `user_prompt_plain`，前端生成请求优先使用最近一次优化的 plain 版；后端 keyframe prompt 再兜底去除 `人物/场景/镜头/灯光/运动/负面约束` 等段头。
- Generate 模式资产上限：人物最多 3 个 full card，场景最多 1 个 full card；超出资产只注入签名，并在 `excluded_assets` 记录 `degraded_to_signature_over_limit`。
- Context subgraph 跳数：`reference` 边不消耗普通 3 跳预算，单独最多 6 层防环；`generation/director` 仍受 3 跳限制。
- `visual_asset` 升级到 v0.2，新增 `supersedes_asset_id`；同项目同类型同 label 多个 fixed 资产只选择版本链末端，未建链时选择最新 `server_recorded_at`。
- `context_bundle` 新增 `resolver_version`、`vocabulary_hash`、included asset 的 `feature_card_hash`。
- 图像 provider readiness/network 类错误会短退避重试一次，`retry_count` 写入 safe manifest；配置错误、invalid key、4xx 类语义错误不重试。
- Studio 删除非图片节点假生成占位：当前 MVP 只有图片节点可真实生成；视频/音频/脚本/合成发送按钮禁用并给出 tooltip。
- Studio 资产 lifecycle UI：固定成功提示画布撤销不会撤销资产；节点资产 badge 和 drawer 显性资产卡支持只读详情；retired/superseded/missing 资产在生成后灰显为“已失效，本次未携带”。
- Studio 文案收口：去掉 visible `asset_fix`，拒绝按钮改为“不采用”，优化资产 chip “项目内可用”改为“未引用 · 可连线”，隐藏未接真实计价的成本数字。
- 节点悬浮“固定为资产”入口中文化，避免内测 UI 露出 `fix visual asset`。
- Drawer 搜索现在按资产标题、摘要、asset id 过滤；快捷键面板补 `?`、`Ctrl+L`、`Ctrl+D`。

## Verification So Far

```text
Backend focused:
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_context_resolver.py tests\test_api_runtime_visual_assets.py tests\test_api_runtime_creative_agent_keyframes.py tests\test_api_runtime_prompt_memory_loop.py -q
33 passed, 1 Starlette/httpx warning

Studio static:
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_static.py -q
12 passed

Changed Studio JS node --check:
optimizer-contract.js, optimizer.js, prompt-bar.js, node-actions.js, canvas-input.js, canvas-view.js, visual-asset-panel.js, drawer.js, asset-detail-popover.js, shortcuts-panel.js passed

Full pytest:
.\.venv\Scripts\python.exe -m pytest -q
855 passed, 1 Starlette/httpx warning

Maintenance audit:
failed=0, passed=4, warning=2
warnings are existing human-doc Chinese coverage and oversized-file findings; no secret-like fragments or tracked runtime artifacts.

git diff --check:
passed with Windows CRLF notices only

Browser light QA:
`http://127.0.0.1:8790/studio/` loaded without console errors; visible page no longer contains `asset_fix`, `fix visual asset`, `本地预览`, or `.bar-cost`; node fixed-asset action title is `固定为资产`. The current browser state had no `.asset-badge`, so readonly asset-detail clicking still needs a seeded asset state for full browser QA and is currently protected by static tests.
```

## Boundaries

- No Kling/video provider work is included.
- No live provider call is claimed by this handoff.
- Browser QA in this slice is a light runtime smoke, not full human acceptance.
- Runtime verification is not human acceptance.
