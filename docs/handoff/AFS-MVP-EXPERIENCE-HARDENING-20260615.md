# AFS MVP 体验加固交接 - 2026-06-15

## 概要

本轮是第一版 MVP 的内测体验加固切片，来源是最新 Studio 体验反馈和
Claude 计划复核。目标不是扩展 provider 调用，而是把现有链路的可靠性、
可见性和边界提示补齐，让后续人工验收和视频局部重生成测试有更稳定的
证据入口。

本轮已完成：

- Runtime `/health` 增加 Studio 静态资源 readiness 和各 provider gate
  的布尔状态投影，不暴露 provider 配置路径、secret 或本地私有路径。
- 新增内部测试启动脚本，可显式打开 LLM/image/video gate，同时强制保持
  ASR 关闭。
- Studio 节点上新增固定资产携带链提示，最多显示有限数量，避免多资产
  时撑爆节点。
- 把“提示词点名了固定资产但未连接”的检查抽成共享的
  `asset-reference-inspector`，让优化面板和提交前 fail-closed 行为一致。
- 视频生成状态新增本地取消边界说明。`cancelled_local_only` 会显示为独立
  的本地取消状态，不再被误读为成功或普通失败。
- 完成的图像/视频节点可以通过 `/feedback` 记录结构化质量反馈，包括身份
  相似度、服饰一致性、场景连续性、文字/水印、目标修改成功度和漂移备注。
- Claude 收口复核后，补了三处边界加固：`/feedback` 服务端白名单与脱敏、
  内部测试脚本强制关闭 external download、前端只读取 preview URL 的存在性
  并只保存 `safe_preview_ref`。

## 边界

- 本轮没有进行任何 live provider 调用。
- ASR 和 external download 仍保持关闭。
- 当前视频 revision 仍是 best-effort/experimental。MVP 已能表达“只改这一
  部分，其他尽量不变”的意图和评分入口，但这不等于已经证明 Kling 或其他
  provider 具备真正的局部视频编辑能力。
- `/feedback` 写入的是 raw evidence，不写长期记忆、不写 Company KB、不写
  provider raw response、signed URL、本地路径或媒体字节。

## 验证

已通过的 focused 验证：

```text
pytest tests/test_api_runtime_service.py tests/test_studio_internal_launcher.py tests/test_web_studio_static.py -q
-> 37 passed, 1 warning

pytest tests/test_api_runtime_video_generations.py tests/test_api_runtime_video_revisions.py tests/test_kling_video_runtime_polling.py -q
-> 13 passed, 1 warning

pytest tests/test_api_runtime_keyframe_reference_assets.py tests/test_api_runtime_visual_assets.py tests/test_studio_asset_context_browser_qa_tool.py -q
-> 12 passed, 1 warning

Studio JS node --check -> passed
```

最终验证：

```text
pytest -q -> 417 passed, 527 deselected, 2 warnings
pytest -m legacy -q -> 527 passed, 417 deselected, 1 warning
maintenance_audit.py -> failed=0, warnings only
git diff --check -> exit 0
```

Runtime smoke：

- 使用当前 worktree 在隔离端口启动 Runtime。
- `/health` 返回 `status=ready`，Studio static `status=ready`。
- `llm/image/video/asr/external_download` 全部为 `false`。

Browser 说明：

- in-app Browser 访问 localhost Studio URL 时触发 Browser URL policy block，
  标签页显示 `This page crashed`。
- 该结果已经记录到外部 evidence root。
- 按 Browser 安全策略，没有使用其它浏览器 surface 绕过该阻断。

外部证据根目录：

```text
D:\Projects\AgentFlowStudio-evidence\20260615-afs-mvp-experience-hardening\
```

## 后续

- 如果需要浏览器人工式验收，需要由用户控制的浏览器或后续可用的 Browser
  环境重新跑 `/studio/`。
- 视频局部重生成的下一步应明确 provider 能力：若支持 true V2V/masked/
  temporal edit，则接对应路径；若只支持 I2V revision attempt，则必须明确
  标注 best-effort，并用 A/B drift scoring 记录偏差。
- 本轮新增的结构化质量反馈应作为下一轮视频 revision 与 I2I optimizer 加固
  的证据输入，不能自动晋升为 durable memory。
