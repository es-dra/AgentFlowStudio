# 运行时过大模块盘点与小范围拆分（2026-08-05）

| 项 | 值 |
|---|---|
| tip | `382e8169`（含 #230/#231 之后的 alias eval 提交；相对 `de05374d` 多文档/评测，核心 runtime 大文件量级同级） |
| 动作 | 盘点 + 成因分析 + **一次纯结构拆分**（场景块匹配辅助函数） |
| 原则 | 不改 API / 数据结构 / 业务逻辑；拆分前后同套测试 |

---

## 1. 模块大小盘点（按行数）

阈值：单文件 **≥1500** 标为明显过大；**1000–1499** 标为偏大需关注。

### 1.1 `apps/api/` Top（节选）

| 行数 | 文件 | 标记 |
|---:|---|---|
| 3438 | `runtime_video_admission.py` | 过大 |
| **3131→3080** | `runtime_script_core_truth.py` | 过大（本周 #230/#231 主膨胀点；拆分后略降） |
| 2725 | `runtime_asset_bible.py` | 过大 |
| 2648 | `runtime_image_admission.py` | 过大 |
| 2020 | `runtime_embedded_creative_actions.py` | 过大 |
| 2007 | `runtime_production_control.py` | 过大 |
| 1409 | `runtime_production_runs.py` | 偏大 |
| 1336 | `runtime_m6_script_plan_asset_bible.py` | 偏大 |
| 1293 | `runtime_dynamic_production_plan.py` | 偏大 |
| … | （另有多份 ~900–1200） | 偏大 |
| **366** | `runtime_script_candidate_extraction.py` | 健康（#230 已拆出的确定性提取） |
| **82** | `runtime_script_scene_block_match.py` | **本次新建** |

### 1.2 `apps/studio/src/` Top（节选）

| 行数 | 文件 | 标记 |
|---:|---|---|
| **5963** | `product-shell.js` | 过大（第一天即标出，仍为前端之最） |
| 2691 | `agent-chat-lifecycle.js` | 过大 |
| 1263 | `agent-chat-panel.js` | 偏大（挂了 candidate review UI） |
| 1163 | `asset-bible-workspace.js` | 偏大 |
| 1133 | `embedded-creative-actions.js` | 偏大 |
| 1075 | `runtime-client.js` | 偏大（含 analysis-candidates 客户端） |
| **168** | `script-candidate-review.js` | 健康（#230 新审阅 UI） |

### 1.3 相对第一天旧数据

- `product-shell.js`、`runtime_embedded_creative_actions.py` **仍然很大**，量级未因 #230/#231 消失。
- **新增大块：** `runtime_script_core_truth.py` 因 candidate extract/review + scene ownership 涨到 3k+；提取规则本身已在独立的 `runtime_script_candidate_extraction.py`（366 行）。
- Studio 审阅未堆回 Asset Bible 巨石，而是相对小的 `script-candidate-review.js`。

---

## 2. 前 2–3 名成因与拆分风险

### 2.1 `product-shell.js`（~5963）— 风险极高

- **为什么大：** 产品壳路由、多 workspace（含 Asset Bible）、命令恢复、媒体/图片准入 UI、状态编排混在同一文件。
- **自然边界：** 有，但切面会碰到几乎整站导航与状态。
- **依赖：** studio/tests 引用面约 **29** 处量级；动一处易 ripple。
- **本次：** **不拆**。

### 2.2 `runtime_script_core_truth.py`（~3k）— 收益高、全拆风险高

- **为什么大：** 同文件混合：Pydantic 契约、HTTP 路由注册、revision/candidate/asset 持久化、审阅与 Graph 写入、core-asset 命令、**#231 场景归属**。
- **自然边界：**
  - 已拆：确定性人物/场景提取 → `runtime_script_candidate_extraction.py`
  - 可继续：场景块字面匹配（纯函数）→ 本次已做
  - 下一步候选（未做）：ownership 路由+审阅状态机、core-asset 命令、public projection DTO
- **依赖：** API/tests 约 **15** 处直接引用；内部私有函数互相调用密。
- **本次：** 只拆 **纯匹配辅助**，不动路由与状态机。

### 2.3 `runtime_video_admission.py` / `runtime_asset_bible.py` / `runtime_embedded_creative_actions.py`

- 视频/图片准入、Asset Bible、嵌入创作动作：各自是完整纵切，**fan-in 不一**（embedded ~2，看似好拆，但内部 `_safe_text` 等横切 60+ 次，整块搬家仍易牵连）。
- **本次：** 不选它们做第一刀（与本周 Script Core 主线距离远，或耦合面不比「三函数外提」更干净）。

---

## 3. 实际拆分（低风险）

### 3.1 做了什么

| 之前 | 之后 |
|---|---|
| `_scene_start` / `_scene_content_start` / `_member_spans_in_scene_block` 在 `runtime_script_core_truth.py` | 迁至 `apps/api/runtime_script_scene_block_match.py`（公开名 `scene_evidence_start` 等） |
| 同文件直接定义 | `runtime_script_core_truth` **仅改 import 别名**，仍用 `_scene_start` 等内部名调用 |

- **未改：** HTTP 路径、JSON 契约、ownership 状态机、Graph 写入。
- 新模块内保留与原先等价的 label 清洗私有辅助（避免把全局 `_clean_text_list` 大搬家）。

### 3.2 行数对比

| 文件 | 拆分前 | 拆分后 |
|---|---:|---:|
| `runtime_script_core_truth.py` | 3131 | **3080** |
| `runtime_script_scene_block_match.py` | — | **82** |

### 3.3 测试证据

同一命令：

```text
pytest tests/test_api_runtime_scene_ownership.py \
       tests/test_api_runtime_script_candidate_extraction.py \
       tests/test_api_runtime_script_candidate_review.py \
       tests/test_api_runtime_script_core_truth.py -q
```

| 阶段 | 结果 |
|---|---|
| 拆分前 | **16 passed**（~7.0s） |
| 拆分后 | **16 passed**（~7.4s） |

行为回归：ownership missing/present、candidate extract/review、core truth 契约测试均绿。

---

## 4. 后续拆分建议（未做）

1. 将 `#231` ownership **审阅/失效/Graph 边** 整段迁到 `runtime_script_scene_ownership.py`（仍依赖 store 辅助，需一次较大 PR）。
2. `product-shell.js` 按 workspace 切片（独立里程碑，需前端专项）。
3. `runtime_embedded_creative_actions.py` 先抽 screenplay safety 纯函数簇（需先抽出共享 `_safe_text` 小模块以免循环依赖）。

---

## 5. 一句话

**当前最大巨石仍是 `product-shell.js` 与若干 admission/bible 后端；本周相关的 `runtime_script_core_truth.py` 因 #230/#231 成为新的 3k 级集中点。本次只做了场景块匹配辅助函数的纯结构外提，相关 16 个测试拆分前后均通过；未动最大文件以免牵连评测主线。**
