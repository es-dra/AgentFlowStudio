# AFS 全栈产品架构 v0.1

状态：执行基线，不代表公开发布、商业验收或 Provider 媒体验收。

## 1. 产品对象与不漂移边界

AFS 是面向内容制作的 Creator-first、AI 原生生产系统。它验证 AOS 的持续生产范式，但不等于 AOS，也不是把内部编排节点直接暴露给创作者的节点工具。

产品闭环固定为：

```text
项目 / 剧本
  -> 分镜
  -> Asset Bible
  -> 资产图
  -> 镜头关键画面
  -> 视频候选
  -> 人工审核
  -> 局部返工
  -> 拼接
  -> 产品内播放与交付
```

以下能力是平台内核，前端重构、数据迁移和服务器优化都不得绕开：

1. `ProductionGraph` 是项目业务状态的唯一权威；数据库事件流是它的持久化日志，不是第二套业务真相。
2. 剧本、场景、镜头、资产、候选、任务、审核和交付使用稳定实体引用；不得用数组下标或页面状态充当身份。
3. 候选不可覆盖，采用必须显式选择；每次变化保留输入、输出、版本、任务、审核和费用谱系。
4. 任何远程生成先经过权限、Provider gate、预算、幂等和当前版本检查；`submission_unknown` 不允许盲目重发。
5. 智能体可以提出、推进和恢复工作，但不可替用户完成关键采用、费用扩大和发布决策。
6. 变更必须先计算影响范围；返工以受影响的镜头、资产或交付段为边界，不能默认全量重跑。
7. 内部 Gate、Manifest、Truth、ID、诊断和原始调度状态默认隐藏，仅在制作详情、证据或管理面渐进披露。

## 2. 产品信息架构

### 2.1 顶层入口

| 路由 | 用户目标 | 说明 |
|---|---|---|
| `/login` | 登录或接受邀请 | 不承载项目业务状态 |
| `/projects` | 创建、导入、选择项目 | 展示项目结果和恢复摘要，不展示内部任务海洋 |
| `/studio/?project=...&surface=...&entity=...` | 完成一部作品 | 主产品；默认 `surface=canvas` |
| `/library` | 复用组织资产 | P4；资产仍通过项目引用进入 ProductionGraph |
| `/settings/team` | 团队与权限 | P4；Creator 与管理员职责分离 |
| `/settings/models` | 模型渠道、预算和 gate | P4；不向前端返回 secret |
| `/settings/billing` | 费用与配额 | P4；费用事实来自后端账本 |
| `/admin` | 运维、迁移和审计 | 独立管理面，不污染 Creator 工作区 |

### 2.2 Studio 唯一产品壳

```text
StudioProductShell
├─ AuthProjectBoundary
├─ ProjectHeader
│  ├─ ProjectSwitcher
│  ├─ SaveAndSyncState
│  ├─ ProjectOutcomeSummary
│  └─ GlobalActions
├─ SurfaceNavigation
│  ├─ Canvas（默认）
│  ├─ Script
│  ├─ Storyboard
│  ├─ Asset Bible
│  ├─ 生成审核
│  └─ 合成交付
├─ SurfaceOutlet
├─ AgentWorkspace（壳层常驻兄弟节点）
└─ ProgressivePanels
   ├─ 制作详情
   ├─ 谱系与证据
   └─ 管理 / 诊断
```

同一项目、同一 Graph 版本、同一智能体会话在六个工作面之间切换。切换工作面不能卸载智能体工作区，也不能复制项目状态。

### 2.3 桌面布局

```text
┌──────────────────── ProjectHeader · 56 ────────────────────┐
├──────────── SurfaceNavigation · 44 ──────────────┬─────────┤
│                                                  │ Agent   │
│                 SurfaceOutlet                    │ 360–420 │
│                                                  │ px      │
│                                                  │         │
├──────────────────────────────────────────────────┴─────────┤
│ ProgressivePanels / task and evidence drawer when opened   │
└────────────────────────────────────────────────────────────┘
```

- 内容工作面优先占用宽度；右侧智能体工作区固定但可折叠为窄栏。
- 详情面板不常驻挤压主工作区，使用就近 inspector 或底部 drawer。
- 全局 Header 只保留项目切换、同步/恢复状态、播放/导出入口和账户菜单。
- 颜色、状态和徽标只表达创作者可行动的信息；技术诊断使用独立层级。

## 3. 六个工作面的职责与组件分配

| 工作面 | 主区域 | 左侧/上方导航 | 就近详情 | 主要动作 | 后端配合 |
|---|---|---|---|---|---|
| Canvas | 可缩放 ProductionGraph 关系画布 | 场景/镜头定位、缩放、筛选 | 选中实体 inspector | 创建意图、连接引用、查看影响、发起生成 | Graph 只读投影、命令预览、影响计算 |
| Script | 结构化剧本编辑器 | 场次目录、角色过滤 | 场次/台词属性 | 导入、编辑、确认结构、比较版本 | Script 命令、版本冲突、结构验证 |
| Storyboard | 按场次/镜头排序的分镜带 | 场次导航、节奏摘要 | 镜头卡 inspector | 拆镜、改时长、调整镜头意图、批量选择 | Shot reducer、时长规则、依赖影响 |
| Asset Bible | 人物/场景/道具资产库 | 类型、状态、复用过滤 | 资产版本与引用 | 确认身份、生成候选、采用、退役 | Asset commands、谱系、唯一引用 |
| 生成审核 | 大媒体预览 + 候选队列 | 待审核/失败/不确定/已采用 | 对比、质量和影响摘要 | 采用、拒绝、记录失败、局部返工 | Admission policy、显式选择、rework plan |
| 合成交付 | 播放器 + 时间线 + 交付检查 | 版本、阻塞项、输出规格 | 片段/音轨/字幕 inspector | 拼接、冻结版本、播放、导出 | Assembly task、delivery version、Range media |

### 3.1 Canvas

Canvas 负责关系和上下文，不承担所有细节编辑。

```text
CanvasSurface
├─ GraphViewport
│  ├─ EntityNode
│  ├─ RelationEdge
│  ├─ SelectionHalo
│  └─ ImpactOverlay
├─ CanvasLocator
├─ ContextActionBar
└─ EntityInspector
```

节点显示名称、媒体预览、创作状态和一到两个可靠动作。Provider 名称、内部 task id、manifest 字段和 gate 原因不进入节点正文。

### 3.2 Script

```text
ScriptSurface
├─ SceneOutline
├─ StructuredScriptEditor
├─ VersionCompare
└─ ScriptInspector
```

文本编辑与 Graph 更新通过命令预览完成。预览展示“会改变什么、影响哪些镜头”，确认后才生成事件。

### 3.3 Storyboard

```text
StoryboardSurface
├─ SceneRail
├─ ShotSequence
│  └─ ShotCard
├─ RhythmSummary
└─ ShotInspector
```

Storyboard 是时间顺序工作面，不复制 Canvas。镜头排序、时长和拍摄意图是第一层；技术提示词和模型参数进入详情。

### 3.4 Asset Bible

```text
AssetBibleSurface
├─ AssetFilters
├─ AssetGrid
│  └─ AssetCard
├─ IdentityCoverage
└─ AssetInspector
```

资产卡区分“资产身份”“候选媒体”“当前采用版本”。单张媒体图不能同时充当三者。

### 3.5 生成审核

```text
ReviewSurface
├─ ReviewQueue
├─ CandidateStage
├─ CandidateComparison
├─ DecisionBar
└─ ReworkPreview
```

默认选择待审核项，不默认采用第一候选。固定审核命令可在 Graph 前进后继续执行；批次延续和派发命令必须重新验证精确来源版本。

### 3.6 合成交付

```text
DeliverySurface
├─ DeliveryPlayer
├─ AssemblyTimeline
├─ DeliveryChecklist
├─ VersionHistory
└─ ExportPanel
```

产品内播放读取不可变交付版本。导出不会覆盖上一个版本；发现局部问题时从交付段反查镜头和候选，形成限定返工计划。

## 4. 智能体工作区

智能体工作区的会话身份为：

```text
project_id + stable_entity_ref + conversation_id
```

它不是普通聊天侧栏，而是项目命令协作面：

```text
AgentWorkspace
├─ ContextHeader
├─ Conversation
├─ ProposalCard
│  ├─ change_summary
│  ├─ affected_entities
│  ├─ cost_and_gate_summary
│  └─ Apply / Revise / Dismiss
├─ ActiveTaskSummary
├─ RecoveryPrompt
└─ Composer
```

核心交互为：

```text
选择实体 -> 提出变更 -> 影响预览 -> 用户确认 -> 持久命令
         -> 后台任务 -> 候选/失败证据 -> 审核 -> 可撤销或局部返工
```

智能体只提交与 UI 相同的命令信封，不直接写 Graph 文件、数据库表或对象存储。

## 5. 前端工程边界

目标技术栈是 React + TypeScript。迁移期间旧 Canvas 通过 adapter 嵌入新壳，先保持真实项目可用，再逐面替换。

建议包结构：

```text
apps/studio-web/
├─ app/
│  ├─ router/
│  ├─ providers/
│  └─ StudioProductShell.tsx
├─ surfaces/
│  ├─ canvas/
│  ├─ script/
│  ├─ storyboard/
│  ├─ asset-bible/
│  ├─ review/
│  └─ delivery/
├─ features/
│  ├─ agent-workspace/
│  ├─ commands/
│  ├─ tasks/
│  ├─ lineage/
│  ├─ media/
│  └─ recovery/
├─ entities/
├─ shared/
│  ├─ api/
│  ├─ ui/
│  ├─ state/
│  └─ tokens/
└─ legacy/canvas-adapter/
```

状态所有权：

| 状态 | 权威位置 |
|---|---|
| 项目、Graph、实体、版本、候选、采用、任务、审核、谱系、费用、交付 | 服务器 |
| 当前项目、工作面、实体 deep link | URL |
| 查询缓存 | 前端 query cache，以 `project_id + project_version + surface` 为键 |
| 缩放、滚动、筛选、面板宽度、未发送输入、焦点 | 本地 UI state |
| 业务采用、任务成功、Graph 版本 | 禁止写入 localStorage 作为真相 |

响应式：

- `>=1200px`：完整三段布局，Agent 360–420px。
- `761–1199px`：Agent 作为可固定的右侧层，保留会话。
- `<=760px`：Agent 为底部 sheet；六个工作面用横向导航和“更多”，Canvas 可只读但不能跳到另一套移动产品。

## 6. 后端形态

先采用模块化 FastAPI 单体 + PostgreSQL + 对象存储 + 独立 durable worker。先解决事务边界、恢复和性能，再根据负载证据拆微服务。

```text
apps/backend/
├─ app.py
├─ bff/
│  ├─ studio_routes.py
│  ├─ studio_projection.py
│  ├─ event_stream.py
│  └─ safe_media_proxy.py
├─ commands/
│  ├─ envelope.py
│  ├─ dispatcher.py
│  ├─ receipts.py
│  └─ handlers/
├─ domain/
│  ├─ production_graph/
│  ├─ episode/
│  └─ production_control/
├─ persistence/
│  ├─ unit_of_work.py
│  ├─ project_stream.py
│  ├─ repositories/
│  ├─ projections/
│  └─ migrations/
├─ tasks/
│  ├─ scheduler.py
│  ├─ worker.py
│  ├─ leases.py
│  ├─ recovery.py
│  └─ state_machine.py
├─ providers/
├─ artifacts/
├─ identity/
├─ admin/
├─ migration/
└─ compatibility/
```

### 6.1 Studio BFF

```http
GET  /api/v1/workspaces
POST /api/v1/projects
GET  /api/v1/projects/{project_id}/studio?surface=...
GET  /api/v1/projects/{project_id}/events?after_sequence=...
GET  /api/v1/projects/{project_id}/tasks
POST /api/v1/projects/{project_id}/commands/preview
POST /api/v1/projects/{project_id}/commands
POST /api/v1/projects/{project_id}/tasks/{task_id}/actions
GET  /api/v1/projects/{project_id}/artifacts/{artifact_id}/content
GET  /api/v1/projects/{project_id}/deliveries/{delivery_id}/play
```

工作面返回统一信封：

```json
{
  "project_id": "project-id",
  "project_version": 33,
  "graph_digest": "sha256",
  "surface": "review",
  "entities": [],
  "allowed_actions": [],
  "task_summaries": [],
  "review_queue": [],
  "cost_summary": {},
  "recovery_summary": {}
}
```

BFF 不写业务状态，只读取投影并提交命令。

### 6.2 命令与事务

命令信封必须包含：

```text
type
expected_project_version
idempotency_key
correlation_id / causation_id
exact_entity_refs
required_capability
provider_gate_ref / budget_authorization_ref
payload / payload_digest
```

一次命令事务：

```text
认证与 RBAC
  -> BEGIN
  -> 幂等 receipt replay/conflict
  -> 锁 project_stream
  -> 校验版本、引用、规则、gate、预算
  -> reducer 生成事件
  -> 写 event + projection + receipt
  -> 如需后台工作，同时写 task + cost reservation + outbox
  -> COMMIT
  -> worker 才能执行网络调用
```

同一成功命令只增加一次 `project_version`；该命令产生的多个事件共享同一版本，并按连续 `event_sequence` 排序。

### 6.3 持久任务与 Provider

worker 通过租约认领任务，初期使用 PostgreSQL `FOR UPDATE SKIP LOCKED`。Provider 派发状态至少包含：

```text
prepared
network_started
submitted_confirmed
submission_unknown
completed
failed_terminal
reconcile_required
```

API 进程不直接持有图片/视频执行所有权，不在请求中同步 submit/poll，不用进程内集合证明任务已提交。

## 7. 数据与对象存储

核心表域：

```text
identity: organizations, users, memberships, teams, project_grants, sessions
truth: project_streams, project_events, command_receipts, outbox
graph: entity_versions, relations, entity_heads, projection_offsets
tasks: tasks, task_dependencies, task_attempts, worker_leases, provider_dispatches
media: artifacts, objects, artifact_inputs, provenance
review: review_decisions, candidate_selections, delivery_versions
cost: provider_services, routes, gates, prices, reservations, costs
audit: audit_events, security_events, migration_runs
```

媒体先进入 quarantine，完成 MIME、大小、来源主机、digest 和安全检查后进入不可变对象存储。数据库保存对象引用、digest、谱系和状态，不保存媒体字节或 signed URL 作为长期事实。

## 8. 服务器性能与运行拓扑

目标运行形态：

```text
reverse proxy
├─ afs-api           无 Provider 长任务
├─ afs-worker-llm    独立并发、gate、预算
├─ afs-worker-image  独立并发、gate、预算
├─ afs-worker-video  独立并发、gate、预算
├─ PostgreSQL
├─ S3 / MinIO
└─ metrics / traces / redacted logs
```

数据库迁移前的确定性优化顺序：

1. GET 项目列表不注册 artifact、不重写全局 index。
2. 认证用户在单请求内复用，`last_seen_at` 限频写入。
3. 删除无条件 AnyIO monkeypatch，恢复共享有界线程池和背压。
4. 建立 project-scoped job 索引，避免每项目扫描全部 jobs。
5. 将 Provider submit/poll 移出 API，改为 durable outbox。
6. 收敛 systemd 配置来源、轮换凭据、设置资源隔离和有限重启策略。

目标 SLO（需 staging 关闭 Provider 后验证）：

| 指标 | 目标 |
|---|---|
| 非 Provider 读 API | p95 <= 250ms，p99 <= 750ms |
| 本地命令 preview/confirm | p95 <= 500ms |
| durable enqueue | p95 <= 300ms |
| worker pickup | p95 <= 2s |
| 崩溃恢复 / reconcile | <= 60s |
| API 错误率 | < 0.5% |
| 重复 Provider dispatch | 0 |
| committed metadata/outbox | RPO 0 |
| 整体恢复 | RTO <= 15min |

负载和故障注入只在 8791/staging 执行，不对 8790 或受保护的 8792 压测。

## 9. 保留、重构、合并、退役

| 分类 | 内容 |
|---|---|
| 保留 | Graph validator/reducer、稳定实体引用、显式候选选择、媒体安全投影、现有真实项目、幂等与恢复证据 |
| 重构 | 旧静态 Studio 到 React 壳；文件存储到事务事件流；进程内 executor 到 durable worker；散落路由到模块域 |
| 合并 | Canvas/Storyboard/Bible/Review/Delivery 到同一 Studio 壳；Episode/Production Control 作为 Graph 的规则和约束 |
| 退役 | `/studio/review.html`、独立 episode workspace、长期双写、页面本地业务真相、数组下标身份、直接批处理 Provider 路由 |
| 删除条件 | 新路径真实项目 parity、浏览器 QA、evaluator、CI 和回滚证据全部通过后，才删除旧路径 |

## 10. 迁移路线与垂直交付

每个项目具有单一权威模式：

```text
legacy_file -> graph_v1 -> postgres_v2
```

迁移过程：

1. 冻结单项目写入和 Provider 派发。
2. 快照 manifest、Graph、Episode、Control、任务、artifact、账本和 outbox。
3. 先导入 Graph，再把 Episode/Control 归并为约束和投影。
4. 导入任务、远端身份、未知派发和费用证据。
5. 比较实体数、关系、版本、digest、候选采用和谱系；冲突即停止。
6. 原子切换 `authority_mode`。
7. 旧文件只读保留为恢复证据，不做长期双写。

垂直切片顺序：

1. **Foundation**：统一 Studio BFF 只读投影 + 项目列表热路径优化。
2. **Shell**：React/TypeScript 产品壳、六工作面导航、常驻 Agent、旧 Canvas adapter。
3. **Authoring**：Script -> Storyboard -> Asset Bible，真实项目无 Provider parity。
4. **Review**：关键画面/视频候选审核、显式采用、局部返工。
5. **Delivery**：拼接、版本冻结、产品内播放、导出。
6. **Platform**：PostgreSQL、对象存储、durable worker、RBAC、团队、模型、费用、管理。
7. **Commercial hardening**：性能、安全、备份、升级、监控和恢复演练。

每条切片必须同时包含：

```text
schema/contract
backend command or projection
frontend working flow
real-project no-provider evidence
focused tests
browser QA
independent evaluator
CI
release gate
```

文档、页面数量、Agent 数量和测试数量都不能替代完整的创作者结果。
