# AFS 深度 UX 与 Runtime 加固收尾 - 2026-06-19

## 基线

- 最终本地/GitHub/服务器提交：`fda2dcafb3a5609deddc9e4ad664b6be060cb053`
- 本轮包含提交：
  - `8b178ac feat(studio): harden beta UX and runtime health`
  - `fda2dca fix(runtime): honor runtime root env in service CLI`
- 实施分支：`codex/afs-deep-ux-runtime-hardening-20260619`
- 收尾审计分支：`codex/afs-closeout-audit-20260619`
- 写入本收尾记录前，GitHub `master`、服务器 `/home/afs-ops/AgentFlowStudio`、服务器 `/opt/afs/AgentFlowStudio` 已对齐到 `fda2dca`。

## 角色审查

### 全栈工程

- Runtime `/health` 的 `runtime_root_persisted` 已改为安全布尔值，不暴露也不暗示服务器绝对路径。
- `runtime-service --runtime-root` 已接入 `AFS_RUNTIME_ROOT`，服务器 systemd 环境能真实传入 `create_runtime_app()`。
- 跨用户隔离测试已覆盖项目列表、Studio state、image assets、image previews、jobs、artifact manifests。
- `main.js` 中的项目生命周期逻辑已迁移到 `studio-project-controller.js`。
- 新增 `npm run check:studio-js`，作为 Studio 和 site JavaScript 的可重复语法检查入口。

### 产品与内测可用性

- 首页第一屏已经从系统解释页转向专业 AI 视频创作入口。
- Studio 顶层导航保留回到 `/site/` 的明确路径。
- Studio 右侧 inspector 默认只保留下一步行动、本次参考摘要、抽屉入口和折叠详情。
- 账号与项目仍是内测范围：邀请码注册、owner 隔离项目，不声明为完整 SaaS 账号体系。

### 前端交互设计

- 画布连线锚点对齐可见 port 位置，线条保持更轻的圆端视觉。
- 选中节点的相关连线使用更慢的方向流光，用于表达上下游关系，而不是警报感。
- port magnet 缩小纵向误吸范围，增强左右侧意图。
- 生成中和优化中的文字使用低干扰流光，并保留 reduced-motion 兼容。

### QA 与发布

- 本地实施切片已完成验证：
  - `npm run check:studio-js` -> 86 个 JavaScript 文件通过。
  - focused Runtime/Studio/site regression -> 69 passed / 1 warning。
  - full default pytest -> 508 passed / 527 deselected / 2 warnings。
  - CLI help/version -> passed；runtime-service help 显示 `AFS_RUNTIME_ROOT`。
  - `tools/maintenance_audit.py` -> failed=0，仅 warnings。
  - `git diff --check` -> passed。
- 浏览器验证覆盖 `/site/`、`/studio/`、项目 hub 入口、回首页、inspector 降噪、console warn/error count=0。
- 服务器 `/home` 与 `/opt` 均已完成重点测试，并在最终 health 检查前完成同步。

### 运维与三端同步

- GitHub `master`、本地 `master`、服务器 `/home`、服务器 `/opt` 已对齐到 `fda2dca`。
- 服务重启后，服务器 `/health` 返回：
  - `status=ready`
  - `runtime_root_persisted=true`
  - `auth_required=true`
  - `llm=true`
  - `image=true`
  - `vision=true`
  - `video=false`
- 由于无 sudo 密码，本轮通过终止当前 `afs-ops` 用户下的 runtime 与 worker 进程，让 systemd 自动拉起新进程完成重启。

### 安全与 provider 边界

- 未打开 video gate。
- 未引入新 provider。
- 未提交 provider raw response、signed URL、secret、本地绝对素材路径或生成媒体字节。
- LLM/image/vision gate 仍取决于服务器配置；video 保持关闭，直到 Kling API 配置完成且获得明确授权。

## 非声明

- 这不是人工创意验收。
- 这不是商业验证。
- 这不是 live video provider 验证。
- 这不是 COS durable rule 晋升。
- 本轮只证明 deterministic 路由、UI、隔离和安全边界，不证明生成媒体质量。

## 剩余风险

- 真实内测验收仍需要人工跑通：注册、登录、创建项目、上传、vision draft、提示词优化、生图、worker 回填、资产确认、修订反馈。
- 后端结构仍有待继续拆分：`runtime_video_routes.py`、`runtime_llm_enhancement.py`、`node-actions.js` 适合作为下一轮低风险切片。
- 视频能力仍受 Kling API 未配置和 video gate 关闭限制。
- 旧 markdown 中历史乱码未做全量重写，避免大范围文档 churn 造成回归风险。

## 下一轮建议

建议下一轮在已部署服务器上做一次受控内测验收：

1. 使用邀请码注册并登录。
2. 创建两个用户，确认项目互相不可见。
3. 创建项目，上传参考图，通过 vision 生成 draft asset card。
4. 触发提示词优化，并通过当前 Codex image 路由提交一次生图。
5. 确认 worker 回填、图片展示、资产确认和下一次调用的上下文复用。
6. 视频只测 preflight/gate 行为；Kling API 配置前不做真实视频调用。

