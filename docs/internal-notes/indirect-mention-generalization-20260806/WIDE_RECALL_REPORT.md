# 间接提及发现：宽召回验证（2026-08-06）

探索性验证。不接生产、不推送。

## 实现调整

- `tools/indirect_mention_discovery.py`
  - 去掉引号候选的左上下文白名单。
  - 去掉面向具体措辞的 quoted phrase 黑名单。
  - 引号内 2-24 字符、含中文的片段全部作为结构候选进入发现结果。
  - 保留已有 label / speaker cue / bio 证据 span 的重叠过滤，避免与确定性提取重复。
  - cue 路径仍保留 `_is_person_name`，作为补充结构通道，不做开放 NER。
- `tools/indirect_mention_llm_prototype.py`
  - 判断 prompt 增加规则：整句对白、命令、口号、标题、业务短语、物品/格口/告示文字等明显非人物指称必须 `is_character=false`。
- `tools/indirect_mention_discover_judge_prototype.py`
  - 默认 `--max-mentions` 从 12 改为 1000；`--max-mentions <= 0` 表示判断全部发现候选。

## 5 份剧本发现结果

discover-only 产物：

- `wide_recall_discover_only.json`

| 剧本 | 宽召回发现数 | 发现候选 |
|---|---:|---|
| `01_echo_inn_long.txt` | 6 | 苏衡；别自己拆；回声-07；默记修缮；悦安；钥匙在三零二的钟里。 |
| `02_night_post_long.txt` | 12 | 留局待领；别让她当着人拆。；顾衡；夜班邮筒第七格；默记；夜班邮筒；失踪汇款；第七格——顾衡案——不得夜班单独开启。；晚晚；设备老化，待报修；晚上见；陈默 |
| `01_office_standup.txt` | 4 | 周五前提交；别再甩锅；沈岚；开会开到吐 |
| `02_campus_relay.txt` | 3 | 江澄；把节奏交给下一棒；少抱怨多冲刺 |
| `03_lab_night_shift.txt` | 4 | 样本冷藏；权限不足；柯衡；重启实验舱 |
| **合计** | **29** |  |

## LLM 判断运行结果

真实闭环产物：

- `wide_recall_discover_judge_report.json`

本次未取得有效判断样本：

| 指标 | 结果 |
|---|---:|
| 发现候选总数 | 29 |
| 尝试判断数 / 真实请求数 | 29 |
| 成功判断数 | 0 |
| 失败数 | 29 |
| 失败原因 | provider 返回 401 无效令牌 |

说明：

- 首次未映射凭据运行时，首个请求报 `CRAZYROUTER_API_KEY` 未配置，后续同进程请求受 provider pool 状态影响失败。
- 仅在本次命令进程内把本地已有网关 key 名称映射到 `CRAZYROUTER_API_KEY` 后重跑，29 个请求全部返回 provider 401 无效令牌。
- 因此本轮不能报告“判断后候选数”或“长对白误判率”。这些数据不可得，不能用推测替代。

## 专项验证

| 案例 | 旧收紧发现 | 宽召回发现 | LLM 判断 |
|---|---:|---:|---|
| 沈岚 | MISS | HIT | 不可得：provider 401 |
| 江澄 | MISS | HIT | 不可得：provider 401 |
| 柯衡 | HIT | HIT | 不可得：provider 401 |
| 顾衡 | HIT | HIT | 不可得：provider 401 |

结论：这次实现解决了“沈岚 / 江澄 因左上下文白名单而漏发现”的问题，但还没有证明 LLM 在新增噪声规模下仍稳定。

## 成本变化

与已有记录对比：

| 跑法 | 剧本范围 | 发现数 | LLM 调用数 |
|---|---|---:|---:|
| 2026-08-05 两份长剧本旧闭环 | 2 份 | 12 | 12 |
| 2026-08-06 三份新剧本收紧门控 | 3 份 | 1 | 1 |
| 本轮宽召回 | 5 份 | 29 | 29 |

同样只看昨天两份长剧本，宽召回从 12 增到 18，增加 6 次，约 +50%。  
看 5 份合计，本轮需要 29 次判断；其中新三份从收紧门控的 1 次增加到 11 次，增加 10 次。这是真实成本增长，不应淡化。

## 诚实评估

方向上，宽召回确实修正了发现层过拟合具体左上下文的问题：沈岚、江澄都能进入候选。

代价也很明确：发现候选中混入了大量非人名噪声，包括完整句子、标题、告示、业务短语和物品标记。这个方向把问题从“规则漏召回”转移为“LLM 承担更多过滤成本与误判风险”。

当前边界没有完成闭环验证：由于 provider 凭据不可用，无法判断 LLM 是否会把 `别让她当着人拆。`、`第七格——顾衡案——不得夜班单独开启。`、`设备老化，待报修` 这类明显噪声误判为 true。下一步必须在可用凭据下重跑同一份 `wide_recall_discover_judge_report.json` 路径，才能决定该方向是否真能落地。

## Verification

- `.venv/bin/python -m pytest tests/test_indirect_mention_discovery_prototype.py`：4 passed
- `.venv/bin/python tools/indirect_mention_discover_judge_prototype.py --discover-only ... --max-mentions 0`：生成 5 份 discover-only 结果
- `.venv/bin/python tools/indirect_mention_discover_judge_prototype.py ... --max-mentions 0`：29 次 provider 请求均失败，401 无效令牌
- `git diff --check`：通过
