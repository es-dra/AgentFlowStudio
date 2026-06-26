# AFS Studio 生成与资产引用修复 - 2026-06-26

## 任务级别

Deep。

本轮修复内测反馈中影响 `/studio/` 当前 MVP 主链路的问题：剧本导入格式、提示词/图片/视频生成进度、素材库参考图绑定、以及外部中转 API 的 image provider 诊断口径。

## 写入范围

- `apps/studio/src/`
  - 剧本导入解析。
  - 生成进度百分比显示。
  - 素材库“用作参考”到当前节点的实际绑定。
  - 当前 Image2/Seedance 模型服务 ID 的产品口径。
- `apps/api/`
  - keyframe/image generation 对外部 relay provider 的错误分类与参考图处理。
  - Runtime request 默认 image service。
- `agentflow_studio/model_gateway/`
  - API relay image/reference 的安全诊断。
- `configs/providers.example.json`
  - 示例 provider 配置投影到外部 image relay。
- `tests/`
  - 覆盖上述 contract 的静态/单元回归。
- `TASK_TRACKER.md`、`DEVLOG.md`
  - 记录本轮修复与验证边界。

## 非目标

- 不触发真实 LLM/image/video provider 调用。
- 不写入 provider secret、signed URL、媒体字节、客户材料或 COS/GFR 源头私有内容。
- 不删除历史 `codex_image_handoff` 代码和测试；它降级为 legacy/tested code，本轮只清理当前产品默认和示例配置中的 `codex_image` 口径。
- 不做 SaaS 化、计费、多人并发存储迁移或人工创意质量验收。

## Provider Gate

本轮本地验证默认不开 provider gate。若后续需要 live smoke，必须按能力单独授权：

- image: `AFS_ALLOW_REMOTE_IMAGE=true`
- video: `AFS_ALLOW_REMOTE_VIDEO=true`
- LLM: `AFS_ALLOW_REMOTE_LLM=true`

授权 image 不代表授权 video、LLM、ASR 或 external download。

## 验证命令

```text
npm run check:studio-js
python -m pytest tests/test_web_studio_prompt_script_static.py tests/test_web_studio_assets_generation_static.py tests/test_web_studio_frontend_wave.py tests/test_api_runtime_keyframe_reference_assets.py tests/test_provider_adapter_registry.py tests/test_api_runtime_creative_agent_keyframes.py -q
python -m apps.cli.main --help
python -m apps.cli.main version
python tools/maintenance_audit.py
git diff --check
```

## Handoff

本轮完成后将把验证结果写入 `DEVLOG.md` 和 `TASK_TRACKER.md`。如需上线，还需要在部署环境把 ignored provider config 中 image 服务 ID 同步为 `image_relay`，或保留兼容 alias 后再重启 Runtime。

## 维护备注

- `apps/studio/src/script-breakdown.js` 在加入 Office 解析后超过 500 行，已拆出 `apps/studio/src/script-file-import.js`，当前保留 301-500 warning 级别。
- `apps/api/runtime_keyframes.py` 是既有超 500 行 Runtime 生成编排文件。本轮只做 provider relay 诊断和参考图路径局部修复，不在同一变更中拆分生成编排；后续应按 `provider resolution / prompt assembly / dispatch writeback` 三段拆分。
- `apps/studio/src/panels/drawer-asset-actions.js` 进入 301-500 warning。本轮新增绑定 contract 后先保留同文件，后续若继续增加资产动作，应拆出 `drawer-image-reference-actions.js`。

## 验证结果

```text
npm run check:studio-js -> passed, 122 files
python -m json.tool configs/providers.example.json -> passed
python -m py_compile runtime/provider touched files -> passed
role-based local user simulation -> script import, asset reuse, progress, provider route passed
python -m pytest tests/test_web_studio_prompt_script_static.py tests/test_web_studio_assets_generation_static.py tests/test_web_studio_frontend_wave.py tests/test_api_runtime_keyframe_reference_assets.py tests/test_provider_adapter_registry.py tests/test_api_runtime_creative_agent_keyframes.py -q -> 104 passed
python -m apps.cli.main --help -> passed
python -m apps.cli.main version -> 0.1.0
python tools/maintenance_audit.py -> failed=0, warnings only
git diff --check -> passed
python -m pytest -> 637 passed / 3 failed / 520 deselected / 1 warning
```

全量 pytest 的 3 个失败不是本轮生成链路改动：

- `tests/test_agentflow_knowledgebase.py` 与 `tests/test_agentflow_knowledgebase_coverage.py` 依赖当前 Linux 环境不存在的 Windows 源头知识库路径 `D:/Learning materials/.../knowledgebase`。
- `tests/test_repository_retention_review.py` 期望 `manual_review_required_count == 0`，当前实际为 27；明细来自未跟踪的 `ops/sub2api/*`，不是本轮新增文件。
