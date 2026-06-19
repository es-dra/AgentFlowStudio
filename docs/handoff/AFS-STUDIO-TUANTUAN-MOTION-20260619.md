# AFS Studio 团团连续运动层交接记录 - 2026-06-19

## 当前状态

- 分支：`codex/studio-sprite-character-redesign-20260619`
- 最新提交：`e1ae84e polish(studio): add lossless TuanTuan motion layer`
- 上一个团团提交：`9c06dbe polish(studio): make TuanTuan sprite multi-pose`
- 分支起点：`aa74120 feat(beta): record human review decisions`
- 当前本地分支与 `origin/codex/studio-sprite-character-redesign-20260619` 已对齐到 `e1ae84e`。
- 已有草稿 PR #91。由于本机 GitHub connector token 过期，且没有可用的 `gh` CLI，本轮没有自动更新 PR 描述。

## 本轮范围

这一切片的目标是让团团不再只是姿态贴图切换，而是在保留参考图形象和高清 PNG 资产的前提下，增加连续、无损、低侵入的动态交互。

- `apps/studio/src/sprite-character.js`
  - 负责团团姿态资产注册表。
  - 渲染 `idle`、`happy`、`curious`、`thinking`、`surprised`、`sleepy`、`working`、`celebrate` 八个姿态。
  - 将临时姿态、闲置姿态轮换从 widget 外壳中拆出。

- `apps/studio/src/sprite-motion.js`
  - 负责鼠标关注、悬停、拖拽、工作中、成功、失败等连续运动。
  - 通过 CSS 变量驱动位移、倾斜、抬起、挤压和阴影变化。
  - 运动变量写入真实的 `.afs-sprite-avatar`，不是只写到 `#sprite-root`，避免被头像层默认变量覆盖。
  - 支持 `prefers-reduced-motion`，用户系统要求降低动态效果时会降级。

- `apps/studio/src/sprite-widget.js`
  - 保留小精灵入口、聊天面板、设置面板、LLM 边界和拖拽入口。
  - 将角色资产和运动行为委托给独立模块。

- `apps/studio/styles/studio-sprite-avatar-mascot.css`
  - 使用运动变量控制团团整体渲染和阴影。
  - 移除旧的只靠 keyframes 的 working/celebrate 动效，改由 JS spring motion layer 统一驱动。

## 验证记录

本地验证命令：

```text
npm run check:studio-js
=> JS syntax check passed: 96 files

.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_static.py tests\test_web_studio_sprite_static.py tests\test_api_runtime_sprite.py -q
=> 16 passed, 1 个既有 Starlette/httpx warning

.\.venv\Scripts\python.exe tools\maintenance_audit.py
=> failed=0，只有既有 warning

git diff --check
=> passed
```

Chrome 浏览器烟测目标为 `/studio/?project=tuantuan-motion-smoke`：

- 8 个团团姿态资产全部加载。
- 每个姿态资产尺寸为 `410x515`。
- 初始状态为 `pose=idle`、`motion=idle`。
- 鼠标靠近后，`shift`、`tilt`、stage transform、shadow scale 均发生变化。
- 悬停状态进入 `pose=happy`、`motion=hover`。
- 拖拽状态进入 `pose=happy`、`motion=drag`，computed transform 中可见抬起和挤压。
- 浏览器 console warning/error 数量为 0。
- 截图证据：`runs/tuantuan-sprite-motion-smoke-20260619.png`。

## 边界

- 没有修改 Runtime API shape。
- 没有修改 provider gate。
- 没有发起 provider 调用。
- 没有打开 video gate。
- 没有写入 provider raw response、signed URL、secret、本地私有素材字节或 Company OS 私有源内容。
- 这属于前端 runtime verification，不是 human acceptance，也不是 business validation。
- 当前是轻量连续运动层，不是完整骨骼绑定。真正 Live2D / Spine 级团团需要分层源文件、序列帧或专门动画资产管线。

## 合并与部署 Gate

在用户确认团团视觉/IP 方向前，不要将该分支合并到 `master`，也不要部署到 `/opt`。

如果用户确认可进入主线，建议流程：

1. GitHub auth 可用后更新草稿 PR #91 描述。
2. 合并该分支到本地 `master`。
3. 推送 `origin/master`。
4. SSH 到 `afs-bwg-ops`。
5. fast-forward `/home/afs-ops/AgentFlowStudio`。
6. 运行前端与静态重点检查。
7. 同步 `/opt/afs/AgentFlowStudio`。
8. 重启 `afs-runtime`。
9. 验证 `/health`、`/site/`、`/studio/` 和已部署团团运动烟测。

## 剩余风险

- 当前是整体角色的无损连续运动，还没有单独驱动耳朵、眼睛、尾巴、灵感芽等局部部件。
- 如果要继续提升“真实小精灵”的感觉，需要补充分层 IP 资产包或小型 runtime rig 格式。
- 仍需要用户做视觉接受确认后再进入主线。
