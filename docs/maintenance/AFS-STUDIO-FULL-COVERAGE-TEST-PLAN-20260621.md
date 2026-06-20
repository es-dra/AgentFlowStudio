# AFS Studio 全量内测计划 - 2026-06-21

## 目标

用自动化和操作者视角测试替代第一轮真人内测，尽量从多角色、多链路、多故障状态里提前发现问题。发现非阻断问题时先记录并继续跑完整链路，之后集中修复和复测。

本轮覆盖：

- `/studio/` 画布、侧栏、节点、prompt bar、团团、素材库、作品库。
- Runtime Service 给 Studio 暴露的 API 边界。
- 非 video 模型需求：提示词优化、团团回复、参考图上传、图片/关键帧任务、可用的视觉检查通路。
- 本地、GitHub、服务器 `/home`、服务器 `/opt` 的三端同步和部署健康。

本轮不覆盖：

- 真实 video 生成。
- ASR gate、external download gate。
- 真人验收、商业验证、长期公司记忆晋升。
- secret、provider raw response、signed URL、本地私有素材字节、invite code、session token。

## 角色矩阵

| 角色 | 测试重点 |
|---|---|
| 新创作者 | 能否进入 Studio，创建节点，上传参考图，看到结果或明确失败状态。 |
| 继续创作者 | 刷新后节点、素材、画布、保存状态是否恢复。 |
| 创意导演 | 提示词优化是否保持主体、资产、场景和导演意图。 |
| 素材管理员 | 素材能否预览、详情查看、右键删除、从侧栏消失，并同步到 Runtime。 |
| QA 审查者 | 进度、失败、重试、反馈入口是否真实且不误导。 |
| 发布操作者 | 三端状态、Runtime health、公开边缘、provider gate 是否明确。 |
| 隐私安全审查者 | 前端和 API payload 是否不暴露 secret、原始 provider 响应、签名地址、本地路径。 |
| 等待中的用户 | 慢请求时是否有等待标识、文案轮换、输入焦点不丢、按钮状态可理解。 |
| 小屏用户 | 侧栏、prompt bar、团团、节点、菜单在小视口不横向溢出。 |
| 故障恢复用户 | gate 关闭、provider 配置不可用、旧 running job、长轮询是否能恢复或给出明确状态。 |

## 测试层次

1. 本地基线
   - `pytest`
   - `npm run check:studio-js`
   - `tools/maintenance_audit.py`
   - CLI help/version
   - `git diff --check`

2. Runtime/API 契约
   - health 和 provider gate 投影。
   - project 创建、Studio state 保存/恢复。
   - job progress 的 pending/running/terminal 状态。
   - 上传图片的 safe preview URL。
   - 图片素材删除和项目隔离。

3. 浏览器角色链路
   - 页面启动和控制台无错误。
   - 创建图片节点、上传参考图、固定素材。
   - 提示词优化、连接建议、上下文携带。
   - 图片 gate 关闭时的阻断状态。
   - 素材库预览、详情、右键删除。
   - 团团等待光流、等待文案轮换、回复完成。
   - 刷新恢复和小视口布局。

4. 服务器和三端
   - 本地分支、origin、服务器 `/home`、服务器 `/opt` 是否一致。
   - Runtime health 和 safe provider gate 字段。
   - 公开 `/studio/` 边缘是否被 Basic Auth 或其他层挡住。
   - 当前 Studio 静态资源是否可访问。
   - video gate 保持关闭。

## 严重级别

| 级别 | 定义 | 处理 |
|---|---|---|
| S0 | Studio 无法启动、无法保存、无法认证，或核心非 video 模型链路不可用。 | 立即停止当前链路并修复。 |
| S1 | 内测主链路可走但存在数据丢失、错误阻断、误导状态、关键按钮不可点。 | 当前链路能继续则先跑完，然后集中修复。 |
| S2 | 影响体验、布局、等待感、错误提示或测试稳定性。 | 批量修复并复测。 |
| S3 | 小文案、低风险样式、后续增强。 | 记录，能低风险处理则修。 |

## 完成标准

- 本地完整 pytest 通过。
- Studio JS 检查通过。
- 维护审计没有 failed。
- 多角色浏览器 QA 通过并留下 JSON/截图证据。
- 三端和服务器健康检查完成。
- 公开边缘状态被明确分类。
- 本轮发现的 S0/S1/S2 均已修复或记录为外部阻塞。
- video 生成未被触发，video gate 未打开。

