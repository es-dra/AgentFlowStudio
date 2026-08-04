# Beat 级资产需求调查结论（2026-08-04）

状态：**不做生产接线**。与 ContinuityFlag / 镜头表达同类：诚实评估后暂缓。

## 结论

**现在不要做 Beat 级别资产需求。**

- Scene→Beat「继承整场 cast/prop」= 换包装，没有新信息，还会误导下游
- 真正的 Beat 归属需要新的候选事实 + 确认闭环，成本接近再做一层 Scene cast/prop，而六剧本几乎没有 Beat 标记可验

## Beat 现在记了什么

生产链路（`runtime_script_improved_extraction.py` → `runtime_candidate_confirmation.py`）里 Beat 只有：

- `scene[X].beats[N].boundary` — 显式 `节拍N` / `BEAT N`
- 标签 facets：`conflict` / `turn` / `info_release` / `emotion_shift.*`

**没有** Beat 范围的人物/道具归属事实。facet 文本是叙述摘要，不是结构化「本拍用了哪些资产」；文中偶尔出现人名/道具名也不能当归属证据。

资产需求视图（`runtime_asset_requirements.py`）只从已确认的 **Scene cast / Scene prop** 投影，`scope_kind="scene"`。

```text
Scene range
  ├─ cast appearance facts ──┐
  ├─ props name facts ───────┼─→ Scene asset_requirements
  └─ beat boundary + facets ─┘   （无归属边）
```

## 证据

| 语料 | 显式 Beat | 对 Beat 资产需求的含义 |
|---|---|---|
| 六剧本 `01`–`06` | **0** | 做了也会全空 |
| `LABELED_BEAT_CONTROL` | 每场 1 拍 | 可在 Beat range 复跑 cast/prop 提取器，但「一场一拍」时结果≈整场列表 |
| 合成「火车站两拍」 | 2 拍 | 「等待」→ 陈浩+照片；「离开」→ cue 提取为空，而叙述仍写陈浩/照片 |

最后一行说明：**不能把 Scene 列表套到每个 Beat**。继承会把照片/陈浩安到「离开」上，却没有该拍范围内的 cue 证据——违反 fail-closed。

## 继承有没有意义？

**没有。** `Beat → parent Scene → Scene asset_requirements` 只是重贴标签，回答不了「这一拍具体用到什么」，还会让分镜/节拍规划误以为粒度已细化。

## 若要做「真·Beat 归属」需要什么

不是只读再聚合，而是：

1. 在已确认/已切出的 Beat source range 内，用现有封闭规则重跑 cast / prop 提取
2. 产出新候选事实，例如 `scene[X].beats[N].cast[M].appearance`、`scene[X].beats[N].props[M].name`，走确认闭环（不能从 Scene 事实自动晋升）
3. 派生视图增加 `scope_kind="beat"`，只读上述权威事实

工作量≈再做一层归属（确认 UX、Graph metadata、绑定/supersede、**带显式 Beat 的测试语料**）。六剧本验不了。召回会低于 Scene（Beat 标记稀少；道具提取本就偏保守；纯叙述出场继续 fail-closed——合成「离开」为空是规则正确，不是该用继承去「修」）。

## 为何暂缓

- 主评测六剧本无 Beat → 功能会「测过但永远空」
- 真需求依赖剧本普遍带显式 Beat，或下游明确要求「经确认的逐拍资产清单」并接受新候选类型成本（见 `beat-schema-findings-20260803.md`）
- Scene 级资产需求已回答当前问题：确认后「这场需要哪些已知人物/道具」
- 继承有害；完整 Beat 归属当前性价比不足

## 何时再开

满足至少一条再议：

1. 生产剧本常规带显式 Beat 标签，或
2. 下游（如镜头规划）明确要经确认的逐拍资产列表，并接受新归属候选 + 确认成本

本次：**仅本笔记，不改 `apps/api` 生产代码。**
