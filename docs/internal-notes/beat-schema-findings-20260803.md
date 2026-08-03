# Beat Schema 设计与本地验证（2026-08-03）

状态：设计草稿；未接入 `apps/api`、M6、Production Graph 或 Studio Runtime。

## 结论

`BeatVersion` / `BeatEntity` 可以沿用 Character/Scene 的版本、证据、
`ClaimedText`、候选状态机和人工确认闭环；真正困难的是 Beat 边界，不是
Pydantic schema。

现有 6 份剧本均没有 `节拍1` / `BEAT 1` 之类的显式边界。场标题只能证明
Scene 边界，空行、动作句、对白轮次都可能与节拍相关，但任何一个单独使用
都会把排版习惯误当叙事结构。因此本地确定性评估器对 6 份剧本全部返回
`missing`，不输出 Beat candidate。

## 复用链路

```text
人工确认或显式标签给出 Beat source range
  -> BeatVersion / BeatEntity
  -> beat_version_to_candidate_facts
  -> CandidateFact(entity_kind="beat")
  -> CandidateReviewItem（同一个 DTO）
  -> accept / edit_confirm / reject（同一套确认函数）
  -> promote_candidate_fact（原函数未改）
  -> AuthoritativeScriptFact(entity_kind="beat")
  -> script revision invalidation（原函数未改）
```

本次只在 `docs/internal-notes` 草稿层把 `entity_kind` 扩展到 `beat`。生产模块
`apps/api/runtime_candidate_fact_status.py` 仍保持 Character/Scene 范围；这是
“先设计验证、后决定是否接生产”的边界，不代表 Runtime 已支持 Beat。

## Schema 决策

- `BeatIdentity`：`scene_id` + 场景内 `order_index`。
- `BeatBoundary`：source range + 边界决定方式。没有边界就不构造 BeatVersion。
- `BeatConflict`：`tension: ClaimedText | None` + `present/missing`。
- `BeatTurn`：`change: ClaimedText | None` + `present/missing`。
- `BeatInfoRelease`：`information: ClaimedText | None` + `present/missing`。
- `BeatEmotionShift`：`from_state`、`to_state`、`change` 都是 ClaimedText；
  三者证据不完整时整个 facet 必须 `missing`，不能补情绪模板。
- Beat facet 映射为现有 `CandidateFact`；`missing` 行没有 evidence，也不能
  accept/promote。

## 六剧本实测

| 剧本 | Scene heading | 空行分隔 | 显式 Beat 标记 | 输出 Beat |
|---|---:|---:|---:|---:|
| 01 最后的光 | 2 | 8 | 0 | 0 (`missing`) |
| 02 海边的信 | 3 | 18 | 0 | 0 (`missing`) |
| 03 归途 | 2 | 11 | 0 | 0 (`missing`) |
| 04 旧照片 | 2 | 10 | 0 | 0 (`missing`) |
| 05 陌生来电 | 1 | 7 | 0 | 0 (`missing`) |
| 06 夜班（对抗样本） | 2 | 12 | 0 | 0 (`missing`) |

正向控制样本包含两个显式编号 Beat 标签，评估器只在该样本输出两个边界。
另用《最后的光》中一个人工确认范围验证了 3 个有证据 facet 和 1 个
`missing` emotion facet，并通过现有 accept、edit_confirm、promotion、revision
invalidation 链路。

验证命令：

```bash
.venv/bin/python docs/internal-notes/run_beat_schema_against_test_scripts.py
```

结果：`ALL PASS`。

## 现实难度

可靠 Beat 切分通常需要同时理解动作目标、冲突状态、信息增量、状态变化和
跨句上下文；它不是稳定的正则问题。一个场景也可能存在多种合理切法，取决于
导演、编剧或剪辑意图。后续若引入模型切分，应只产生
`model_inferred` boundary candidates，附 source spans 和不确定性，再走人工确认；
不能把模型切分直接当权威，也不能用“每段一个 Beat”作为确定性 fallback。

## 下一阶段集成条件

只有在确认 Runtime 集成时，才应同步扩展生产 `CandidateFact`、
`AuthoritativeScriptFact`、确认 DTO、ledger refresh/extraction contract，以及任何
下游按 `entity_kind` 穷举的分支。该集成需要单独测试 API 持久化、revision
invalidation 和 Production Graph 映射，本草稿不声称这些已经完成。
