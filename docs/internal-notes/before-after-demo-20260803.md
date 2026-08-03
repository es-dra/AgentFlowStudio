# 之前 vs 之后：以《海边的信》为例

> 本报告由 `docs/internal-notes/run_before_after_demo.py` **实际跑本地临时 Runtime API** 生成，
> 不是设计文档。可重复执行脚本复现同一结论。

- 脚本：`02_industry_standard_letter_by_the_sea.txt`
- 生成状态：**ALL ASSERTIONS PASSED**（21 checks）
- 配套证据 JSON：`before-after-demo-20260803.evidence.json`

---

## 问题（复现，证明现在依然存在）

所有新开关保持**默认关闭**，走现有 M6 preview API。
legacy 正则仍然把「苏晴没 / 从远处 / 道他可能」当成人物，validation 仍然 **PASS**。

### 实际结果（Part 1）

- Script Truth revision：`scrrev_205cf8f17dc94e24`
- 识别出的人物：`['苏晴没', '从远处', '道他可能']`
- 识别出的场景：`['柜台前', '柜台上', '礁石上', '她身边坐下', '书桌前', '一叠信纸上']`
- validation：`{'verdict': 'PASS', 'P0': 0, 'P1': 0}`
- shadow_extraction 是否出现：`False`（关开关时应为 false）

```json
{
  "character_display_names": [
    "苏晴没",
    "从远处",
    "道他可能"
  ],
  "scene_names": [
    "柜台前",
    "柜台上",
    "礁石上",
    "她身边坐下",
    "书桌前",
    "一叠信纸上"
  ],
  "shadow_extraction_present": false,
  "validation": {
    "P0": 0,
    "P1": 0,
    "verdict": "PASS"
  }
}
```

### 为什么这是个问题

1. **内容错了还 PASS**：校验器检查结构完备性，不检查「名字是不是真人物」。
2. **没有人工确认门槛**：高置信度提取会被当成可用结果继续往下走。
3. **关掉新开关后问题立刻回来**——不是「代码碰巧修好了」，必须显式打开旁路能力。

---

## 解决方案的完整旅程

打开相关开关（仅本演示临时 Runtime）：

```json
{
  "AFS_CANDIDATE_FACTS_FEED_PRODUCTION_GRAPH": "true",
  "AFS_CANDIDATE_FACTS_USE_NAMESPACED_REVISION_NODES": "true",
  "AFS_M6_REUSE_SCRIPT_TRUTH_REVISION_ID": "true",
  "AFS_USE_CANDIDATE_CONFIRMATION_LOOP": "true",
  "AFS_USE_IMPROVED_EXTRACTION": "true"
}
```

### 步骤 1：提交剧本 → Script Truth revision

真实 API：`POST /projects/{id}/script-revisions`

```json
{
  "revision_id": "scrrev_18861d03750a458b",
  "source_digest": "02674232e5cfe7b78663b63654d4e9acc4e901a43256a08f26657de87a49e3f7"
}
```

### 步骤 2：改进提取（shadow-only）

打开 `AFS_USE_IMPROVED_EXTRACTION` 后再次跑 M6 preview。
**候选 candidate 仍是 legacy 垃圾**（旁路不偷偷改主路径），
但 `shadow_extraction.improved` 给出正确人物/场景。

```json
{
  "affects_production_graph": false,
  "candidate_still_uses_legacy_characters": [
    "苏晴没",
    "从远处",
    "道他可能"
  ],
  "diff": {
    "characters_only_in_improved": [
      "林悦",
      "老王",
      "苏晴"
    ],
    "characters_only_in_legacy": [
      "从远处",
      "苏晴没",
      "道他可能"
    ],
    "scenes_only_in_improved": [
      "海边礁石",
      "老式邮局",
      "苏晴的房间"
    ],
    "scenes_only_in_legacy": [
      "一叠信纸上",
      "书桌前",
      "她身边坐下",
      "柜台上",
      "柜台前",
      "礁石上"
    ]
  },
  "embedded_script_revision_id": "scrrev_18861d03750a458b",
  "improved_characters": [
    "苏晴",
    "老王",
    "林悦"
  ],
  "improved_scenes": [
    "老式邮局",
    "海边礁石",
    "苏晴的房间"
  ],
  "legacy_characters": [
    "苏晴没",
    "从远处",
    "道他可能"
  ],
  "legacy_scenes": [
    "柜台前",
    "柜台上",
    "礁石上",
    "她身边坐下",
    "书桌前",
    "一叠信纸上"
  ],
  "validation_verdict": "PASS"
}
```

### 步骤 3：候选确认闭环 + 垃圾注入

打开 `AFS_USE_CANDIDATE_CONFIRMATION_LOOP`，`POST .../candidate-facts/review/refresh`。
此时 **authoritative 仍为空**。故意注入「苏晴没」（置信度 0.96）只能停在候选态：

```json
{
  "authoritative_still_empty": true,
  "confidence": 0.96,
  "fact_id": "fact_38a9503a4509",
  "review_decision": "pending",
  "status": "extracted_from_text",
  "text": "苏晴没",
  "uncertainty_note": "legacy regex fragment; not a real name",
  "why_not_auto_authoritative": "status=extracted_from_text + high confidence is still a CandidateFact; promote_candidate_fact requires human_confirmed (or a named deterministic check). Confidence alone never promotes."
}
```

刷新后的真实候选（节选）：

```json
{
  "authoritative_before_human": [],
  "candidate_texts": [
    "林悦",
    "海边礁石",
    "老式邮局",
    "老王",
    "苏晴",
    "苏晴的房间"
  ],
  "sample_items": [
    {
      "confidence": 0.9,
      "entity_kind": "character",
      "is_missing_slot": false,
      "review_decision": "pending",
      "status": "extracted_from_text",
      "text": "苏晴"
    },
    {
      "confidence": 0.9,
      "entity_kind": "character",
      "is_missing_slot": false,
      "review_decision": "pending",
      "status": "extracted_from_text",
      "text": "老王"
    },
    {
      "confidence": 0.9,
      "entity_kind": "character",
      "is_missing_slot": false,
      "review_decision": "pending",
      "status": "extracted_from_text",
      "text": "林悦"
    },
    {
      "confidence": 0.92,
      "entity_kind": "scene",
      "is_missing_slot": false,
      "review_decision": "pending",
      "status": "extracted_from_text",
      "text": "老式邮局"
    },
    {
      "confidence": 0.92,
      "entity_kind": "scene",
      "is_missing_slot": false,
      "review_decision": "pending",
      "status": "extracted_from_text",
      "text": "海边礁石"
    },
    {
      "confidence": 0.92,
      "entity_kind": "scene",
      "is_missing_slot": false,
      "review_decision": "pending",
      "status": "extracted_from_text",
      "text": "苏晴的房间"
    }
  ]
}
```

### 步骤 4：人工拒绝垃圾、确认真实人物/场景

- `reject`「苏晴没」→ 不进 authoritative，也不写 Graph
- `accept` 苏晴 / 老王 / 林悦 + 三个场景
- `resolved` 下游读到人工确认后的正确名单

```json
{
  "authoritative_texts": [
    "苏晴",
    "老王",
    "林悦",
    "老式邮局",
    "海边礁石",
    "苏晴的房间"
  ],
  "reject_junk": {
    "action": "reject",
    "affects_production_graph": false,
    "graph_feed": {
      "fed": false,
      "node_ids": [],
      "reason": "no_new_authoritative_fact",
      "skipped": true
    },
    "result": {
      "rejected_fact_id": "fact_38a9503a4509"
    }
  },
  "resolved_for_downstream": {
    "authoritative_fact_ids": [
      "auth_c016da4e5cd8",
      "auth_c7acb18be967",
      "auth_1853af9a5b3e",
      "auth_2b5d1c6d983f",
      "auth_804017471e4a",
      "auth_12ac80242f33"
    ],
    "authority_source": "authoritative_ledger",
    "characters": [
      "苏晴",
      "老王",
      "林悦"
    ],
    "raw_extraction_characters": [],
    "raw_extraction_scenes": [],
    "revision_id": "scrrev_18861d03750a458b",
    "scenes": [
      "老式邮局",
      "海边礁石",
      "苏晴的房间"
    ]
  },
  "sample_accept_graph_feed": {
    "affects_production_graph": true,
    "fed": true,
    "graph_version": 1,
    "idempotent_replay": false,
    "node_ids": [
      "authfact-character-auth_c016da4e5cd8"
    ],
    "reason": null,
    "skipped": false
  },
  "sample_authoritative_fact": {
    "authoritative_fact_id": "auth_c016da4e5cd8",
    "deterministic_check_id": null,
    "entity_id": "character_0_苏晴",
    "entity_kind": "character",
    "evidence_spans": [
      {
        "end": 50,
        "quote": "苏晴（20多岁，安静，眼神里带着期待）",
        "start": 31
      }
    ],
    "field_path": "identity.display_name",
    "human_confirmed_by": "local-runtime-owner",
    "project_id": "demo_sea_closed_loop",
    "promoted_at": "2026-08-03T05:55:32.930012Z",
    "promotion_kind": "human_confirmation",
    "schema_version": "afs.script_understanding.candidate_fact_status.v0.1",
    "source_candidate_fact_id": "fact_0692d0c2ade5",
    "source_confidence": 0.9,
    "source_revision_digest": "02674232e5cfe7b78663b63654d4e9acc4e901a43256a08f26657de87a49e3f7",
    "source_revision_id": "scrrev_18861d03750a458b",
    "text": "苏晴"
  }
}
```

### 步骤 5：权威事实写入 Production Graph（可溯源）

打开 `AFS_CANDIDATE_FACTS_FEED_PRODUCTION_GRAPH` + `AFS_CANDIDATE_FACTS_USE_NAMESPACED_REVISION_NODES`。
accept 后写入 Graph；`GET /projects/{id}/m4/production-graph` 读回。
revision 节点使用 `scripttruth-revision-{scrrev_*}-{digest16}`，避免与 M6 candidate 静默抢 key。

```json
{
  "authfact_node_count": 6,
  "graph_version": 6,
  "namespaced_revision_prefix_ok": true,
  "provenance_rows": [
    {
      "authoritative_fact_id": "auth_1853af9a5b3e",
      "category": "entity",
      "human_confirmed_by": "local-runtime-owner",
      "node_id": "authfact-character-auth_1853af9a5b3e",
      "promotion_kind": "human_confirmation",
      "source": "authoritative_script_fact_feed",
      "source_candidate_fact_id": "fact_86121af18268",
      "source_revision_id": "scrrev_18861d03750a458b",
      "text": "林悦"
    },
    {
      "authoritative_fact_id": "auth_c016da4e5cd8",
      "category": "entity",
      "human_confirmed_by": "local-runtime-owner",
      "node_id": "authfact-character-auth_c016da4e5cd8",
      "promotion_kind": "human_confirmation",
      "source": "authoritative_script_fact_feed",
      "source_candidate_fact_id": "fact_0692d0c2ade5",
      "source_revision_id": "scrrev_18861d03750a458b",
      "text": "苏晴"
    },
    {
      "authoritative_fact_id": "auth_c7acb18be967",
      "category": "entity",
      "human_confirmed_by": "local-runtime-owner",
      "node_id": "authfact-character-auth_c7acb18be967",
      "promotion_kind": "human_confirmation",
      "source": "authoritative_script_fact_feed",
      "source_candidate_fact_id": "fact_5b480a0c057a",
      "source_revision_id": "scrrev_18861d03750a458b",
      "text": "老王"
    },
    {
      "authoritative_fact_id": "auth_12ac80242f33",
      "category": "location",
      "human_confirmed_by": "local-runtime-owner",
      "node_id": "authfact-scene-auth_12ac80242f33",
      "promotion_kind": "human_confirmation",
      "source": "authoritative_script_fact_feed",
      "source_candidate_fact_id": "fact_b48cc56ea1ba",
      "source_revision_id": "scrrev_18861d03750a458b",
      "text": "苏晴的房间"
    },
    {
      "authoritative_fact_id": "auth_2b5d1c6d983f",
      "category": "location",
      "human_confirmed_by": "local-runtime-owner",
      "node_id": "authfact-scene-auth_2b5d1c6d983f",
      "promotion_kind": "human_confirmation",
      "source": "authoritative_script_fact_feed",
      "source_candidate_fact_id": "fact_6a7de5d361a8",
      "source_revision_id": "scrrev_18861d03750a458b",
      "text": "老式邮局"
    },
    {
      "authoritative_fact_id": "auth_804017471e4a",
      "category": "location",
      "human_confirmed_by": "local-runtime-owner",
      "node_id": "authfact-scene-auth_804017471e4a",
      "promotion_kind": "human_confirmation",
      "source": "authoritative_script_fact_feed",
      "source_candidate_fact_id": "fact_b3f222e8b8eb",
      "source_revision_id": "scrrev_18861d03750a458b",
      "text": "海边礁石"
    }
  ],
  "revision_node_ids": [
    "scripttruth-revision-scrrev_18861d03750a458b-02674232e5cfe7b7"
  ]
}
```

单节点样例（含溯源字段）：

```json
{
  "category": "entity",
  "metadata": {
    "authoritative_fact_id": "auth_1853af9a5b3e",
    "display_name": "林悦",
    "entity_id": "character_2_林悦",
    "entity_kind": "character",
    "field_path": "identity.display_name",
    "human_confirmed_by": "local-runtime-owner",
    "promotion_kind": "human_confirmation",
    "source": "authoritative_script_fact_feed",
    "source_candidate_fact_id": "fact_86121af18268",
    "source_confidence": 0.9,
    "source_revision_digest": "02674232e5cfe7b78663b63654d4e9acc4e901a43256a08f26657de87a49e3f7",
    "source_revision_id": "scrrev_18861d03750a458b",
    "text": "林悦"
  },
  "node_id": "authfact-character-auth_1853af9a5b3e",
  "state": "active"
}
```

### 步骤 6：换剧本版本 → 旧权威失效，审计保留

把「老式邮局」改成「海边老式邮局」，创建新 revision 并 refresh。
旧 authoritative 全部 `invalidated_by_revision`；当前 authoritative 为空；
`change_log` **累加保留**（含先前 accept/reject）。

```json
{
  "active_authoritative_after_refresh": [],
  "change_log_after_count": 10,
  "change_log_before_count": 8,
  "has_script_revision_changed_reason": true,
  "invalidated_count": 6,
  "invalidated_sample": [
    {
      "invalidated_by_revision_id": "scrrev_8aed539e609f4a4c",
      "source_revision_id": "scrrev_18861d03750a458b",
      "text": "苏晴",
      "validity": "invalidated_by_revision"
    },
    {
      "invalidated_by_revision_id": "scrrev_8aed539e609f4a4c",
      "source_revision_id": "scrrev_18861d03750a458b",
      "text": "老王",
      "validity": "invalidated_by_revision"
    },
    {
      "invalidated_by_revision_id": "scrrev_8aed539e609f4a4c",
      "source_revision_id": "scrrev_18861d03750a458b",
      "text": "林悦",
      "validity": "invalidated_by_revision"
    },
    {
      "invalidated_by_revision_id": "scrrev_8aed539e609f4a4c",
      "source_revision_id": "scrrev_18861d03750a458b",
      "text": "老式邮局",
      "validity": "invalidated_by_revision"
    },
    {
      "invalidated_by_revision_id": "scrrev_8aed539e609f4a4c",
      "source_revision_id": "scrrev_18861d03750a458b",
      "text": "海边礁石",
      "validity": "invalidated_by_revision"
    }
  ],
  "new_candidate_scene_present": true,
  "new_revision_id": "scrrev_8aed539e609f4a4c",
  "old_revision_id": "scrrev_18861d03750a458b",
  "prior_change_ids_retained": true
}
```

---

## 关键证明点

| 证明点 | 证据 |
|---|---|
| 垃圾数据被拦住 | 注入「苏晴没」后仍 pending；reject 后 authoritative 无此名，Graph 亦无 |
| 人工确认后下游正确 | `resolved.characters=['苏晴', '老王', '林悦']` / `scenes=['老式邮局', '海边礁石', '苏晴的房间']` |
| 溯源链路完整 | Graph 节点带 `authoritative_fact_id` / `source_candidate_fact_id` / `source_revision_id=scrrev_18861d03750a458b` / `promotion_kind=human_confirmation` |
| 换版本旧数据失效 | invalidated=6；refresh 后 authoritative=`[]`；change_log 8→10 且旧 id 保留 |
| 默认关闭仍坏 | Part 1 characters=`['苏晴没', '从远处', '道他可能']` + verdict=`PASS` |

### 断言清单

- [PASS] legacy still extracts junk characters — got ['苏晴没', '从远处', '道他可能']
- [PASS] legacy validation still PASS despite junk — {'verdict': 'PASS', 'P0': 0, 'P1': 0}
- [PASS] shadow extraction absent when flag off — shadow_extraction unexpectedly present
- [PASS] script truth revision id is scrrev_* — scrrev_18861d03750a458b
- [PASS] improved shadow characters are 苏晴/老王/林悦 — ['苏晴', '老王', '林悦']
- [PASS] improved shadow scenes are expected — ['老式邮局', '海边礁石', '苏晴的房间']
- [PASS] candidate path still legacy until confirmation (shadow-only) — ['苏晴没', '从远处', '道他可能']
- [PASS] reuse flag embeds scrrev_* in M6 candidate — scrrev_18861d03750a458b
- [PASS] refresh surfaces real character candidates — ['林悦', '海边礁石', '老式邮局', '老王', '苏晴', '苏晴的房间']
- [PASS] no automatic authoritative facts yet — []
- [PASS] junk stays pending candidate with high confidence — {
  "authoritative_still_empty": true,
  "confidence": 0.96,
  "fact_id": "fact_38a9503a4509",
  "review_decision": "pending",
  "status": "extracted_from_text",
  "text": "苏晴没",
  "uncertainty_note": "legacy regex fragment; not a real name",
  "why_not_auto_authoritative": "status=extracted_from_text + high confidence is still a CandidateFact; promote_candidate_fact requires human_confirmed (or a named deterministic check). Confidence alone never promotes."
}
- [PASS] junk never appears in authoritative — ['苏晴', '老王', '林悦', '老式邮局', '海边礁石', '苏晴的房间']
- [PASS] downstream resolve has correct characters — ['苏晴', '老王', '林悦']
- [PASS] downstream resolve has correct scenes — ['老式邮局', '海边礁石', '苏晴的房间']
- [PASS] graph contains confirmed character nodes — ['林悦', '海边礁石', '老式邮局', '老王', '苏晴', '苏晴的房间']
- [PASS] graph does not contain junk 苏晴没 — ['林悦', '海边礁石', '老式邮局', '老王', '苏晴', '苏晴的房间']
- [PASS] revision nodes are namespaced (no silent collision key) — ['scripttruth-revision-scrrev_18861d03750a458b-02674232e5cfe7b7']
- [PASS] every authfact node has full provenance — [
  {
    "authoritative_fact_id": "auth_1853af9a5b3e",
    "category": "entity",
    "human_confirmed_by": "local-runtime-owner",
    "node_id": "authfact-character-auth_1853af9a5b3e",
    "promotion_kind": "human_confirmation",
    "source": "authoritative_script_fact_feed",
    "source_candidate_fact_id": "fact_86121af18268",
    "source_revision_id": "scrrev_18861d03750a458b",
    "text": "林悦"
  },
  {
    "authoritative_fact_id": "auth_c016da4e5cd8",
    "category": "entity",
    "human_confirmed_by": "local-runtime-owner",
    "node_id": "authfact-character-auth_c016da4e5cd8",
    "promotion_kind": "human_confirmation",
    "source": "authoritative_script_fact_feed",
    "source_candidate_fact_id": "fact_0692d0c2ade5",
    "source_revision_id": "scrrev_18861d03750
  … (truncated)
}
- [PASS] old authoritative facts invalidated on revision change — invalidated=6 before_active=6
- [PASS] change_log accumulates across revision refresh — before=8 after=10
- [PASS] new revision needs re-confirmation (no auto authority) — []

---

## 如何自己复现

```bash
cd /path/to/repo
.venv/bin/python docs/internal-notes/run_before_after_demo.py
```

脚本会：
1. 用 tempfile 建本地 Runtime（不碰 /opt / 线上）
2. 走真实 FastAPI TestClient 路由（与 Scenario A/B/C 同模式）
3. 重写本报告与 `before-after-demo-20260803.evidence.json`
4. 断言失败则以非零退出码退出

