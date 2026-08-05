# 缺失证据评测范围裁剪备忘（2026-08-05）

| 项 | 值 |
|---|---|
| 状态 | 范围备忘（非完整设计稿；无金标 JSON；无代码） |
| 基线 tip | `master` @ `de05374d` 一带（analysis-candidates / #231） |
| 相关调查 | 别名工作之后的「缺失证据」现状盘点 |
| 原则 | 模型/规则只提案；缺失必须可诚实表达；未经确认不能成为权威事实 |

---

## 1. 范围声明

**本次评测协议只覆盖两类已在当前 master 产品契约里落地的缺失表达：**

1. **槽级 missing** — 候选 payload 上的 `missing_slots ∈ {named_characters, main_scenes}`（整类提不到）。
2. **关系级 missing（#231）** — `scene_cast` / `scene_core_prop` 关系上的 `status=missing` 且 `evidence_status=missing`（场景块内对已有成员做精确名/alias 命中失败）。

并计划用 **1–2 条「有名无戏份」金标草案**（见 §3）专门检验关系级行为：人物已是 analysis asset，但在指定场景块内不应出现可确认的出演证据。

**其他一切缺失表达方式，本次明确不覆盖**（理由见 §2，不是空泛延期）。

---

## 2. 明确排除项与理由

### 2.1 Profile 五维 present / missing（主题 / 类型 / 受众 / 叙事目标 / 风格）

| | |
|---|---|
| **排除** | 整套 ScriptProfile facet 级 `present \| missing` 评测 |
| **理由** | 该模型与确认纪律验证过，但是在 **week / #229 捐赠线**（CandidateFact + confirmation ledger）上；当前 master 的 analysis-candidates **没有** 对应可审阅 Profile 实体闭环。候选上虽有可选 `style` / `genre` / `tone` 字符串，但不是 facet 证据状态机，也没有「缺一维就不能 accept」的门禁。在 master 上评 Profile missing，等于用未接线的契约考生产行为——假阳性/假阴性都无法归因。 |
| **不是** | 「这次不想做」；而是 **评测对象在 tip 上不存在可观测的权威语义**。 |

### 2.2 Beat 情绪三元组等 facet 级缺失

| | |
|---|---|
| **排除** | Beat 边界、tension / turn / info / emotion_shift 等 facet missing 评测 |
| **理由** | 同上：本地验证过「无显式 Beat 标记则整类 missing」「emotion 三元组缺一则整 facet missing」；但 master 投影仍为 `dynamic_beats: reserved_not_implemented`，beats 未进入 asset/relationship 审阅。无确认门、无 Graph 写入路径，则「该不该标 missing」没有产品真值可对齐。 |
| **不是** | 否定 week 经验；经验保留给「是否迁入 analysis-candidates」的后续决策（§4）。 |

### 2.3 「有人但叫不出名字」（匿名实体 + name_missing）

| | |
|---|---|
| **排除** | 匿名出场、只有「女人/来电者」等、需要 `name_missing` 的金标与协议 |
| **理由（schema 硬限制，评测绕不过）** | 当前 `CandidateCharacter` / `CandidateMainScene` 要求 `evidence_spans` **min_length=1**，且人物以 `display_name` 为中心。槽级只能表达「整类 named_characters 为空」，**不能**表达「存在一个未命名角色实体、姓名槽位 missing」。要支持该类用例，必须先改契约（至少：允许无 display_name 的占位实体，或放宽/重定义 evidence 约束，并定义确认门禁）——这是 **schema / 产品语义变更**，不是金标措辞能补上的洞。 |
| **记录** | 见 §4.1；本次只记账，不评测、不设计补丁方案。 |

### 2.4 本次也不顺带覆盖的相邻项

| 项 | 为何不进本备忘范围 |
|---|---|
| 别名链接质量 | 已有独立评测集；缺失协议不重复考身份聚类 |
| 间接叙事提及导致的「假 missing」 | 属于召回/理解问题；会污染「诚实 missing」归因 |
| 长剧本性能 | 与缺失语义正交 |
| `scene_core_prop` 深度用例 | 关系 missing 语义与 cast 同源，本备忘用 `scene_cast` 钉「有名无戏份」；道具可后续对称加 1 条，**不阻塞**本次范围冻结 |

---

## 3. 对齐已有机制（不发明新词汇）

评测观察与断言必须直接复用现有字段语义，**禁止**引入第三套如 `partial_missing` / `soft_absent` 等新枚举（除非将来单独做 schema 变更提案）。

### 3.1 槽级：`missing_slots`

| 字段 | 已有语义（评测应对齐） |
|---|---|
| `missing_slots` 含 `named_characters` | 确定性/结构化候选认为：**没有任何**可源文本支撑的命名人物候选 |
| `missing_slots` 含 `main_scenes` | 同上，对主场景 |
| 同时可有 `extraction_notes` | 人类可读说明；**不以 notes 字符串为权威断言** |

断言方向（协议级，非正式 JSON）：

- 故意写空的「无姓名、无场景标签」短文 → 应出现对应 `missing_slots`；**不得**为了填槽而捏造专名/地点后当候选。
- 已抽出非空 `named_characters` 时 → **不应**再带 `named_characters` ∈ `missing_slots`（互斥纪律）。

### 3.2 关系级：`scene_cast` / `scene_core_prop`

| 字段 | 已有语义（评测应对齐） |
|---|---|
| `status=missing` | 该「场景 × 成员」关系当前**无**可确认出演/归属证据 |
| `evidence_status=missing` | 与上一致；confirm 路径拒绝（`scene_ownership_evidence_missing`） |
| `evidence_spans=[]` | 无精确命中 |
| `evidence_policy` | `exact_member_label_or_alias_within_confirmed_scene_span`（块内精确标签或 alias） |

断言方向：

- 成员在剧本**其他位置**有名、已形成 character asset，但在**目标场景块**内无其 display_name/alias 字面命中 → 该 `scene_cast` **必须**为 missing；不得用「剧情上应该在场」脑补 spans。
- missing 关系 **不得** 经 confirm 进入 Production Graph；reject 或保持 missing 均可按现 API，但 confirm 必须失败。

### 3.3 与资产级 `evidence_status` 的边界

Character/Scene 资产上的 `evidence_status` 枚举是 `extracted_from_text | model_inferred | conflicting`，**不含 missing**。  
「有名无戏份」测的是 **关系** missing，不是把人物资产标成 missing。备忘要求金标与报告写清这一层，避免评测写错对象。

---

## 4. 「有名无戏份」金标用例草案（1–2 条）

以下仅为**草案文本 + 期望**，非正式 `gold_cases.json`。实现评测时再机器化。

### M1 — 人物列表有名，第二场块内无字面出场（核心）

**意图：** 验证关系级 missing：资产存在 ≠ 每场都有出演证据。

**原文草案：**

```text
标题：只在名单里

第一场 - 内景 - 会议室 - 日

人物：陈默、李薇

陈默
纪要发我一份。

李薇
好。

第二场 - 内景 - 地下车库 - 夜

李薇独自走向车门，掏出车钥匙。引擎声在空旷车位间回响。

李薇
（自语）
还是自己回去吧。
```

**前置（评测编排假设，对齐现流程）：**

1. 对 revision 跑 `analysis-candidates/extract`（或等价提交），得到人物资产 `陈默`、`李薇` 与场景 `会议室`、`地下车库`（名称以实际抽取为准，金标用稳定 display_name 对齐）。
2. 确认相关人物/场景资产（若 ownership extract 要求端点已确认——以 #231 测试为准）。
3. 跑 `analysis-relationships/extract`。

**期望（关系级）：**

| 关系（逻辑） | 期望 |
|---|---|
| 会议室 × 陈默 | `status=candidate`（或等价有证据），spans 非空 |
| 会议室 × 李薇 | 有证据 |
| **地下车库 × 陈默** | **`status=missing` 且 `evidence_status=missing`，spans=[]** |
| 地下车库 × 李薇 | 有证据（「李薇」出现在第二场块内） |

**禁止行为：**

- 因「第一场两人开会、第二场李薇说还是自己回去」而**推断**陈默在车库 → 给车库×陈默写 spans 或标成可 confirm 的 candidate。
- 对车库×陈默执行 confirm 成功。

**槽级：** 本条 **不** 期望 `named_characters` / `main_scenes` ∈ `missing_slots`（两类都非空）。

---

### M2 — 槽级 missing 对照（整类提不到）

**意图：** 钉住槽级，避免关系级用例把「整类缺失」挤出协议视野；并与「有名无戏份」对照。

**原文草案：**

```text
标题：陌生来电（槽级对照）

第一场

深夜，一个女人坐在昏暗的房间里，手机屏幕的光照着她的脸。
屏幕上显示一个陌生号码。她犹豫很久，接通电话。

女人
（压低声音）
喂？

电话那头只有呼吸声。电话挂断了。
```

（可复用 week《陌生来电》精神；此处独立成短对照，不依赖未合入的文件路径。）

**期望（槽级）：**

- `named_characters` ∈ `missing_slots`（「女人」为泛称，确定性路径不应产出专名候选）。
- 若亦无合格场景 heading/地点标签 → `main_scenes` ∈ `missing_slots`（以实际确定性规则为准；本草案故意偏散文，**期望至少人物槽 missing**）。
- **不得** 把「女人」晋升为可确认命名人物资产以「填满」槽位。

**关系级：** 本条不要求 ownership 用例（没有稳定命名人物资产时，有名无戏份命题不成立）。

---

## 5. 后续问题清单（不在本次解决；供排优先级）

### 5.1 「有人但叫不出名字」要不要动 schema？

- **现象：** 叙事需要「未具名角色」占位，但当前候选人物强制有名 + 至少一段 evidence span。
- **若要处理，大致会动到：**  
  - `CandidateCharacter`（或后继）是否允许 `display_name` 空 / 占位类型；  
  - `evidence_spans` 的 min_length 与「姓名证据 vs 出场证据」是否拆分；  
  - 确认门：无名实体能否 confirm、Graph 节点标签是什么；  
  - Studio 审阅文案（避免把占位当成已命名事实）。
- **建议态度：** 先当 **明确的产品/契约债** 记账；在未改 schema 前，**不要**用评测协议假装已支持。

### 5.2 Profile / Beat 的 missing 经验要不要迁到 analysis-candidates？

- **已有价值：** facet 级 present/missing、缺证据不可 accept、只能 `edit_confirm`——与老板「复杂/部分缺失」高度相关。
- **迁移前提（矩阵已暗示）：** 每类要有真实下游消费者；挂到 **单一** 审阅骨架，禁止再开 CandidateFact 第二账本。
- **决策问题：**  
  - 先迁 Profile 五维，还是等媒体/计划侧真正消费 theme/genre？  
  - Beat 是否仍因边界难题继续整类 missing，只迁「显式标签才 present」？  
  - missing facet 在 analysis-candidates 上是做成 asset 字段、独立 relationship，还是 candidate 级 structured slots？
- **建议态度：** 与本备忘的槽级+关系级评测 **解耦排期**；本备忘跑通后，再单独开「Profile/Beat 迁入范围」备忘，避免一次评测协议吞三层本体。

### 5.3 可选的小扩展（仍非本次必做）

- 为 `scene_core_prop` 加一条对称的「道具已建、场内无字面」金标。  
- 计分侧是否需要类似别名的 **coverage** 指标（例如：期望 missing 的关系有多少被系统标出）——留给正式设计稿，本备忘不定义公式。

---

## 6. 本备忘不交付什么

- 不写 `gold_cases.json` / 计分脚本 / 生产代码。  
- 不改 `apps/api` schema。  
- 不推分支、不开 PR。  
- 不把 week 的 Profile/Beat 实现「假设为已在 master」。

---

## 7. 冻结结论（一句话）

**缺失证据评测 v0 只考：槽级 `missing_slots` + 关系级 ownership `missing`，并用 M1/M2 草案钉「有名无戏份」与「整类没有」；Profile/Beat facet 与匿名 name_missing 因契约未就绪或硬限制，排除在外并记入 §5。**
