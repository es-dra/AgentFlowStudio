# 判断器拆字段：人物指称 vs 在场（2026-08-06）

探索性修复。不接生产、不推送。发现层未改。

## 改动

`tools/indirect_mention_llm_prototype.py` 输出改为：

| 字段 | 含义 |
|---|---|
| `refers_to_real_character` (+ conf/reason) | 字符串本身是否指向值得追踪的故事人物 |
| `is_present_in_scene` (+ conf/reason) | 该人物此次是否有直接出场证据 |
| `is_indirect_mention`（派生） | `refers && !present` |

闭环提案写入同步更新（`discover_judge`）。`is_character` 仅作 **presence 旧别名**。

## 聚焦验证（10 次真实调用，~39s）

### 正例：间接提及定义组合

| 案例 | refers | present | indirect | 预期 |
|---|---|---|---|---|
| 沈岚 | **true** | false | **true** | ✓ |
| 江澄 | **true** | false | **true** | ✓ |
| 顾衡 | **true** | false | **true** | ✓ |
| 柯衡 | **true** | false | **true** | ✓ |

四个关键 I1 **全部**落到 `refers=true + present=false`。今天上午的「问错问题」已对症。

### 悦安（在场别名）

| 轮次 | refers | present | 说明 |
|---|---|---|---|
| 初跑 | true | **false** | 承认是林悦别名，但不算在场 |
| prompt 收紧后再跑 | true | **false** | 仍坚持：录音称呼 ≠ 当场以该名出场 |

**边界**：模型把「别名指向在场者」判成间接提及，而不是 `present=true`。若产品要把在场别名算出场，prompt/规则还要再加硬例子；本次未强行拟合。

### 噪声回归

| 案例 | 初跑 refers | 收紧后再跑 | 说明 |
|---|---|---|---|
| 留局待领 | false | — | ✓ |
| 周五前提交 | false | — | ✓ |
| 钥匙在三零二的钟里。 | false | — | ✓ |
| **别自己拆** | **true（误）** | **false ✓** | 初跑把「对苏晴说的话」当成指人 |
| **样本冷藏** | **true（误）** | **false ✓** | 初跑答成上下文里的柯衡，串题 |

拆字段后一度把 `refers` 问松：模型会「看见附近有人就 true」。补了「只评价疑似提及字符串本身」后，抽测噪声恢复。

## 诚实评估

**解决了今天的核心问题**：间接提及终于有可操作定义——`refers_to_real_character=true` 且 `is_present_in_scene=false`。沈岚/江澄/顾衡/柯衡均命中。

**新边界 / 代价**：

1. **字段拆分会暂时放松噪声门**（别自己拆、样本冷藏初跑失败）；必须显式约束「评字符串本身」。收紧后抽测恢复，但说明双字段比单字段更吃 prompt 纪律。
2. **悦安**：`refers` 对、`present` 偏保守——别名/在场绑定仍不稳。
3. **样本冷藏串题**暴露上下文窗口干扰：宽窗口里有更抢戏的人名时，模型可能答错对象；生产上或需更短窗口 / 更强「只评 mention」约束。

**结论**：双字段设计方向正确，值得保留；不要接生产前还需要：别名在场规则样例 + 噪声/`mention` 锚定的回归集。

产物：

- `focused_validation.json`（首轮 10 案）
- `prompt_tighten_retry.json`（失败案复测）
