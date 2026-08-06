# 运行时模块拆分（2026-08-06）：embedded screenplay safety

| 项 | 值 |
|---|---|
| tip worktree | `codex/real-understanding-quality-20260805` |
| 动作 | 盘点 + 依赖风险分析 + **一次有分量的纯结构拆分** |
| 原则 | 不改 API / 数据结构 / 业务逻辑；零行为变化 |

---

## 1. 最新模块大小盘点

### 1.1 `apps/api/` Top

| 行数 | 文件 | 备注 |
|---:|---|---|
| 3634 | `runtime_script_core_truth.py` | 过大；今日间接提及等主线仍在此膨胀 |
| 3438 | `runtime_video_admission.py` | 过大；fan-in 广（dispatch/preflight/tools） |
| 2725 | `runtime_asset_bible.py` | 过大 |
| 2648 | `runtime_image_admission.py` | 过大；与 video admission 耦合 |
| **2020→1488** | `runtime_embedded_creative_actions.py` | **本次拆分目标** |
| 2007 | `runtime_production_control.py` | 过大 |
| … | 其余 ~900–1400 | 偏大 |
| **572** | `runtime_embedded_screenplay_safety.py` | **本次新建** |

### 1.2 `apps/studio/src/` Top

| 行数 | 文件 | 本次 |
|---:|---|---|
| **5963** | `product-shell.js` | **不碰**（依赖广、职责杂、测试面大） |
| 2723 | `agent-chat-lifecycle.js` | 不碰 |
| 1263 | `agent-chat-panel.js` | 不碰 |

---

## 2. 选定目标与风险分析

### 选定：`runtime_embedded_creative_actions.py` → `runtime_embedded_screenplay_safety.py`

**独立职责：** 嵌入式创作动作中的 **剧本候选 / 分镜计划安全校验完整功能块**  
（screenplay_candidate / shot_plan 校验、production brief 归一化、时长评估、文本安全辅助）。

**为何选它：**

- 第一天报告已点名为下一刀，且当时只做过 ~50 行象征性拆分。
- 生产 fan-in 极窄：`runtime_service.py` 只注册路由；测试主要打 HTTP 契约。
- 块内多为纯函数，边界清晰，不碰 idempotency / Graph apply / provider dispatch。

**未选：**

| 候选 | 原因 |
|---|---|
| `product-shell.js` | 风险过高 |
| `runtime_script_core_truth.py` | 今日主线仍在改；已有多次局部拆分 |
| video / image admission | 公共+私有导入面大，媒体路径 blast radius |
| asset bible owner import | 可作备选，但共享 token 辅助有循环税 |

**依赖处理：** `_safe_production_brief` 对 `EmbeddedProductionBrief` 使用函数内懒导入，避免父模块↔安全模块循环，并保持原 `isinstance` 语义。

**契约工具：** `evaluate_m6_6_…` 源码契约拆成「父模块合同 ID / 导入」+「安全模块校验实现」两条，避免字符串探针误报。

---

## 3. 拆分前后对比

| 文件 | 拆分前 | 拆分后 | Δ |
|---|---:|---:|---:|
| `runtime_embedded_creative_actions.py` | 2020 | **1488** | **−532** |
| `runtime_embedded_screenplay_safety.py` | — | **572** | +572 |

迁出内容（完整职责块，非散装纯函数）：

- 常量：`UNSAFE_TEXT_FRAGMENTS` / `PROMPT_LEAK_FRAGMENTS` / speaker 规则 / 时长默认值
- `_screenplay_candidate_schema`
- `_validate_preview_payload` 及整条 screenplay/shot 校验链
- `_safe_shot_plan` / `_safe_production_brief` / `_shot_plan_duration_assessment`
- 共享 `_safe_text` / `_safe_token` / `_contains_*`

父模块保留：路由注册、请求模型、provider preview/apply、idempotency、Graph compile/recovery。

---

## 4. 测试验证

### 4.1 相关测试基线 / 拆分后

```text
pytest tests/test_api_runtime_embedded_creative_actions.py \
       tests/test_evaluate_m6_5_embedded_creative_action_ux.py \
       tests/test_evaluate_m6_6_visible_creative_tasks_screenplay_graph_actions.py -q
```

| 阶段 | 结果 |
|---|---|
| 拆分前 | **14 passed**（embedded + m6.5；m6.6 另 1 passed）→ 合计 **15** |
| 拆分后 | **15 passed**（~6.0s） |

### 4.2 全量非浏览器回归

命令：`pytest tests/ --ignore=tests/browser --ignore=tests/test_studio_browser -q`

| 结果 | 数量 |
|---|---:|
| passed | 2225 |
| failed | 30 |
| skipped | 9 |

其中 **非浏览器失败恰好 12 个**，与今日已知既有失败集合 **完全一致**（context budget / image admission hash / keyframe bridge / m6 preview recovery ×6 / m6 script-plan ×3）。  
**无新增失败。** 其余 18 个为 `test_web_studio_*browser*`（未被 `--ignore=tests/browser` 排除），不计入本闸。

---

## 5. 一句话

**在不动 `product-shell.js` / Script Core 主线的前提下，把 embedded creative 的剧本/分镜安全校验整块外提到独立模块（父文件 −532 行），相关 15 测与已知 12 既有失败集合之外的非浏览器回归均无新增问题；未推送。**
