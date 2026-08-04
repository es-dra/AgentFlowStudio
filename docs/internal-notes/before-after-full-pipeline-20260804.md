# 完整链路之前/之后对比：三份原始剧本

> 本报告由 `docs/internal-notes/run_full_pipeline_demo.py` **实际跑本地临时 Runtime API** 生成，
> 不是设计文档。可重复执行脚本复现同一结论。不碰 `/opt` 或线上数据。

- 生成状态：**ALL ASSERTIONS PASSED**（50 checks）
- 配套证据 JSON：`before-after-full-pipeline-20260804.evidence.json`
- 新系统开关：`AFS_USE_IMPROVED_EXTRACTION, AFS_USE_CANDIDATE_CONFIRMATION_LOOP, AFS_M6_REUSE_SCRIPT_TRUTH_REVISION_ID, AFS_CANDIDATE_FACTS_FEED_PRODUCTION_GRAPH, AFS_CANDIDATE_FACTS_USE_NAMESPACED_REVISION_NODES`

## 发现（跑演示时如实记录）

- **last_light**: Legacy characters for《最后的光》are now just ['玛雅'] (correct); junk remains on scenes ['颤抖','灯上']. Earlier day-1 notes that mentioned character junk '颤抖'/'灯上' are outdated for the character slot.
- **homecoming**: 《归途》legacy characters already match improved extract (labeled cast list). New-system value is ScriptFormatProfile + confirmation/Graph provenance, not character rescue.

---

## 《最后的光》

脚本：`01_industry_standard_last_light.txt`

### Legacy（开关全关）

- Script Truth revision：`scrrev_6b870cca716c4ca7`
- 人物：`["玛雅"]`
- 场景：`["颤抖", "灯上"]`
- validation：`{"verdict": "PASS", "P0": 0, "P1": 0}`
- shadow_extraction 出现：`False`

```json
{
  "characters": [
    "玛雅"
  ],
  "scenes": [
    "颤抖",
    "灯上"
  ],
  "validation": {
    "verdict": "PASS",
    "P0": 0,
    "P1": 0
  }
}
```

### 完整新系统（相关开关全开）

- Script Truth revision：`scrrev_b59ffff49943478d`
- shadow improved 人物：`["玛雅"]`
- shadow improved 场景：`["废弃灯塔", "灯塔阳台"]`
- M6 candidate 仍走 legacy 人物（shadow-only 旁路）：`["玛雅"]`

#### 候选事实（refresh）

- Character：`["玛雅"]`
- Scene：`["废弃灯塔", "灯塔阳台"]`
- ScriptProfile：`{"theme": {"text": "(missing)", "status": "missing"}, "genre": {"text": "(missing)", "status": "missing"}, "audience": {"text": "(missing)", "status": "missing"}, "narrative_goals": {"text": "(missing)", "status": "missing"}, "style_requirements": {"text": "(missing)", "status": "missing"}}`
- ScriptFormatProfile：`{"format_style": {"text": "industry_heading", "status": "extracted_from_text"}, "cleaning_notes": {"text": "[]", "status": "extracted_from_text"}, "scene_boundary_count": {"text": "2", "status": "extracted_from_text"}}`
- Beat boundaries：`0`；Beat facets：`0`
- Beat missing_slots：`2`（无显式节拍标签 → 诚实 missing，未编造）

```json
{
  "characters": [
    "玛雅"
  ],
  "scenes": [
    "废弃灯塔",
    "灯塔阳台"
  ],
  "script_profile": {
    "theme": {
      "text": "(missing)",
      "status": "missing"
    },
    "genre": {
      "text": "(missing)",
      "status": "missing"
    },
    "audience": {
      "text": "(missing)",
      "status": "missing"
    },
    "narrative_goals": {
      "text": "(missing)",
      "status": "missing"
    },
    "style_requirements": {
      "text": "(missing)",
      "status": "missing"
    }
  },
  "script_format_profile": {
    "format_style": {
      "text": "industry_heading",
      "status": "extracted_from_text"
    },
    "cleaning_notes": {
      "text": "[]",
      "status": "extracted_from_text"
    },
    "scene_boundary_count": {
      "text": "2",
      "status": "extracted_from_text"
    }
  },
  "beat_boundary_count": 0,
  "beat_facet_count": 0,
  "beat_missing_slots": [
    {
      "field_path": "scene[scene_0_废弃灯塔].beats",
      "message": "No explicit numbered Beat labels in this Scene; no Beat candidate emitted.",
      "status": "missing"
    },
    {
      "field_path": "scene[scene_1_灯塔阳台].beats",
      "message": "No explicit numbered Beat labels in this Scene; no Beat candidate emitted.",
      "status": "missing"
    }
  ]
}
```

#### 人工确认

- 确认条数：`6`（Character / Scene / present ScriptFormatProfile；不确认 missing ScriptProfile，不编造 Beat）
- 确认明细：`[{"entity_kind": "character", "field_path": "identity.display_name", "text": "玛雅"}, {"entity_kind": "scene", "field_path": "scene.name", "text": "废弃灯塔"}, {"entity_kind": "scene", "field_path": "scene.name", "text": "灯塔阳台"}, {"entity_kind": "script_format_profile", "field_path": "script_format_profile.format_style", "text": "industry_heading"}, {"entity_kind": "script_format_profile", "field_path": "script_format_profile.cleaning_notes", "text": "[]"}, {"entity_kind": "script_format_profile", "field_path": "script_format_profile.scene_boundary_count", "text": "2"}]`
- resolved.characters：`["玛雅"]`
- resolved.scenes：`["废弃灯塔", "灯塔阳台"]`
- resolved.script_format_profile：`{"format_style": "industry_heading", "cleaning_notes": [], "scene_boundary_count": 2}`
- resolved.beats：`[]`

#### Production Graph

- authfact 节点数：`6`
- 按 entity_kind：`{"character": 1, "scene": 2, "script_format_profile": 3}`
- 节点 texts：`["2", "[]", "industry_heading", "废弃灯塔", "灯塔阳台", "玛雅"]`

```json
[
  {
    "node_id": "authfact-character-auth_ca9de7868e0a",
    "entity_kind": "character",
    "field_path": "identity.display_name",
    "text": "玛雅",
    "source_revision_id": "scrrev_b59ffff49943478d",
    "promotion_kind": "human_confirmation"
  },
  {
    "node_id": "authfact-scene-auth_a4d0d0f35c09",
    "entity_kind": "scene",
    "field_path": "scene.name",
    "text": "灯塔阳台",
    "source_revision_id": "scrrev_b59ffff49943478d",
    "promotion_kind": "human_confirmation"
  },
  {
    "node_id": "authfact-scene-auth_e551a2790a71",
    "entity_kind": "scene",
    "field_path": "scene.name",
    "text": "废弃灯塔",
    "source_revision_id": "scrrev_b59ffff49943478d",
    "promotion_kind": "human_confirmation"
  },
  {
    "node_id": "authfact-script_format_profile-1265b790c815174a6d4b1710",
    "entity_kind": "script_format_profile",
    "field_path": "script_format_profile.scene_boundary_count",
    "text": "2",
    "source_revision_id": "scrrev_b59ffff49943478d",
    "promotion_kind": "human_confirmation"
  },
  {
    "node_id": "authfact-script_format_profile-173ce5a8d087431924aa2f6d",
    "entity_kind": "script_format_profile",
    "field_path": "script_format_profile.cleaning_notes",
    "text": "[]",
    "source_revision_id": "scrrev_b59ffff49943478d",
    "promotion_kind": "human_confirmation"
  },
  {
    "node_id": "authfact-script_format_profile-22984fc27373d9e37e47b7b0",
    "entity_kind": "script_format_profile",
    "field_path": "script_format_profile.format_style",
    "text": "industry_heading",
    "source_revision_id": "scrrev_b59ffff49943478d",
    "promotion_kind": "human_confirmation"
  }
]
```

---

## 《归途》

脚本：`03_labeled_fields_homecoming.txt`

### Legacy（开关全关）

- Script Truth revision：`scrrev_9106c66361e74487`
- 人物：`["陈浩", "林秀"]`
- 场景：`["小镇火车站", "陈浩家中的老屋"]`
- validation：`{"verdict": "PASS", "P0": 0, "P1": 0}`
- shadow_extraction 出现：`False`

```json
{
  "characters": [
    "陈浩",
    "林秀"
  ],
  "scenes": [
    "小镇火车站",
    "陈浩家中的老屋"
  ],
  "validation": {
    "verdict": "PASS",
    "P0": 0,
    "P1": 0
  }
}
```

### 完整新系统（相关开关全开）

- Script Truth revision：`scrrev_47fe21e047674e95`
- shadow improved 人物：`["陈浩", "林秀"]`
- shadow improved 场景：`["小镇火车站", "陈浩家中的老屋"]`
- M6 candidate 仍走 legacy 人物（shadow-only 旁路）：`["陈浩", "林秀"]`

#### 候选事实（refresh）

- Character：`["陈浩", "林秀"]`
- Scene：`["小镇火车站", "陈浩家中的老屋"]`
- ScriptProfile：`{"theme": {"text": "(missing)", "status": "missing"}, "genre": {"text": "(missing)", "status": "missing"}, "audience": {"text": "(missing)", "status": "missing"}, "narrative_goals": {"text": "(missing)", "status": "missing"}, "style_requirements": {"text": "(missing)", "status": "missing"}}`
- ScriptFormatProfile：`{"format_style": {"text": "labeled", "status": "extracted_from_text"}, "cleaning_notes": {"text": "[]", "status": "extracted_from_text"}, "scene_boundary_count": {"text": "2", "status": "extracted_from_text"}}`
- Beat boundaries：`0`；Beat facets：`0`
- Beat missing_slots：`2`（无显式节拍标签 → 诚实 missing，未编造）

```json
{
  "characters": [
    "陈浩",
    "林秀"
  ],
  "scenes": [
    "小镇火车站",
    "陈浩家中的老屋"
  ],
  "script_profile": {
    "theme": {
      "text": "(missing)",
      "status": "missing"
    },
    "genre": {
      "text": "(missing)",
      "status": "missing"
    },
    "audience": {
      "text": "(missing)",
      "status": "missing"
    },
    "narrative_goals": {
      "text": "(missing)",
      "status": "missing"
    },
    "style_requirements": {
      "text": "(missing)",
      "status": "missing"
    }
  },
  "script_format_profile": {
    "format_style": {
      "text": "labeled",
      "status": "extracted_from_text"
    },
    "cleaning_notes": {
      "text": "[]",
      "status": "extracted_from_text"
    },
    "scene_boundary_count": {
      "text": "2",
      "status": "extracted_from_text"
    }
  },
  "beat_boundary_count": 0,
  "beat_facet_count": 0,
  "beat_missing_slots": [
    {
      "field_path": "scene[scene_0_小镇火车站].beats",
      "message": "No explicit numbered Beat labels in this Scene; no Beat candidate emitted.",
      "status": "missing"
    },
    {
      "field_path": "scene[scene_1_陈浩家中的老屋].beats",
      "message": "No explicit numbered Beat labels in this Scene; no Beat candidate emitted.",
      "status": "missing"
    }
  ]
}
```

#### 人工确认

- 确认条数：`7`（Character / Scene / present ScriptFormatProfile；不确认 missing ScriptProfile，不编造 Beat）
- 确认明细：`[{"entity_kind": "character", "field_path": "identity.display_name", "text": "陈浩"}, {"entity_kind": "character", "field_path": "identity.display_name", "text": "林秀"}, {"entity_kind": "scene", "field_path": "scene.name", "text": "小镇火车站"}, {"entity_kind": "scene", "field_path": "scene.name", "text": "陈浩家中的老屋"}, {"entity_kind": "script_format_profile", "field_path": "script_format_profile.format_style", "text": "labeled"}, {"entity_kind": "script_format_profile", "field_path": "script_format_profile.cleaning_notes", "text": "[]"}, {"entity_kind": "script_format_profile", "field_path": "script_format_profile.scene_boundary_count", "text": "2"}]`
- resolved.characters：`["陈浩", "林秀"]`
- resolved.scenes：`["小镇火车站", "陈浩家中的老屋"]`
- resolved.script_format_profile：`{"format_style": "labeled", "cleaning_notes": [], "scene_boundary_count": 2}`
- resolved.beats：`[]`

#### Production Graph

- authfact 节点数：`7`
- 按 entity_kind：`{"character": 2, "scene": 2, "script_format_profile": 3}`
- 节点 texts：`["2", "[]", "labeled", "小镇火车站", "林秀", "陈浩", "陈浩家中的老屋"]`

```json
[
  {
    "node_id": "authfact-character-auth_16dfcedf58ff",
    "entity_kind": "character",
    "field_path": "identity.display_name",
    "text": "林秀",
    "source_revision_id": "scrrev_47fe21e047674e95",
    "promotion_kind": "human_confirmation"
  },
  {
    "node_id": "authfact-character-auth_d55c8d66d6dd",
    "entity_kind": "character",
    "field_path": "identity.display_name",
    "text": "陈浩",
    "source_revision_id": "scrrev_47fe21e047674e95",
    "promotion_kind": "human_confirmation"
  },
  {
    "node_id": "authfact-scene-auth_297665725b46",
    "entity_kind": "scene",
    "field_path": "scene.name",
    "text": "小镇火车站",
    "source_revision_id": "scrrev_47fe21e047674e95",
    "promotion_kind": "human_confirmation"
  },
  {
    "node_id": "authfact-scene-auth_a8ee79a8b7a2",
    "entity_kind": "scene",
    "field_path": "scene.name",
    "text": "陈浩家中的老屋",
    "source_revision_id": "scrrev_47fe21e047674e95",
    "promotion_kind": "human_confirmation"
  },
  {
    "node_id": "authfact-script_format_profile-4456d107c665517d02b6ed16",
    "entity_kind": "script_format_profile",
    "field_path": "script_format_profile.cleaning_notes",
    "text": "[]",
    "source_revision_id": "scrrev_47fe21e047674e95",
    "promotion_kind": "human_confirmation"
  },
  {
    "node_id": "authfact-script_format_profile-99e0b7c8887ef88bda42c11f",
    "entity_kind": "script_format_profile",
    "field_path": "script_format_profile.format_style",
    "text": "labeled",
    "source_revision_id": "scrrev_47fe21e047674e95",
    "promotion_kind": "human_confirmation"
  },
  {
    "node_id": "authfact-script_format_profile-e95746f93b180ecbac27132f",
    "entity_kind": "script_format_profile",
    "field_path": "script_format_profile.scene_boundary_count",
    "text": "2",
    "source_revision_id": "scrrev_47fe21e047674e95",
    "promotion_kind": "human_confirmation"
  }
]
```

---

## 《海边的信》

脚本：`02_industry_standard_letter_by_the_sea.txt`

### Legacy（开关全关）

- Script Truth revision：`scrrev_cf5a41aa26294717`
- 人物：`["苏晴没", "从远处", "道他可能"]`
- 场景：`["柜台前", "柜台上", "礁石上", "她身边坐下", "书桌前", "一叠信纸上"]`
- validation：`{"verdict": "PASS", "P0": 0, "P1": 0}`
- shadow_extraction 出现：`False`

```json
{
  "characters": [
    "苏晴没",
    "从远处",
    "道他可能"
  ],
  "scenes": [
    "柜台前",
    "柜台上",
    "礁石上",
    "她身边坐下",
    "书桌前",
    "一叠信纸上"
  ],
  "validation": {
    "verdict": "PASS",
    "P0": 0,
    "P1": 0
  }
}
```

### 完整新系统（相关开关全开）

- Script Truth revision：`scrrev_eb86ce43578b430c`
- shadow improved 人物：`["苏晴", "老王", "林悦"]`
- shadow improved 场景：`["老式邮局", "海边礁石", "苏晴的房间"]`
- M6 candidate 仍走 legacy 人物（shadow-only 旁路）：`["苏晴没", "从远处", "道他可能"]`

#### 候选事实（refresh）

- Character：`["苏晴", "老王", "林悦"]`
- Scene：`["老式邮局", "海边礁石", "苏晴的房间"]`
- ScriptProfile：`{"theme": {"text": "(missing)", "status": "missing"}, "genre": {"text": "(missing)", "status": "missing"}, "audience": {"text": "(missing)", "status": "missing"}, "narrative_goals": {"text": "(missing)", "status": "missing"}, "style_requirements": {"text": "(missing)", "status": "missing"}}`
- ScriptFormatProfile：`{"format_style": {"text": "industry_heading", "status": "extracted_from_text"}, "cleaning_notes": {"text": "[]", "status": "extracted_from_text"}, "scene_boundary_count": {"text": "3", "status": "extracted_from_text"}}`
- Beat boundaries：`0`；Beat facets：`0`
- Beat missing_slots：`3`（无显式节拍标签 → 诚实 missing，未编造）

```json
{
  "characters": [
    "苏晴",
    "老王",
    "林悦"
  ],
  "scenes": [
    "老式邮局",
    "海边礁石",
    "苏晴的房间"
  ],
  "script_profile": {
    "theme": {
      "text": "(missing)",
      "status": "missing"
    },
    "genre": {
      "text": "(missing)",
      "status": "missing"
    },
    "audience": {
      "text": "(missing)",
      "status": "missing"
    },
    "narrative_goals": {
      "text": "(missing)",
      "status": "missing"
    },
    "style_requirements": {
      "text": "(missing)",
      "status": "missing"
    }
  },
  "script_format_profile": {
    "format_style": {
      "text": "industry_heading",
      "status": "extracted_from_text"
    },
    "cleaning_notes": {
      "text": "[]",
      "status": "extracted_from_text"
    },
    "scene_boundary_count": {
      "text": "3",
      "status": "extracted_from_text"
    }
  },
  "beat_boundary_count": 0,
  "beat_facet_count": 0,
  "beat_missing_slots": [
    {
      "field_path": "scene[scene_0_老式邮局].beats",
      "message": "No explicit numbered Beat labels in this Scene; no Beat candidate emitted.",
      "status": "missing"
    },
    {
      "field_path": "scene[scene_1_海边礁石].beats",
      "message": "No explicit numbered Beat labels in this Scene; no Beat candidate emitted.",
      "status": "missing"
    },
    {
      "field_path": "scene[scene_2_苏晴的房间].beats",
      "message": "No explicit numbered Beat labels in this Scene; no Beat candidate emitted.",
      "status": "missing"
    }
  ]
}
```

#### 人工确认

- 确认条数：`9`（Character / Scene / present ScriptFormatProfile；不确认 missing ScriptProfile，不编造 Beat）
- 确认明细：`[{"entity_kind": "character", "field_path": "identity.display_name", "text": "苏晴"}, {"entity_kind": "character", "field_path": "identity.display_name", "text": "老王"}, {"entity_kind": "character", "field_path": "identity.display_name", "text": "林悦"}, {"entity_kind": "scene", "field_path": "scene.name", "text": "老式邮局"}, {"entity_kind": "scene", "field_path": "scene.name", "text": "海边礁石"}, {"entity_kind": "scene", "field_path": "scene.name", "text": "苏晴的房间"}, {"entity_kind": "script_format_profile", "field_path": "script_format_profile.format_style", "text": "industry_heading"}, {"entity_kind": "script_format_profile", "field_path": "script_format_profile.cleaning_notes", "text": "[]"}, {"entity_kind": "script_format_profile", "field_path": "script_format_profile.scene_boundary_count", "text": "3"}]`
- resolved.characters：`["苏晴", "老王", "林悦"]`
- resolved.scenes：`["老式邮局", "海边礁石", "苏晴的房间"]`
- resolved.script_format_profile：`{"format_style": "industry_heading", "cleaning_notes": [], "scene_boundary_count": 3}`
- resolved.beats：`[]`

#### Production Graph

- authfact 节点数：`9`
- 按 entity_kind：`{"character": 3, "scene": 3, "script_format_profile": 3}`
- 节点 texts：`["3", "[]", "industry_heading", "林悦", "海边礁石", "老式邮局", "老王", "苏晴", "苏晴的房间"]`

```json
[
  {
    "node_id": "authfact-character-auth_29d85eeab7db",
    "entity_kind": "character",
    "field_path": "identity.display_name",
    "text": "苏晴",
    "source_revision_id": "scrrev_eb86ce43578b430c",
    "promotion_kind": "human_confirmation"
  },
  {
    "node_id": "authfact-character-auth_99f1a56d64ed",
    "entity_kind": "character",
    "field_path": "identity.display_name",
    "text": "林悦",
    "source_revision_id": "scrrev_eb86ce43578b430c",
    "promotion_kind": "human_confirmation"
  },
  {
    "node_id": "authfact-character-auth_cfede61b823e",
    "entity_kind": "character",
    "field_path": "identity.display_name",
    "text": "老王",
    "source_revision_id": "scrrev_eb86ce43578b430c",
    "promotion_kind": "human_confirmation"
  },
  {
    "node_id": "authfact-scene-auth_0e3cdff47634",
    "entity_kind": "scene",
    "field_path": "scene.name",
    "text": "苏晴的房间",
    "source_revision_id": "scrrev_eb86ce43578b430c",
    "promotion_kind": "human_confirmation"
  },
  {
    "node_id": "authfact-scene-auth_2d809aefdf96",
    "entity_kind": "scene",
    "field_path": "scene.name",
    "text": "海边礁石",
    "source_revision_id": "scrrev_eb86ce43578b430c",
    "promotion_kind": "human_confirmation"
  },
  {
    "node_id": "authfact-scene-auth_eb5e3ac429a0",
    "entity_kind": "scene",
    "field_path": "scene.name",
    "text": "老式邮局",
    "source_revision_id": "scrrev_eb86ce43578b430c",
    "promotion_kind": "human_confirmation"
  },
  {
    "node_id": "authfact-script_format_profile-171f64ef42dd7734a2bc6647",
    "entity_kind": "script_format_profile",
    "field_path": "script_format_profile.cleaning_notes",
    "text": "[]",
    "source_revision_id": "scrrev_eb86ce43578b430c",
    "promotion_kind": "human_confirmation"
  },
  {
    "node_id": "authfact-script_format_profile-5f9fda5fefddee73cf74c7a4",
    "entity_kind": "script_format_profile",
    "field_path": "script_format_profile.scene_boundary_count",
    "text": "3",
    "source_revision_id": "scrrev_eb86ce43578b430c",
    "promotion_kind": "human_confirmation"
  },
  {
    "node_id": "authfact-script_format_profile-7de472ff72666d15e4bae764",
    "entity_kind": "script_format_profile",
    "field_path": "script_format_profile.format_style",
    "text": "industry_heading",
    "source_revision_id": "scrrev_eb86ce43578b430c",
    "promotion_kind": "human_confirmation"
  }
]
```

---

## 总结表格

| 剧本 | Legacy 人物 | 新系统人物 | Legacy 场景 | 新系统场景 | ScriptProfile | Beat | Graph 节点数 |
|---|---|---|---|---|---|---|---|
| 最后的光 | 玛雅 | 玛雅 | 颤抖, 灯上 | 废弃灯塔, 灯塔阳台 | all missing | missing (0 candidates) | 6 |
| 归途 | 陈浩, 林秀 | 陈浩, 林秀 | 小镇火车站, 陈浩家中的老屋 | 小镇火车站, 陈浩家中的老屋 | all missing | missing (0 candidates) | 7 |
| 海边的信 | 苏晴没, 从远处, 道他可能 | 苏晴, 老王, 林悦 | 柜台前, 柜台上, 礁石上, 她身边坐下, 书桌前, 一叠信纸上 | 老式邮局, 海边礁石, 苏晴的房间 | all missing | missing (0 candidates) | 9 |

## 怎么复现

```bash
.venv/bin/python docs/internal-notes/run_full_pipeline_demo.py
```

每次运行使用全新 tempfile Runtime；结果结构应一致（revision id / fact id 会变）。
