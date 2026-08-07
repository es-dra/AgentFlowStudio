# 缺失证据评测：真实跑数与分析（v0.1）

| 项 | 值 |
|---|---|
| 日期 | 2026-08-05 |
| 范围 | `../../missing-evidence-eval-scope-memo-20260805.md`（槽级 + `scene_cast` 关系级） |
| 金标 | `gold_cases.json`（M1–M5） |
| 计分 | `score_missing_evidence.py` |
| 跑数（历史） | 曾用 `run_against_runtime.py`（依赖 `apps.api`）生成 `runtime_candidates.json` |
| 本 research 切片 | **不带** `run_against_runtime.py`；离线重跑只对已检入的结构化 candidates 计分 |
| 生产代码 | **未改动** |

---

## 1. 金标一览

| ID | 类型 | 考什么 |
|---|---|---|
| M1 | 关系 missing 正例 | 地下车库 × 陈默必须 missing；会议室双方与车库×李薇 present |
| M2 | 槽级 missing 正例 | `named_characters` + `main_scenes` 均应 missing |
| M3 | 槽级 **反例**（防假阳性） | 有字面时两槽都不得 missing；咖啡馆出演 present |
| M4 | 关系 **正例**（防过度保守） | 书房内叙述+对白字面 → 两人均不得标 missing |
| M5 | 槽级部分缺失 | 仅 `main_scenes` missing；`named_characters` 不得连带 missing |

---

## 2. 计分器自检（合成）

| 模式 | accuracy | FP missing rate | FN missing rate | 说明 |
|---|---:|---:|---:|---|
| perfect | 1.0 | 0.0 | 0.0 | 覆盖率 1.0 |
| over_missing | 0.222 | **1.0** | 0.0 | 到处标 missing → FP 打满 |
| under_missing | 0.778 | 0.0 | **1.0** | 从不标 missing → FN 打满 |

覆盖率字段与质量指标同处 summary：`relation_judgment_coverage_rate`、`cases_with_prerequisite_gaps*`、`cases_with_uncovered_relations*`。

---

## 3. 真实 runtime 结果

来源：`runtime_candidates.json` + `runtime_score_report.json`。

### Summary

| 指标 | 值 |
|---|---|
| case_count | 5 |
| relation_judgment_coverage_rate | **1.0**（8/8） |
| prerequisite gaps | **0** |
| judgment_count_scored | 18 |
| missing_judgment_accuracy | **1.0** |
| false_positive_missing_rate | **0.0** |
| false_negative_missing_rate | **0.0** |
| TP / TN / FP / FN | 4 / 14 / 0 / 0 |

### 用例级

| 用例 | FP | FN | 缺口 | 备注 |
|---|---:|---:|---|---|
| M1 | 0 | 0 | — | 车库×陈默 → `missing`；其余 cast → `candidate` |
| M2 | 0 | 0 | — | 两槽均 missing；无人物/场景资产，未跑关系（金标也无关系断言） |
| M3 | 0 | 0 | — | 槽非 missing；咖啡馆×两人 present |
| M4 | 0 | 0 | — | 叙述句「陈默坐…李薇站…」字面命中，未过度 missing |
| M5 | 0 | 0 | — | 仅 `main_scenes` missing |

---

## 4. 如实解读（避免虚高叙事）

1. **在本冻结范围内、且金标按现有确定性+ #231 行为编写时，活路径全部命中。**
   这说明备忘里的语义与实现一致，评测脚手架可用——**不是**「缺失证据作为理解问题已彻底解决」。

2. **覆盖率 100% 是因为 M1/M3/M4 的人物场景都能被现提取器抽出。**
   若金标依赖间接提及才出现的人名（如长文里的「顾衡」），关系断言会进 `uncovered`，accuracy 不会把它们算成 FN——与别名课一致。

3. **本集未覆盖的失败模式（已知，不在分数里）：**
   - Profile/Beat facet missing（master 无闭环）
   - 匿名 `name_missing`（schema 硬限制）
   - 「说起了X」是否算在场（I3 政策）——会改写 M1 真值，未纳入

4. **假阳性 missing 守卫（M3/M4）通过**：当前实现没有「过度到处标 missing」；主要风险仍在别的层（漏抽人导致槽级假 missing，或将来模型乱填导致假 FN）。

---

## 5. 一句话

**缺失证据离线评测已可执行；在槽级 + scene_cast 的五条金标上，现网提取/归属路径真实跑分为满分且覆盖率满，符合「范围内机制已到位」而非「全局缺失问题消失」。**
