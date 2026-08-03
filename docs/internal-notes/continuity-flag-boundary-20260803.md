# Continuity Flag 边界说明（2026-08-03）

状态：设计/边界调查；**未**接入 `apps/api` candidate-fact 生产路径，
**未**修改 Episode `ContinuityStateVersion` 或 continuity 服务。

## 结论

| 问题 | 判断 |
|---|---|
| 跟 `ContinuityStateVersion` 会不会做成第二套？ | **边界清楚，不会。** 不同层、不同存储、不同服务对象。 |
| 现在能不能像 Beat facet 一样“标签抽取就接生产”？ | **不能诚实做到。** 文本连续性矛盾是跨场比较 + 语言理解，不是单行标签读取。 |
| 本次交付 | 本说明 + `draft_continuity_flag_schema_20260803.py`；不接假阳性检测器。 |

这符合退出条件：系统边界可分清，但检测难度接近/超过 Beat 情绪主观性，
宁可交站得住脚的说明，也不要勉强实现。

## 两个系统的关系

```text
Script understanding (proposed)
  ScriptRevision text
    -> CandidateFact ledger
    -> continuity_flag   # 问题标记，将来

Episode production (existing, untouched)
  ContinuityStateVersion
    -> ShotVersion.continuity_refs
    -> AssetCandidate / SelectedVersion

continuity_flag -.-> optional future read-only hint only -.-> ContinuityStateVersion
  (never promote flag into continuity_state; never share storage)
```

### `ContinuityStateVersion`（已存在，本次不动）

- 合同：`docs/architecture/AFS_EPISODE_PRODUCTION_FACT_CONTRACT.md`
- 定义：`apps/api/runtime_episode_domain_contract.py`
  - `subject_type` ∈ character / scene / prop
  - `identity_baseline` / `temporary_state` / `prohibited_changes`
  - `approved_asset_selection_refs`
- 行为：`apps/api/runtime_episode_continuity_service.py` propose / apply / undo，
  只替换 Shot 上的精确 `continuity_refs`
- 存储：Episode aggregate JSON（`episode_aggregates/...`），**不是**
  `projects/{id}/candidate_facts/ledger.json`
- **不读剧本正文**找逻辑矛盾；服务对象是生成链路的视觉/造型锁定

### §7.2 文本连续性（尚未存在于生产）

- 服务对象：剧本诊断——时间 / 空间 / 人物 / 服化道 / 事件在**文字上**是否自洽
- 产物形态：`entity_kind="continuity_flag"` —— **发现的连续性问题标记**，
  不是“续接状态事实”
- 一天设计已明示：不要把 ContinuityStateVersion 当假故事模型
  （`draft_script_understanding_character_schema_20260801.py`）
- 一天风险报告点名“多套重叠实现”
  （`script-flow-risks-20260801.md`）；把文本矛盾塞进 ContinuityStateVersion
  或另起平行生产存储，正是重蹈覆辙

### 怎么避免重复

1. **不同名字**：生产侧 `continuity_state`；理解侧 `continuity_flag`
2. **不同存储**：flag 只进 candidate-fact ledger（将来）；永不写入
   `ProductionProjectAggregate.continuity_states`
3. **不修改** Continuity 服务 / 合同 / Shot ref 图
4. **若将来关联**：最多只读引用（例如 `related_scene_ids` 指向已确认 Scene）；
   **禁止**从 flag promote 成 ContinuityStateVersion
5. **不把** Asset Bible / UI 里的 `continuity_states` 标签当成同一概念

## 为什么现在不硬接生产检测器

Beat / ScriptProfile / ScriptFormatProfile 的成功模式是：
**显式标签 → ClaimedText → 确认闭环**。连续性矛盾不是这个形状。

1. **真实剧本几乎没有** `连续性矛盾：` / `时间矛盾：` 之类标签。
   标签抽取对 6 份测试剧本只会永远 0 flags——看起来“诚实”，但只测了空管道，
   测不到检测能力。
2. **“清晨紧接深夜且无跳跃说明”** 在中文分场剧本里几乎是常态：换场标题本身
   就是时间跳跃，剧本很少写“时间跳跃：”。按字面做正则会**系统性假阳性**。
3. **“下雨 → 地面干燥”** 是跨场动作/状态推理，需要语言理解。当前生产 Scene
   候选几乎只有地点名，**没有**已权威化的 `time_of_day` / props / events
   ClaimedText 可供确定性交叉比对（Scene 全 facet 仍在
   `draft_scene_schema_20260802.py`，未整包进 candidate pipeline）。
4. 强行接一个“差不多能抓雨/干”的启发式，会重演一天批评过的问题：
   表面结构 PASS、语义站不住。

因此：**复用 ClaimedText / 状态机可以，但“发现矛盾”这一步现在没有站得住的
确定性输入。**

## 六剧本预期（不跑假检测凑数）

这 6 份是精心写的短剧本，预期**没有**可确定性证明的字面连续性矛盾。
本次**不**实现扫描器去“确认 0”，以免把空实现包装成验证通过。

| 剧本 | 预期真实文本矛盾 | 说明 |
|---|---|---|
| 01 最后的光 | 0 | 干净行业格式短片 |
| 02 海边的信 | 0 | 干净行业格式短片 |
| 03 归途 | 0 | 带人物标签，无跨场逻辑打架 |
| 04 旧照片 | 0 | 混合格式，仍无故意矛盾 |
| 05 陌生来电 | 0 | 信息缺失样本，≠ 连续性矛盾 |
| 06 夜班 | 0 | 对抗的是抽取/格式，不是跨场矛盾 |

人为构造的雨/干、打碎/完好对抗样本，应留给**以后有 Scene facet 证据之后**
的确定性交叉检查器，而不是现在用正则硬凑。

## 以后接生产的前置条件（缺一不可）

1. **Scene（及必要时 Prop / 事件）facet** 进入 candidate pipeline，且
   time / prop / event 带可核对 evidence
2. **确定性交叉检查器**：只在**两侧都有 evidenced ClaimedText** 且存在字面
   互斥对时产出 flag；叙事留白（缺时间说明）→ 不报
3. 人工构造对抗样本验证真阳性；6 份干净剧本验证 0 假阳性
4. 更广覆盖走 **`model_inferred` + 人工确认**（更接近 §7.3 诊断链），
   不冒充确定性抽取

## 风险自检

- 命名：`continuity_flag` vs `continuity_state` 故意不同，避免 UI/API 混用
- 证据：flag 必须**至少两段**互相矛盾的原文 span；单侧“看起来可疑”一律不产出
- 不复用 Continuity edit / apply 命令路径
- 不把 Asset Bible 的 UI `continuity_states` 当成同一概念
- 本次 `git` 范围仅 `docs/internal-notes/`；`apps/api` Continuity 相关文件零改动

## 相关草稿

- Schema：`docs/internal-notes/draft_continuity_flag_schema_20260803.py`
- Scene facets（前置依赖）：`docs/internal-notes/draft_scene_schema_20260802.py`
- 一天 Character 设计中的 Continuity 边界说明：
  `docs/internal-notes/draft_script_understanding_character_schema_20260801.py`
