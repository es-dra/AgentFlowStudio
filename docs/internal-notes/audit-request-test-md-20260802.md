
修第三、四个问题，一起处理，因为根因相关：Production Graph 节点被静默覆盖，以及"权威账本已确认但图写入失败"导致的卡死状态。

## 问题 1：节点覆盖（cross-flag collision）

独立审计已经实测复现：同时开启 `AFS_M6_REUSE_SCRIPT_TRUTH_REVISION_ID` 和 `AFS_CANDIDATE_FACTS_FEED_PRODUCTION_GRAPH` 时，M6 candidate 和权威事实 feed 会用同一个 `scrrev_*` 当 Production Graph 的 revision node key，但两边对应的内容/digest 不一样（`runtime_production_graph.py:230` 是无条件覆盖），后写的一方直接覆盖前写的一方，没有任何冲突检测。

## 问题 2：卡死状态（partial commit）

`apps/api/runtime_candidate_confirmation.py:1099` 附近：accept/edit_confirm 操作先保存权威账本（标记为"已决定"），再尝试写入 Production Graph。如果 Graph 写入失败，账本已经是"已决定"状态，没法重试——再次尝试会报 "fact already decided" 错误，这条记录就卡在"确认了但没进图"的状态，无法恢复。

## 目标（不要求今天彻底解决图的通用并发模型，先做到诚实、安全、可恢复）

### 针对问题 1：节点身份区分

不要求"合并"两种不同内容到一个节点，而是**避免用同一个 key 表示不同语义的东西**：

1. 想清楚：M6 candidate 产出的 revision node，和权威事实 feed 产出的 revision node，语义上到底是不是同一件事？如果不完全是（比如 M6 可能包含扩写文本），应该给它们不同的 node key 或者不同的 category，而不是共用一个 key 硬覆盖
2. 具体方案由你判断怎么做风险最小（比如给权威事实 feed 产生的 revision node 用带前缀的 key，或者在 metadata 里明确标注"这个节点的内容来自哪条路径"，防止语义不同的内容互相覆盖却看不出来）
3. 这一步还是要 feature flag 保护，不要动默认行为

### 针对问题 2：让失败可恢复

1. 至少要做到：graph feed 失败时，不能让账本卡在一个"已决定但无法重试"的死状态
2. 简单方案：账本记录里加一个显式的 `graph_feed_status`（比如 `pending` / `succeeded` / `failed`），accept/edit_confirm 成功但 graph 写入失败时，标记为 `failed`，并且允许针对这条记录**单独重试图写入**（不需要重新走一遍人工确认流程）
3. 想清楚失败时要不要把整个 HTTP 请求返回成功还是失败——如果账本已经确认成功、只是图写入失败，可能应该返回部分成功的状态，而不是笼统的 4xx/5xx，让调用方知道"人工确认部分是好的，图写入部分需要重试"

## 测试

- 复现独立审计发现的碰撞场景，验证修复后不再发生静默覆盖（要么用不同 key 避免了碰撞，要么有明确的冲突检测拒绝写入）
- 复现 partial-commit 场景（强制让 graph 写入失败），验证：账本状态清晰可查（不是笼统的"already decided"卡住），并且能重试图写入部分

## 范围

- 如果做完发现这个问题比想象中牵连更广（比如需要改 Production Graph 核心的写入语义），如实说明，先给我一个"复杂度评估+建议方案"，不要为了看起来完成就强行简化处理掉一个数据一致性问题

