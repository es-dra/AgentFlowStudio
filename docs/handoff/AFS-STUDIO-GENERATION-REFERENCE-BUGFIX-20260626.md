# AFS Studio 生成引用与 Relay 修复交接 - 2026-06-26

## 范围

本轮修复 `/studio/` 内测反馈的生成链路问题：

- 剧本导入支持文本、Markdown、Word、PPT。
- 图片/视频生成节点显示百分比进度。
- 提示词优化、剧本扩写、分镜拆解写入百分比状态。
- 资产库“用作参考”对当前节点产生真实生成输入。
- 当前图片 provider 口径从 `codex_image` 切到外部 `image_relay`。
- Runtime keyframe/image relay 错误拆分为可诊断的安全 block。

## 部署注意

部署到 `/opt/afs/AgentFlowStudio` 后，需要同步 ignored provider config：

```text
image service id: image_relay
provider: api_relay
capability: image
required gate: AFS_ALLOW_REMOTE_IMAGE
```

Runtime 保留 `image_relay -> codex_image` legacy alias，用于过渡旧本地配置；但当前产品默认、示例配置、前端模型和 request schema 都已使用 `image_relay`。

## 验证

```text
npm run check:studio-js -> passed for 122 files
python -m json.tool configs/providers.example.json -> passed
python -m py_compile runtime/provider touched files -> passed
role-based local user simulation -> script import, asset reuse, progress, provider route passed
focused pytest set -> 104 passed
python -m apps.cli.main --help -> passed
python -m apps.cli.main version -> 0.1.0
python tools/maintenance_audit.py -> failed=0, warnings only
git diff --check -> passed
python -m pytest -> 637 passed / 3 failed / 520 deselected / 1 warning
```

全量 pytest 剩余失败是当前环境/工作树状态，不是本轮生成链路回归：

- Linux 环境没有 `D:/Learning materials/.../knowledgebase`。
- 未跟踪 `ops/sub2api/*` 触发 repository retention manual review count。

## 边界

- 未触发真实 LLM/image/video/ASR provider 调用。
- 未读取或写入 provider secret、signed URL、provider raw response、生成媒体字节、客户素材或 Company OS 私有源头内容。
- 本轮验证不是 human acceptance、creative quality acceptance、business validation 或 durable memory promotion。
