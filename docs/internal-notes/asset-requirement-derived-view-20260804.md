# 资产需求（asset_requirement）调查与设计（2026-08-04）

状态：调查完成；生产接线已落地 — **Scene 人物资产派生视图**（道具仍跳过）。

## 1. SceneProps 生产状态

| 位置 | 状态 |
|---|---|
| `docs/internal-notes/draft_scene_schema_20260802.py` | **草稿**（`SceneProps` / `ScenePropItem`） |
| `apps/api/runtime_candidate_fact_status.py` `entity_kind` | 仅 `character \| scene \| script_profile \| script_format_profile \| beat` |
| `apps/api` 候选提取 / 确认闭环 | **无** SceneProps 候选事实 |

**结论：** 道具资产现在**不能**安全投影。前置条件是把 SceneProps 接到候选→确认生产闭环（像 cast 一样），再投影。本次**不做**道具，也不顺带接线 SceneProps（工作量独立一档）。

## 2. 候选事实 vs 派生视图

| 方案 | 评价 |
|---|---|
| 独立 `entity_kind=asset_requirement` + accept/edit | **不适用**：没有新的文本主张要人审；再确认一次等于对已确认 cast 做二次橡皮图章 |
| **派生视图**（类似 `resolve_for_downstream`） | **选这个**：只读投影已确认 cast + bindings；revision/supersede 自然反映最新权威 |

用户任务里写的 `entity_kind="asset_requirement"` 保留为**视图行语义标签**（`kind`），**不**扩进 `CandidateFact.entity_kind` Literal，避免伪造「可确认」表面。

### 投影输入（仅权威层）

1. 当前 revision 下 `validity=active` 的 cast appearance  
   `field_path = scene[{scene_id}].cast[N].appearance`
2. 同 revision 的 `entity_asset_bindings`（`identity.display_name` 绑定）  
   有 → 填 `core_asset_id`；无 → `core_asset_binding_status=unbound` + 明确文案，**不猜**

不读 raw 候选、不做新文本推断。Beat 范围：预留 `scope_kind`，本次只产出 `scope_kind=scene`。

## 3. 今天做 / 不做

**做**

- `project_scene_character_asset_requirements(store, ledger)`  
- 挂进 `resolve_for_downstream`（需 `store`）与 `GET …/asset-requirements`  
- 六剧本：确认 cast 后投影；绑定/未绑定诚实标注；换 revision / supersede 读最新

**不做**

- 道具 / SceneProps 生产接线  
- 镜头表达 / 制作可行性  
- 把 asset_requirement 塞进候选状态机或 Graph 二次确认  
- 新功能开关

## 4. 风险自检

- 过期数据：只读 `list_current_authoritative` + active bindings  
- 假装有 asset_id：无绑定必须 `unbound`  
- 双重确认陷阱：无 accept 路径  
- 道具偷渡：本视图 `asset_kind` 仅 `character`
