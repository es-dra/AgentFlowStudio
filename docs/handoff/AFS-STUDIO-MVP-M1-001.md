# AFS Studio MVP M1 001

中文摘要：本文是当前 Studio 前端第一版的交接说明。有效入口是 `/studio/`，目标是类 LibTV 的节点画布和节点 prompt 优化体验；旧 `/workbench/`、旧静态 Web 和历史 RC 页面均不是当前产品入口。后续 UI 验收应围绕节点创建、prompt 输入、优化应用、历史/广场/导演台入口和移动布局展开。

执行标准：Studio 前端只展示用户需要的创作动作，不暴露 rule 权重、trace 细节、候选记忆审核、provider raw、本地路径或 signed URL。节点 prompt 优化失败时可以降级为本地规则提示，但必须标明状态。当前验收以 Runtime 静态入口、浏览器体验和 DOM 禁词扫描为准。

Date: 2026-06-11

Owner role: Frontend Interaction Designer + Product Integration Steward

## Scope

Landed the first `apps/studio` frontend package: a no-build vanilla JS infinite-canvas creation graph for AFS prompt-first content production.

The implementation uses mature node-canvas interaction patterns as references, but the product surface is AFS-native. The only user-visible prompt-memory feature is the **Optimize** button beside prompt inputs.

Architecture baseline: `docs/architecture/AFS_STUDIO_FRONTEND_ARCHITECTURE_V1.zh-CN.md`

## Landed

- `apps/studio/`: HTML, dark canvas styles, store, geometry, canvas view/input, node registry, node actions, prompt bar, optimizer, API client, overlay, panels, and presets.
- Canvas shell, pan/zoom, starter cards, node creation, prompt bar, node reference menu, and local script starter flow.
- Prompt optimization popover using `POST /projects/{id}/prompt-optimizations` with local fallback.
- Extension windows: style/motion/effect gallery, toolbox, history assets, shortcuts, and director setup shell.
- Runtime static mount at `/studio/`.
- Send action remains local safe preview and does not start providers.

## Verification

- JavaScript syntax and import integrity passed in the original M1 handoff.
- Browser and full pytest verification are superseded by `AFS-STUDIO-HARD-CLEANUP-001`.

## Boundary

- Provider/MiniMax/Seedance calls are not started.
- No trace, weight, hidden memory candidate, provider state, secret, signed URL, local private material path, provider raw response, or generated media bytes are exposed.
- This is runtime/UI verification only, not human acceptance, business validation, or durable-memory promotion.
