# 开发日志

状态：当前会话短日志。历史长叙事不作为当前任务入口，旧记录已归档到 `docs/archive/`、`docs/frontend_integration/` 和对应 handoff。

## 当前证据入口

- 当前任务账本：`TASK_TRACKER.md`。
- LibTV 画布提示词优化集成：`docs/handoff/AFS-LIBTV-NODE-PROMPT-OPTIMIZER-INTEGRATION-001.md`。
- 提示词记忆闭环：`docs/handoff/AFS-PROMPT-MEMORY-LOOP-MVP-001.md`。
- 专业知识库与 Prompt Assembly：`docs/handoff/AFS-PROFESSIONAL-KNOWLEDGEBASE-PROMPT-ASSEMBLY-001.md`。
- MVP 联合验收：`docs/handoff/AFS-MVP-PROMPT-OPTIMIZER-SUPPORT-001.md`、`docs/frontend_integration/AFS_MVP_PROMPT_OPTIMIZER_JOINT_ACCEPTANCE.zh-CN.md`。
- Web LibTV 画布主线：`docs/handoff/AFS-WEB-LIBTV-CANVAS-PROMPT-ONLY-006.md`。

## 2026-06-11 - Professional Knowledgebase Prompt Assembly 001

- 新增双副本专业影视提示词知识库：公司源头副本在 `10-Startup/70-Projects/AgentFlow-Studio/knowledgebase`，仓库执行副本在 `agentflow/knowledge`。
- 仓库执行副本包含 registry、schema、示例和 12 个规则域，覆盖导演、摄影、灯光、美术、分镜、短视频脚本、音频、角色一致性、关键帧连续性、视频运动、2D 导演台和负面约束。
- Runtime `prompt-optimizations` 已从占位规则切换到 deterministic rule loader、规则选择、中文槽位抽取、上下文优先级、冲突抑制、分段 prompt 输出、trace 和 safe manifest。
- 边界：provider 默认关闭；不提交 secret、signed URL、本地私有素材、provider 原始响应、生成媒体字节、durable memory 晋升或 Company OS active rule。

## 2026-06-11 - LibTV Node Prompt Optimizer Integration 001

- 集成 Web LibTV 画布和 Runtime `prompt-optimizations`：节点内 `优化` 优先调用 Runtime API，失败时才使用本地规则 fallback。
- 新增 `prompt-optimizer-runtime.js`，负责节点类型映射、安全 artifact refs、请求组装、Runtime 响应归一化和 fallback 包装。
- 用户界面只展示原始 prompt、优化后 prompt、分段结果、替换、追加、复制和应用到节点；不展示知识库权重、trace、候选记忆审核或 provider 配置。
- 验证边界：浏览器 QA 记录 Runtime optimizer requests，provider requests 为 0。

## 2026-06-11 - LibTV Canvas Prompt-Only UI 006

- 普通用户 Web 路径重置为 LibTV 风格画布：深色首页、全屏点阵画布、底部 dock、左侧画布/资产抽屉、添加节点、工具箱、素材、历史浮层、节点内控制和导演台覆盖编辑器。
- 提示词记忆闭环保留在后台；前端只在 prompt 输入位暴露 `优化` 入口。
- 普通路径不展示项目记忆页、生成能力门、任务中心、诊断、provider/runtime 文案、trace、权重或候选记忆确认。
- 浏览器 QA 已覆盖 canvas header、add-node、prompt optimizer、toolbox，provider/MiniMax 保持关闭。

## 2026-06-11 - LibTV Canvas Interactions 006A-006L

- 画布从静态布局推进到真实节点编辑器：空画布平移、双击添加节点、拖拽节点、动态 Bezier 边、可见端口、磁吸连接、成功反馈、长按/框选多选、批量复制/对齐/删除、关系聚焦、mini-map、fit view、center selected、reset viewport。
- 默认 8 个 workflow 节点已可打开对应 LibTV 风格节点面板，并支持上游/当前/下游上下文 chip 导航。
- 边选择工具条支持居中端点和断开自定义连接。
- 验证：相关 browser QA 覆盖 canvas interactions、relation focus、canvas viewport、workflow node open、director interactions 和 prompt optimizer；未触发 provider 请求。

## 2026-06-11 - LibTV Node Controls and Mobile 006M-006R

- 节点参数 chips 已变成真实本地控制：text/script attempts、image modes/specs、video modes/specs/toggles、audio target/mode/voice/spec。
- 打开节点、上下游跳转、返回画布具备 enter、chain、return 空间反馈。
- 移动端和 tablet 已增加专用样式：压缩 topbar、底部 dock、上下文栏、参数网格、video-merge 和 Director Desk 布局，节点详情保持可滚动。
- Canvas safety 增强：拖拽中的连线实时跟随，拖拽结束会按 topbar 和 bottom dock 安全区域校正视口，QA 以几何不重叠判断底部 dock 安全。
- Video node `运镜` 入口已成为本地控制面板，含运镜、强度、主体动作、节奏、动画预览和 live summary。
- 最近验证：full pytest 通过 `890 passed`；`maintenance_audit` 曾只剩长记录 warning；`git diff --check` 仅有 Windows CRLF 提示；provider/MiniMax 保持关闭。

## 历史记录归档

- 2026-06-09 到 2026-06-10 的 Web foundation / RC / provider-prep 长记录不再作为当前入口；详见 `docs/archive/DEVLOG-2026-06-09-web-foundation-archive.md`、`docs/frontend_integration/` 和对应 handoff。

## 非声明

- 当前自动化验证不是 human acceptance。
- 当前本地 deterministic / browser QA 不是 business validation。
- provider smoke 尚未执行，后续必须按能力 gate 单独授权。
- 本轮没有把项目证据晋升为 durable memory 或 Company OS active rule。
