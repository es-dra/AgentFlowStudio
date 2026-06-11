# AFS Studio MVP M1.5 Core Loops 001

中文摘要：本文记录 Studio 核心交互闭环的阶段交接，包括节点 prompt 优化、应用到节点、局部预览、历史和导演台入口。当前边界是不扩大到完整视频生成、不暴露后台记忆管理、不展示 provider raw 和本地路径。后续真实模型接入应先从图片/关键帧 gate 开始，视频继续关闭。

Date: 2026-06-11

Owner role: Frontend Interaction Designer + Runtime/API Integrator

## Summary

This slice made the Studio canvas behave like a real node editor instead of a static UI shell, while keeping prompt-memory assembly hidden behind the Runtime Service.

## Landed

- User-facing prompt optimization output: six Chinese sections for `人物 / 场景 / 镜头 / 灯光 / 运动 / 负面约束`.
- `PromptOptimizationRequest.node_parameters` flow from node controls into backend prompt assembly input.
- Real output-to-input Bezier connection sessions with pending edge, target lock, success pulse, and upstream/downstream focus.
- Node-local actions: generate, duplicate, collapse, more menu, rename, retry, set reference, and delete.
- SVG icon system replacing emoji UI.
- Prompt bar collision positioning and anchored optimizer popover behavior.

## Verification

- `node --check` and import integrity passed in the original handoff.
- Focused Runtime prompt tests and full Studio-only verification are superseded by `AFS-STUDIO-HARD-CLEANUP-001`.

## Boundary

- Provider calls remain closed.
- Send remains local safe preview.
- No hidden memory confirmation UI.
- No trace, weights, provider status, raw provider response, signed URL, local private material path, or media bytes appear in ordinary user UI.
