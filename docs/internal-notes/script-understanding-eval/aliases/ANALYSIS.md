# 确定性别名提案：真实计分与分析（v0.1）

| 项 | 值 |
|---|---|
| 日期 | 2026-08-05 |
| 提案模块 | `deterministic_alias_proposer.py`（`deterministic_alias_proposer_v0.1`） + production gated alias proposals |
| 候选输出 | `deterministic_candidates.json` |
| 计分输出 | `deterministic_score_report.json` |
| 计分器 | `score_alias_linking.py` × `gold_cases.json` |
| 生产代码 | 已接入 `analysis-candidates/extract` 候选旁路；`AFS_ENABLE_ALIAS_LINK_PROPOSALS` 默认关闭 |

## 1. 集级真实分数

来自 `deterministic_score_report.json` summary（真代码跑出，非手写假数据）：

| 指标 | 值 |
|---|---|
| case_count | 8 |
| hard_fail_case_count | **0** |
| linkable_gold_cluster_count | 5 |
| linkable_gold_clusters_scored | **4** |
| linkable_cluster_coverage_rate | **0.8** |
| cases_missing_fsr_score_count | **1**（A8） |
| macro_bcubed_precision | 1.0 |
| macro_bcubed_recall | 1.0 |
| macro_bcubed_f1 | 1.0 |
| macro_false_split_rate | 0.0（仅对「宇宙内多人金标簇」有定义的用例宏平均） |
| macro_false_merge_rate | 0.0 |

**读数：** macro F1=1.0 **同时** coverage=0.8——5 个需要链接判断的金标簇里有 4 个进入 FSR 宇宙；A8 因小名表面未抽出而不计 FSR。不能把 macro F1 读成「别名问题已解决」。

## 2. 用例级结果

| 用例 | 现象 | BCubed F1 | FSR | FMR | HARD_FAIL | 抽取缺口 | 提案是否按设计覆盖 |
|---|---|---:|---:|---:|---|---|---|
| A1 | 姓+职衔 | 1.0 | 0.0 | 0.0 | 否 | — | 是：`陈默`≡`陈师傅` |
| A2 | 显式外号 | 1.0 | 0.0 | 0.0 | 否 | — | 是：标签 `外号「阿可」` |
| A3 | 老X | 1.0 | 0.0 | 0.0 | 否 | — | 是：`陈默`≡`老陈` |
| A4 | 全名截短 | 1.0 | 0.0 | 0.0 | 否 | — | 是：`林悦安`≡`悦安`，同场唯一后缀锚点 |
| A5 | 同姓反例 | 1.0 | null | 0.0 | 否 | — | 是：未合并陈默/陈明 |
| A6 | 场外职衔 | 1.0 | null | 0.0 | 否 | — | 是：未链 `陈默`–`陈师傅` |
| A7 | week 回归 | 1.0 | null | 0.0 | 否 | `林悦` | 部分：人物不乱链；林悦未抽到 |
| A8 | 小名/亲属 | 1.0* | null* | 0.0 | 否 | `浩子` | **否（仍刻意不做无标注小名）**；未误链「妈」 |

\*A8 的 F1=1.0 只说明「已抽出的那一半」自成一簇且无错并；**不能**解读为无标注小名已解决。

### 各案提案摘要（来自 candidates）

- **A1:** `surname_title_same_scene`：陈默 ↔ 陈师傅
- **A2:** `explicit_aka_label`：周可 ↔ 阿可
- **A3:** `lao_x_unique_anchor`：陈默 ↔ 老陈
- **A4:** `given_name_suffix_same_scene_unique_anchor`：林悦安 ↔ 悦安
- **A5–A8:** 无链接提案（A5/A6 正确沉默；A8 能力外沉默；A7 无别名可链）

## 3. must_not_link / HARD_FAIL

**全部 8 案 `hard_fail=false`，无 must_not_link 违规。**

关键守卫实际生效点：

- **A5：** 同姓锚点 ≥2（陈默、陈明）时，不把「陈先生」或任何同姓职衔并到其中一人。
- **A6：** `陈师傅` 出现在 `远处有人喊：` 之后 → `offstage` 抑制 L2；`王师傅` 本身是锚点全名，不反向并到陈默。

## 4. 实现中修过的一处规则 bug（不是过拟合）

首轮跑分时 **A1 FSR=1**：对白里的「陈师傅」被「门外有人喊。」的宽松邻近匹配误标为 offstage，核心正例被误杀。

处理：把 offstage 收成「`喊：`/`喊:` 后紧接的呼喊内容」才抑制（对齐 A6 句式），而不是「附近出现过喊字」。

这是启发式假阳性修复，不是给 A1 写死字符串特例。收紧后 A6 仍保持 offstage=True、不链陈默。

## 5. 哪些好、哪些不好、为什么

### 好（符合 DESIGN 确定性覆盖带）

1. **A1 姓+职衔同场** — 唯一同姓本名锚点 + 对白中的 `S+师傅` → 高置信提案。
2. **A2 显式外号** — 标签 `（外号「…」）` 几乎无歧义。
3. **A3 老X** — 全剧仅一个 `陈*` 本名锚点时，`老陈` 可链；这是「全剧表面索引」，不是跨场剧情推理。
4. **A5/A6 反例** — FMR=0 且无 HARD_FAIL；假合并守卫按设计工作。

### 不好 / 未覆盖（分数好看但能力空洞）

1. **A8 小名 `浩子`**
   - 无显式「外号」标注；不在 L1–L3。
   - 同样因未抽出而不进宇宙，macro 被美化。
   - 「浩子」不是 `陈浩` 的连续后缀，靠“名 + 子”是一条昵称经验规则，容易把风格化称呼硬并到唯一同字锚点；本轮不为 coverage 放宽假合并防线。
   - 「妈」未当别名链出（符合 DESIGN 弱处理）；也未误链到陈浩。

2. **A7 `林悦`**
   - 仅出现在「寄给林悦？」叙事/对白宾语，非 speaker/标签 → 抽取缺口。
   - 身份链接层无错并；问题在提及发现，不在别名规则。

### 与 DESIGN.md 预期对比

| DESIGN 预期 | 实际 |
|---|---|
| L1 显式 aka → 高置信 | 符合（A2） |
| L2 同场姓+职衔 → 高置信 | 符合（A1）；场外呼喊抑制符合（A6） |
| L3 保守老X + 无冲突 | 符合（A3）；双同姓则不链（由 A5 机制覆盖） |
| L4 截短弱规则 / 默认可关 | **部分做**：仅同场、唯一锚点、全名后缀独立表面（A4） |
| 小名无标注 / 亲属称呼 | **未做硬别名**；A8 符合「不做」而非「做对」 |
| 代词 / 无字形交集外号 | 未做（本集未考） |
| 反例假合并必须守住 | **守住**（0 HARD_FAIL） |

**总体：** 在「形态可检验 + 锚点唯一」带上，真实表现**符合预期偏正面**（A1–A4、A5–A6）。
宏平均 F1=1.0 **仍好于「能力全覆盖」的错觉**——A8 的失败被抽取缺口从 FSR 分母里拿掉了。报告以用例表为准，不以 macro 作对外成功声明。

## 6. 边界重申

- 输出只是 **proposal clusters / alias_link_proposals**，不是确认，不是 `merge_alias`，不是 Graph 权威。
- production extract 接入受 `AFS_ENABLE_ALIAS_LINK_PROPOSALS` 保护，默认关闭。
- 未为刷分实现无标注小名启发式。

## 7. 建议的下一步（等你确认，不擅自推 PR）

1. 计分器增加「能力内子集」报表（只对 DESIGN 声明覆盖的 A1/A2/A3/A4/A5/A6），避免 macro 美化。
2. 对 A8 在金标侧单独报 `coverage=out_of_scope` 与 `alias_unresolved=true`。
3. Studio 若要展示提案，应只显示候选和 `merge_alias` 动作入口，不增加自动接受路径。
