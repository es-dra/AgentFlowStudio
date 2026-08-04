# ScriptProfile Schema 设计与本地验证（2026-08-03）

状态：设计草稿；未接入 `apps/api`、M6、Production Graph 或 Studio Runtime。

## 结论

`ScriptProfileVersion` / `ScriptProfileEntity` 可以沿用 Character/Scene/Beat 的
`ClaimedText`、候选状态机和人工确认闭环；`entity_kind="script_profile"`，
每个 script revision 通常只有一份 profile。

现有 6 份短篇测试剧本**都没有**显式写出主题/类型/受众/叙事目标/风格要求
标签。确定性提取器因此对 6 份剧本全部返回 **5 个 facet = missing**。
这是预期中的诚实结果，不是抽取失败。

## 复用链路

```text
labeled-only extract (or all-missing profile)
  -> ScriptProfileVersion / ScriptProfileEntity
  -> script_profile_version_to_candidate_facts
  -> CandidateFact(entity_kind="script_profile")
  -> accept / edit_confirm / reject（同一套确认函数）
  -> promote_candidate_fact（原函数未改）
  -> AuthoritativeScriptFact(entity_kind="script_profile")
  -> script revision invalidation（原函数未改）
```

本次只在 `docs/internal-notes` 草稿层把 `entity_kind` 扩展到 `script_profile`。
生产模块 `apps/api/runtime_candidate_fact_status.py` 仍保持既有范围。

## Schema 决策

- `theme` / `audience` / `narrative_goals` / `style_requirements`：
  `SingleClaimFacet` = `present|missing` + optional `ClaimedText`
- `genre`：`GenreFacet`，允许 `ClaimedText` 列表（显式「悬疑、情感」）
- 确定性提取**只认标签行**（`主题：` / `类型：` / `受众：` /
  `叙事目标：` / `风格要求：` 等），禁止从剧情“读出类型”
- missing 槽位不能 `accept`；人工可用 `edit_confirm` 写入判断并晋升

## 六剧本实测（全部 missing = 预期）

| 剧本 | theme | genre | audience | narrative_goals | style_requirements |
|---|---|---|---|---|---|
| 01_industry_standard_last_light.txt | missing | missing | missing | missing | missing |
| 02_industry_standard_letter_by_the_sea.txt | missing | missing | missing | missing | missing |
| 03_labeled_fields_homecoming.txt | missing | missing | missing | missing | missing |
| 04_mixed_format_old_photo.txt | missing | missing | missing | missing | missing |
| 05_missing_info_unknown_call.txt | missing | missing | missing | missing | missing |
| 06_adversarial_night_shift.txt | missing | missing | missing | missing | missing |

### 为什么 missing（共性）

- 这些素材是 Character/Scene/Beat 验证用短篇，正文没有 metadata 标签。
- 「看起来像悬疑/像亲情」属于解读，不是文本证据；按纪律不得标 present。
- `audience` 尤其几乎从不在剧本正文出现，missing 是常态。

## 正向控制样本

显式写入五类标签后，提取器应全部 `present`（genre 拆成列表）：

```json
{
  "theme": {
    "status": "present",
    "text": "等待与释然",
    "why": null
  },
  "genre": {
    "status": "present",
    "text": [
      "悬疑",
      "情感"
    ],
    "why": null
  },
  "audience": {
    "status": "present",
    "text": "成年观众",
    "why": null
  },
  "narrative_goals": {
    "status": "present",
    "text": "让观众体会未送达的告别",
    "why": null
  },
  "style_requirements": {
    "status": "present",
    "text": "克制对白，冷暖光对比",
    "why": null
  }
}
```

## 人工确认路径（无文本类型标签）

对《海边的信》缺失的 `script_profile.genre`：
1. `promote` 直接失败（missing）
2. `accept` 被确认环拒绝（必须 edit_confirm）
3. `edit_confirm(new_text="悬疑")` → `AuthoritativeScriptFact`
   （`promotion_kind=human_confirmation`，`entity_kind=script_profile`）
4. 换 revision → 权威失效

这说明：人工可以补充文本未写明的类型判断，但必须走确认闭环，
不能靠置信度或模型“感觉”自动晋升。

## 现实难度（主观性）

主题、叙事目标、风格比 Character 姓名/Scene 地点更依赖解读：
- 同一剧本可能被合理标成「亲情」或「成长」或「告别」；
- 类型常是营销/平台标签，不一定写在稿纸上；
- 受众几乎总是制作侧信息，不在对白里。

因此确定性层只做标签抽取；任何内容推断若引入，只能作为
`model_inferred` 候选并强制人工确认，不能假装容易。

## 验证命令

```bash
.venv/bin/python docs/internal-notes/run_script_profile_against_test_scripts.py
```

## 下一阶段集成条件

只有确认 Runtime 集成时，才应同步扩展生产 `CandidateFact.entity_kind`、
confirmation API 与（可选）Production Graph feed；在此之前保持草稿隔离。
