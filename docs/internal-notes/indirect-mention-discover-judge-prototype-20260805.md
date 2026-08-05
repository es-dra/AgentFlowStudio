# 间接提及：发现 + 判断闭环原型（2026-08-05）

状态：**探索性原型**。不接 `analysis-candidates`，不接 confirm/merge，不加生产 feature flag。

相关代码：

- `tools/indirect_mention_discovery.py` — 发现（复用 `_is_person_name` + 跳过 label/speaker/bio 证据 span）
- `tools/indirect_mention_llm_prototype.py` — 既有判断器
- `tools/indirect_mention_discover_judge_prototype.py` — 闭环 runner
- 结果 JSON：`docs/internal-notes/indirect-mention-discover-judge-prototype-20260805.json`
- 上一轮纯判断：`docs/internal-notes/indirect-mention-llm-prototype-20260805.md`

## 发现策略（刻意收紧）

开放全文 NER（最长匹配扫 2–4 字）在这两部剧本上会吐出 **~500** 个噪声串，不可用。

本原型只做高精度线索：

1. 引号内 2–4 字且通过 `_is_person_name`
2. 提及句式：`说起了/想起了/收款人是/收件人写着…`
3. 极窄亲属线索：`你爸|我爸` + 短名 + 固定后续（以前/去世/案…）
4. 命中 span 若已与 label/speaker/bio 证据重叠 → 丢弃

## 长剧本真实跑数

| 项 | 值 |
|---|---|
| 剧本 | `01_echo_inn_long.txt` + `02_night_post_long.txt` |
| 发现总数 | **12**（4 + 8） |
| LLM 调用 | **12**（全部成功） |
| 墙钟 | **~30s** |
| Provider | `prompt_optimizer` / 远程 |

### 01 回声旅馆（4）

| mention | is_character | conf | 我的评判 |
|---|---|---|---|
| 苏衡 | false | 0.30 | 窗口对准引号幻听；方向可接受。注：抽取侧已把录音 speaker「苏衡」收进人物表（`already_extracted=true`） |
| 别自己拆 | false | 0.95 | 准（引号噪声，LLM 滤掉） |
| 默记修缮 | false | 0.90 | 准（店招/喷漆） |
| 悦安 | **true** | 0.95 | 合理：林悦别名；不是「新角色发现」，更像 alias 线索 |

### 02 夜班邮筒（8）

| mention | is_character | conf | 我的评判 |
|---|---|---|---|
| 顾衡 | false | 0.95 | **关键 I1 命中**：抽取表没有顾衡；发现+判断都对 |
| 留局待领 / 夜班邮筒 / 失踪汇款 / 晚上见 | false | 0.95 | 准（引号业务词/手势，噪声） |
| 默记 | false | 0.20 | 方向准；置信又虚（同上一轮校准问题） |
| 晚晚 | false | 0.95 | 保守可接受（信中称呼；也可能是顾晚小名/别名） |
| 陈默 | false | 0.95 | 对该引号窗口准（草稿划掉）；但剧本后文陈默实际出场——发现只抓到引号处 |

## 诚实评估

### 发现准不准？

- **召回（I1 有姓名叙事）**：顾衡 ✅；引号「苏衡」✅；探针句式路径仍在（本两部剧本里没有「说起了X」句，但单测覆盖）。
- **噪声**：引号门控仍会捞到大量非人名（留局待领、别自己拆、晚上见…）。**约 12 个发现里有 ~7 个明显非人名**，靠 LLM 后过滤。
- **漏召回**：不在引号/句式里的纯散文首现姓名，本原型**故意不抓**（开放 NER 已证实不可控）。
- **与抽取重叠**：`already_extracted_as_character` 能标出「抽取已有 / 发现仍报」的冲突（苏衡、陈默），有利于人工审，但闭环本身不会去重权威。

### 加上发现之后整体可靠性？

比「给定片段+已知提及」那轮 **更接近真实问题**，也暴露了新瓶颈：

1. **发现精度是主成本**：多数 LLM 调用在否决引号噪声，不是在判真角色。
2. **判断器仍可用**：噪声项几乎全被判 false；顾衡/悦安等关键项方向正确。
3. **置信度仍不稳**：苏衡 0.30、默记 0.20 vs 其它 false 0.95——**不能靠阈值自动化**。
4. **窗口效应**：只喂局部上下文时，会把「别处已出场」的名字判成 false（02 末「陈默」）。

### 要不要继续？

**值得再做一小步，但仍是原型**：优先改进发现门控（例如引号白名单/黑名、排除已知场景词与业务词、对 `already_extracted` 默认降权），而不是接生产。
**现在还不该**进 `analysis-candidates` / confirm / merge。

## 非目标（本次明确不做）

- 不接生产主流程、不加 feature flag
- 不写权威身份、不做 merge_alias / merge_scene_name
- 不改 PR 框架里「维度覆盖」类结论表述；本批仅作探索附件
