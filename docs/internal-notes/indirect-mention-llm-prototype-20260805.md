# 间接提及 LLM 原型验证（2026-08-05）

范围：只读独立脚本 `tools/indirect_mention_llm_prototype.py`；远程
`prompt_optimizer`（`/etc/afs/providers.local.json`）；**不**写入
analysis-candidates / 权威身份。

## 调用统计

- 调用次数：**5**（全部成功）
- 墙钟合计：**~17.3s**（单次约 2.3–7.4s）
- Provider：`prompt_optimizer` / 远程 LLM（非本地模型）

## 案例结果

| case | 提及 | 期望 | LLM | confidence | 我的评判 |
|------|------|------|-----|------------|----------|
| neg_memory_chenmo | 陈默 | false | **false** | 0.95 | 准 |
| neg_letter_guheng | 顾衡 | false / 低置信 | **false** | **0.30** | 方向准；置信偏保守/不稳 |
| pos_dialogue_chenmo | 陈默 | true | **true** | 0.95 | 准 |
| boundary_suheng_mentioned | 苏衡 | 倾向 false | **false** | 0.90 | 准 |
| pos_dialogue_liuzheng | 刘正 | true | **true** | 1.00 | 准 |

完整 JSON：`docs/internal-notes/indirect-mention-llm-prototype-20260805.json`

## 诚实评估

**这次纯判断能力看起来靠谱（5/5 方向正确）**，值得做**下一小步**，但还不能上生产主流程。

靠谱之处：
- 负例（回忆提及、信件/转述亡父）都压成 `false`
- 正例（有对白+动作、无「人物：」标签）都抬成 `true`
- 边界「苏衡」也被正确压掉

仍未验证 / 新问题：
1. **发现层没测**：本次是「给定片段 + 给定提及」的闭集判断，不是从全文捞出可疑专名。
2. **置信度校准不稳**：顾衡判 false 但只有 0.30——同规则下苏衡却有 0.90；若用阈值自动过滤会抖动。
3. **片段窗口敏感**：真实系统若裁错上下文（只给汇款单一行、或把对白截断），结论可能翻。
4. **仍是提案级能力**：即使很准，也只能进非权威候选，不能自动进 Asset Bible。

**建议**：可以继续，但下一步应是「候选发现 + 判断」的最小闭环原型（仍 flag 关闭、只提案），先别接 confirm/merge。
