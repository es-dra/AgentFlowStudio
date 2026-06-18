# AFS 深度 UX 与 Runtime 加固 - 2026-06-19

## GFR 启动包

- 身份：Runtime/API 集成、Studio 交互设计、前端产品审查、QA
  Gatekeeper、provider 边界维护。
- 任务类型：深度维护与产品质量加固。
- 分支：`codex/afs-deep-ux-runtime-hardening-20260619`。
- 写入范围：Runtime 安全 health 投影、账号隔离测试、首页第一屏、
  Studio inspector/连线/吸附/生成反馈、前端结构测试、项目维护记录。
- 非目标：不做 SaaS 级账号体系，不接新数据库，不接新 provider，不打开
  video gate，不自动晋升 COS 私有源规则，不持久化 provider raw、signed
  URL、secret 或生成媒体字节。
- Provider gate：默认只做本地 deterministic 验证。LLM/image/vision 的真实
  smoke 只能在现有服务器 Codex 路由已经可用时执行；video 继续关闭，直到
  Kling API 单独配置并授权。
- 证据路线：先本地单测、静态检查和浏览器验证；再合入 GitHub master；最后
  服务器 `/home` 与 `/opt` fast-forward，同步运行重点测试和
  `/health`、`/site/`、`/studio/` 检查。
- COS 反馈路线：仓库只保存执行投影；流程经验只能进入 Company OS 的
  candidate/limited 反馈，不在本轮变成 active rule。

## 已完成切片

1. 内测安全
   - `GET /health` 的 `runtime_root_persisted` 改为根据当前 runtime root
     计算出的安全布尔值，不暴露也不暗示服务器绝对路径。
   - 跨用户访问测试覆盖到 Studio state、image assets、image preview、jobs
     和 artifact manifest，避免多内测用户互相污染项目数据。

2. 首页产品化
   - 第一屏继续从“算法说明页”转为“专业 AI 视频创作入口”。
   - 预览文案更强调具体作品、角色/场景连续性、参考复用和进入 Studio 的
     创作动作。

3. Studio 降噪和操作手感
   - 右侧 inspector 默认只保留下一步行动、本次参考摘要、抽屉入口和折叠
     详情。
   - 持久化连线使用可见 port 中心作为纵向锚点；默认线条更轻，选中节点
     相关连线的方向流光更慢。
   - port magnet 缩小纵向吸附范围，强化左右 port 意图，减少上下误吸。
   - 生成中文字流光放慢，降低警报感。

4. 前端结构治理
   - `main.js` 缩小为启动、事件绑定和渲染编排。
   - 项目创建、切换、列表过滤和启动项目选择迁入
     `studio-project-controller.js`。
   - 新增 `npm run check:studio-js`，对 Studio 和 site JavaScript 做语法检查。

5. 测试清理
   - 增加 safe health projection 与 auth scope 的回归测试。
   - 调整一个 prompt optimizer 测试，避免继续绑定内部重复 retry 次数，而是
     验证“先试主 provider，404 后进入 fallback，最终成功启动 provider
     调用”的用户可见行为。

## 刻意延后

- `node-actions.js`、`runtime_video_routes.py`、`runtime_llm_enhancement.py`
  仍需要继续拆 route、dispatch、payload 和 safe manifest，但当前三端基线正在
  对齐阶段，本轮避免高风险后端大拆。
- Studio 全量乱码治理还没有完成。本轮只处理当前触达的入口和新模块，避免
  大范围文本替换造成 UI 回归。
- 真实 provider 创作质量验收不属于本维护结论。deterministic 验证只能证明
  路由、隔离和安全边界，不能证明创意质量。

## 验证

本地已完成：

```text
npm run check:studio-js
JS syntax check passed: 86 files

Focused Runtime/Studio/Site regression:
69 passed / 1 warning

Full pytest:
507 passed / 527 deselected / 2 warnings

CLI:
python -m apps.cli.main --help passed
python -m apps.cli.main version -> 0.1.0

maintenance_audit:
failed=0, warnings only

git diff --check:
passed
```
