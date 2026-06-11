# AFS Studio v2 规划：画布小精灵（IP 化身 + 具身 Agent）

日期：2026-06-12
状态：v2 版本规划基线（已确认决策：提案制轻重分级；直接接真实 LLM Agent；形象临时用现成动画库）
上游基线：`AFS_STUDIO_FRONTEND_ARCHITECTURE_V1.zh-CN.md`、`runtime_creative_agent.py`（creative_intent_control_agent_v1）、`prompt-optimizations` 链路

## 0. 一句话定义

小精灵不是装饰物，而是 **Agent 在画布上的可视化身**：它把后台 Agent 的感知、提案、执行、反馈变成用户看得见、可打断、可撤销的具身行为。精灵的每个动作都受 Harness 治理——这正是 COS「Agent 在有规则、有证据、有边界的环境里工作」的产品化表达。

## 1. 已确认决策与两项约束冲突的处理

| 决策 | 内容 | 引出的约束处理 |
|---|---|---|
| 行动模式 | 提案制 + 轻重分级：轻操作直接执行可一键撤销；重操作幽灵预览 → 确认 | **前置依赖：undo/redo 命令栈**（原 M2 欠账，升级为 S0 必做） |
| 智能来源 | 直接接真实 LLM Agent | 与「provider 全关」阶段约束冲突 → LLM 必须走 `AFS_ALLOW_REMOTE_LLM` gate 显式开启；**gate 关闭时精灵自动降级为本地规则大脑**，行为子集可用且 UI 不报错。gate 开启是用户的一次性显式授权动作，写入 runbook |
| 形象资产 | 临时用现成动画库 | 与「无构建零依赖」约束冲突 → 例外评审：**lottie-web 单文件 vendored 进仓库**（不走 CDN、不加构建链），皮肤层做成可替换接口，IP 设计定稿后换正式 Lottie JSON，过渡期内置程序化 SVG 占位精灵保证离线可用 |

## 2. 工作模式组织形式（三模式）

画布从「单一自由编辑」重组为三种工作模式，精灵是模式的载体与切换入口（点击精灵或 dock 模式钮）：

```text
自由模式 Free      现状画布。精灵 idle/陪伴/被动应答，绝不主动干预。
共创模式 Co-pilot  精灵持续感知画布，主动产出建议气泡与提案卡；用户保持主驾。
托管模式 Autopilot 用户给一个目标（如"把这段剧本做成 6 镜头分镜流"），精灵生成
                   任务清单（plan），逐步执行；每步仍按 L0-L3 分级请求确认。
```

- 模式是 store 顶层字段 `workMode`，影响：精灵行为状态机的可用状态集、建议频率上限、感知 tick 频率。
- 默认自由模式；共创/托管的开启本身就是一次用户授权（对应 Harness 的边界声明）。
- 托管模式的任务清单 = 后端返回的 ActionPlan 投影，每步带状态（待确认/执行中/完成/跳过），可整体暂停/终止。

## 3. 动作分级（核心治理规则）

| 级别 | 定义 | 例子 | 确认方式 |
|---|---|---|---|
| L0 | 纯表演，不改任何状态 | 跑动、表情、挥手、指向某节点 | 无 |
| L1 | 轻操作：可逆布局/视图变更 | 整理布局（精灵逐个搬运节点）、对齐、居中视口、展开折叠 | 直接执行 + toast「精灵整理了画布 · 撤销」 |
| L2 | 结构/内容变更 | 建节点、连线、改 prompt、应用优化结果、成组 | 幽灵预览（半透明虚影 + 虚线边）→ 确认/拒绝 |
| L3 | 消耗算力或穿过 provider gate | 触发生成、批量生成、开启 LLM 对话规划 | 显式确认 + gate 状态检查 + ⚡ 成本预告 |

实现保障：LLM 输出**只能**映射到前端 Action Registry 的白名单动作（带 JSON schema 参数校验），未知动作一律丢弃并记 trace；画布内容进入提示词时按数据处理，不作为指令（注入防护）。

## 4. 前端架构（apps/studio/src/sprite/）

```text
sprite/
  sprite-engine.js     行为状态机 + tick loop（活跃 30fps / 空闲 5fps，requestAnimationFrame 节流）
  sprite-body.js       皮肤接口 SpriteSkin { setState, setDirection, setSpeed }
                       皮肤A：程序化 SVG 占位精灵（眨眼/弹跳/拖尾，零依赖）
                       皮肤B：lottie-web vendored + IP 动画 JSON（定稿后替换）
  sprite-motion.js     世界坐标移动：寻路（直线 + 节点矩形避让）、缓动、搬运时与节点同帧位移
  sprite-senses.js     感知：画布快照摘要 + 启发式信号（见 §6），节流采样
  sprite-brain.js      大脑路由：gate 开 → Runtime sprite 接口；gate 关 → 本地规则 planner
  sprite-actions.js    Action Registry：白名单动作表 + schema 校验 + L0-L3 分级执行器
  sprite-proposals.js  提案队列 + 幽灵预览渲染 + 确认/拒绝/全部撤销
  sprite-chat.js       精灵气泡对话（建议气泡 / 用户输入框 / 任务清单卡）
  sprite-config.js     频率上限、静音开关、模式参数
```

- 渲染层：`#sprite-layer` 位于节点层之上、prompt 条之下；精灵在**世界坐标**生活（跟随平移缩放），但体型按 `1/scale` 反缩放并 clamp（0.7x–1.3x），保证远景不消失、近景不巨大。
- 行为状态机：`idle → wander → observe → suggest → propose → execute(carry|tidy|point) → celebrate → sleep`；任何用户 pointerdown 立即打断 execute 以外的状态，精灵让路（避让光标 120px 半径）；执行中可点精灵暂停。
- 精灵不得遮挡交互：移动目标点选择时避开 prompt 条、弹层、dock 的包围盒。
- 关闭权：dock 提供「精灵静音/隐藏」开关（静音=只 L0 表演不建议；隐藏=完全移除 tick）。

## 5. 后端架构（Runtime）

新增两个受 gate 管控的接口（沿用 prompt-optimizations 的 artifact/trace 模式）：

```text
POST /projects/{id}/sprite/plan   输入: work_mode, goal?, canvas_digest(安全摘要), recent_events
                                  输出: ActionPlan { steps: [{action_type, level, params, rationale_zh}], plan_id }
POST /projects/{id}/sprite/chat   输入: message, canvas_digest        输出: reply_zh, suggested_actions[]
```

- `canvas_digest` 是前端生成的安全摘要：节点类型/标题/状态/坐标/连线/未填 prompt 标记；不含本地路径、媒体字节、secret。
- LLM 经 `model_gateway` 调用，受 `AFS_ALLOW_REMOTE_LLM` gate；gate 关闭时接口返回 `mode: "local_rules"` 的确定性 plan（后端规则与前端本地 planner 同源，保证可测试）。
- ActionPlan 是新的 contract 对象，落 `agentflow_sprite_action_plan` artifact + run trace；用户确认/拒绝/撤销作为 feedback signal 回写——接入既有「反馈是 raw evidence」链路，为后续偏好沉淀供料（仍不自动晋升 durable memory）。
- 复用 `runtime_creative_agent.py` 的分层思路：sprite plan agent 同样输出 constraint_layers + candidates + selected，trace 可解释；用户侧只看到中文 rationale。

## 6. 感知信号与对应行为（本地规则集 v1）

| 信号 | 检测 | 精灵行为 |
|---|---|---|
| 布局混乱 | 节点重叠面积比 > 阈值 / 孤儿节点远离主流程 / 边交叉数 | 共创模式：提案 L1「让我帮你整理画布」→ 确认后逐个搬运（分层布局算法 + 12px snap，搬运过程是表演层包装确定性算法） |
| 流程缺口 | 脚本节点完成但无下游 / 图片节点空 prompt / 视频节点缺首帧输入 | 跑到该节点旁指向 + 气泡建议（L0/L2 提案：补节点/连线/填 prompt 模板） |
| 新手停滞 | 空画布无操作 > 15s / 重复无效点击 | 指向 starter 卡或双击位置，演示性引导（纯 L0） |
| 优化机会 | 选中节点 prompt 很短且未用过「优化」 | 气泡提示一次（频率限制：同类建议每会话 ≤ 2 次） |
| 生成完成 | 节点 status → complete | 跑过去 celebrate 小动画（L0），不打断用户 |

频率治理：全局建议节流（默认 ≥ 45s 间隔）、同类去重、用户连续拒绝 2 次则该类建议本会话静默——防骚扰是 IP 好感度的底线。

## 7. 里程碑

| 里程碑 | 内容 | 验收口径 |
|---|---|---|
| S0 前置 | undo/redo 命令栈（history.js，吸收 M2 欠账）；Action Registry + L0-L3 执行器骨架；`#sprite-layer` | 任意 L1 动作可 Ctrl+Z 撤销；registry 拒绝未知动作有测试 |
| S1 表演层 | 精灵本体：状态机、世界坐标移动/避让/反缩放、点击/拖拽交互、SVG 占位皮肤、lottie-web vendored + 皮肤接口 | 60s 观察期内精灵不遮挡任何交互、不掉帧（画布操作输入延迟无感知） |
| S2 提案系统 | 提案队列 UI、幽灵预览、确认/拒绝/撤销、L1 整理布局 + 搬运动画 | 乱序画布 → 提案 → 确认 → 精灵搬运到位 → 一键撤销恢复原状 |
| S3 本地大脑 | sprite-senses 全信号 + 本地规则 planner + 气泡建议 + 频率治理 + 静音/隐藏开关 | gate 全关状态下完整可用；禁词扫描（无 provider/trace 术语外露） |
| S4 LLM 大脑 | Runtime `/sprite/plan` `/sprite/chat` + model_gateway + gate 开启 runbook + 注入防护 + ActionPlan artifact/trace + 对话气泡 | gate 关：local_rules 降级零报错；gate 开：真实 LLM plan 落 trace，白名单外动作 0 执行 |
| S5 模式体系 | 自由/共创/托管三模式、托管任务清单卡、模式切换、浏览器 QA 脚本（tools/studio_sprite_*_browser_qa.py） | 三模式行为边界逐条可复现；gate 关时 provider_request_urls=[] |

建议节奏：S0-S2 一个迭代（纯前端确定性，风险低）；S3 一个迭代；S4 单独迭代（含 gate 授权与安全评审）；S5 收口。

## 8. 风险与边界

- LLM gate：S4 前精灵全部行为确定性可测；开 gate 是用户显式动作并记录；对话与 plan 的 LLM 原始响应只进 trace artifact，不进用户 UI。
- lottie-web 例外：vendored 单文件、版本锁定、退出策略（IP 定稿后若改用程序化皮肤可整体移除）；写入维护账本。
- 性能：精灵 tick 与画布渲染分离；搬运动画走 transform，不触发节点 body 重建。
- 人格与文案：精灵文案全部中文产品语言，禁止出现 rule id/trace/provider/记忆候选等术语；语气规范单独一页（后续与 IP 设计一起定稿）。
- 非声明：本规划与后续实现仍是 structure/runtime verification 路径；精灵的"辅助"不构成 human acceptance；feedback 不自动晋升 durable memory；除显式开启的 LLM gate 外其余 provider 保持关闭。

## 9. 对 COS 的回写价值

精灵把 COS 的抽象对象第一次变成可感知产品：ActionPlan ↔ Execution Router 的可视化、提案确认 ↔ 质量门、撤销/拒绝 ↔ Feedback Signal、托管任务清单 ↔ Run Trace 的用户投影。v2 验证的命题是：**治理不是减损体验，而是 IP 人格的来源**——精灵"先打报告再动手"本身就是品牌性格。
