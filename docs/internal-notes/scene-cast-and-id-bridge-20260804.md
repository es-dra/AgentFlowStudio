# Scene 归属与 ID 映射地基调查（2026-08-04）

状态：调查完成；生产接线已落地（Scene→Cast appearance + 窄 entity↔asset sidecar）；资产需求候选类型仍未做。

## 背景（两个前置缺口）

资产需求候选事实之前，候选闭环缺两块地基：

1. **Scene 归属**：Character / Scene 之间没有「谁在哪场出现」的结构化候选事实  
2. **ID 映射**：候选闭环 `entity_id` / `authoritative_fact_id` 与 Script Core Truth `asset_id` 无正式桥

## 目标 1：Scene ↔ Character 归属

### 现有 Beat 模式（复用）

- `field_path`：`scene[{scene_entity_id}].beats[N].…`
- 仅在 **Scene 证据唯一可定位** 时切 range；重复地点 / 非唯一 evidence → fail-closed
- 只认 range 内显式信号；不跨场推断

### 设计选择：**Scene → Characters（出现关系）**

| 方案 | 结论 |
|---|---|
| Character → Scenes | 弱：人物是全局扁平实体，没有像场标题那样的唯一起点 |
| **Scene → Characters** | **选这个**：与 Beat 同一扇门（unique scene range） |
| 两者都要 | 冗余；需要时再从 Scene→Cast 派生全局索引 |

**field_path 约定：**

```text
entity_kind: character
entity_id:   <与全局 identity.display_name 同一 entity_id>
field_path:  scene[{scene_entity_id}].cast[{order}].appearance
claim.text:  人物 display_name
evidence:    该 Scene range 内的对白 speaker cue，或场内「人物：」名单命中
```

共享全局 `entity_id`，便于后续把「人名确认」与「场内出现」绑到同一 Script Core `char_*`。

### 提取规则（fail-closed）

只认 range 内明确依据：

1. **对白 speaker cue**（与现有 `dialogue_speaker_cue` 同形），且名字已是全局 Character 候选  
2. **场内 `人物：` / `角色：` 名单**（如《归途》分场人物行）命中已知 Character  

不做：跨场推断、「可能在场」、仅凭模糊动作叙述猜人。

同场同人多次对白 → **一条** appearance（首次证据），不是 duplicate-missing。

Scene 归属歧义时：**不产出** cast 候选（与 Beat 一致）。

### 六剧本探针（speaker + 场内人物行）

| 剧本 | 预期 appearance |
|---|---|
| 01 最后的光 | 废弃灯塔→玛雅；灯塔阳台→玛雅 |
| 02 海边的信 | 邮局→苏晴/老王；礁石→苏晴/林悦；房间→苏晴 |
| 03 归途 | 火车站→陈浩；老屋→陈浩/林秀 |
| 04 旧照片 | 阁楼→周明；厨房→周明/母亲 |
| 05 陌生来电 | 无 Character/Scene → 0 |
| 06 夜班 | 地下通道→沈岚/阿拓；货运站台→阿拓 |

## 目标 2：ID 映射

### 两套体系（平行，无正式桥）

| | Script Core Truth | Candidate ledger |
|---|---|---|
| 存储 | `script_core_truth/truth_state.json` | `candidate_facts/ledger.json` |
| ID | `char_*` / `scene_*` / `prop_*`（hash） | `entity_id` + `auth_*` |
| 粒度 | 整个 asset | **字段级** fact |
| 确认 | confidence≥0.82 可自动 confirmed | **必须** human / deterministic |
| 修订 | 同 revision 内 preservation_key 保 id | 换 revision → invalidate 权威 |

**今日无代码**把 `asset_id` 写进 ledger，或把 `authoritative_fact_id` 写进 truth_state。

### 假设冲突（不宜做全量双向同步）

- 自动确认 vs 人工确认  
- 整 asset 原地 edit vs 每次 promote 新 `auth_*`  
- `character_0_X` 顺序敏感 vs `char_{hash}` 证据摘要敏感  
- Beat / Profile 在 Core Truth **没有**对应 asset 类型  

### 正式但窄的映射（今天做）

不把两套生命周期焊死。只在 **人工确认 Character/Scene 的 display_name/name 之后**：

1. 在当前 revision 的 Script Core assets 里按 **display_name + asset_type** 查找  
2. 找到 → 写入 sidecar 绑定行（含 `entity_id`、`authoritative_fact_id`、`core_asset_id`、`revision_id`）  
3. 找不到 → **保持未绑定**（不造 asset、不猜）  
4. 提供双向查询：`entity_id → asset_id`，`asset_id → entity_id`（仅 active 绑定）  
5. 同 `(entity_id, field_path, revision)` supersede → 绑定指向新 `authoritative_fact_id`  
6. revision 变更 → 旧绑定标 stale（与权威 invalidate 对齐）

**明确不做：** asset edit 回写候选、自动 confirm 造权威、Beat/Profile 强行映射、模糊同名匹配。

## 今天实际做 / 不做

**做**

1. Scene→Character `appearance` 候选事实（走现有 accept/edit/reject/promote/supersede/Graph）  
2. 窄 sidecar `entity_asset_bindings` + 确认时绑定 + 双向查询  

**不做**

- 资产需求 / 镜头表达 / 制作可行性候选类型  
- ContinuityStateVersion 耦合  
- 新功能开关（复用现有 confirmation loop）  
- 全生命周期双向同步  

## 风险自检清单

- 重复地点：与 Beat 同门，歧义时不产出 cast  
- 伪造 evidence：appearance 的 edit_confirm 走 exact source span  
- 未类型化：`field_path` / sidecar schema 固定；不写进 Continuity / 不改 Core Truth schema  
- ID 脆弱映射：无 match 则 unbound，禁止按 slug 瞎绑  
