# Scene 资产需求派生视图（2026-08-04）

状态：本地生产接线与确定性测试已落地；证据级别仅为代码/测试验证。

## 1. SceneProps 生产形态

- `ScenePropItem` 保留 `ClaimedText name + optional importance`，生产模型在
  `apps/api/runtime_scene_props.py`。
- 复用 `entity_kind="scene"`：当前道具没有独立、跨 Scene 稳定识别的实体
  生命周期；归属由 `scene[scene_id].props[N].name` 表达，和 cast 的层级路径一致。
- `importance` 只接受显式 `关键道具：` / `重要道具：` 信号。叙事重复、戏份或
  常识不构成 importance evidence；没有信号时保留 missing。
- 候选仍经 CandidateFact 状态机和 accept/edit-confirm 才能成为
  AuthoritativeScriptFact；raw/missing 值不进入 Graph 或资产需求视图。

若未来需要跨 Scene 区分“同一把钥匙”和“两把同名钥匙”，应先建立独立 Prop
identity/lineage 契约，再考虑新增 `entity_kind="prop"`。当前仅凭名词无法可靠完成
该身份判断，因此不提前伪造顶级 Prop 实体。

## 2. 提取纪律与可靠性

自动提取只接受两类信号：

1. Scene 范围内显式 `道具：` 标签；
2. 闭集、无歧义物件名词，且同一叙述分句中存在持有、操作或物理状态信号，
   例如“攥着一封信”“翻出一本相册”“把一把钥匙塞给她”“手机屏幕的光”。

闭集是有意的低召回选择。地点常识、剧情需要、服装、人物、车辆、建筑部件和
普通家具不会自动变成道具。未知名词宁可 missing。重复地点导致 Scene 原文范围
不能唯一归属时，整个 SceneProps 提取 fail closed；evidence 必须满足
`source_text[start:end] == quote == name/importance`，不生成兜底 span。
`edit_confirm` 也只能在原候选 evidence 所属的 Scene source range 内重新寻找精确
span，不能借用另一场里出现的同名或新道具文本。

这比 Character/Scene label 提取更难，也更依赖句子关系。当前实现能证明对这组
语料的保守确定性基线，不能证明开放域道具识别质量。

## 3. 六剧本结果

| 剧本 | Scene -> props | missing |
|---|---|---|
| 01 最后的光 | 废弃灯塔 -> 手电筒、灯塔灯、开关 | 灯塔阳台 |
| 02 海边的信 | 老式邮局 -> 信、挂钟；苏晴的房间 -> 台灯、信纸、笔、信 | 海边礁石 |
| 03 归途 | 小镇火车站 -> 照片 | 陈浩家中的老屋 |
| 04 旧照片 | 阁楼 -> 相册、照片；厨房 -> 照片、刀、相册 | 无 Scene props missing |
| 05 陌生来电 | 无归属结果 | Scene 本身 unresolved；不把手机挂到伪造 Scene |
| 06 夜班 | 地下通道 -> 钥匙 | 货运站台 |

合计 16 个 SceneProp name 候选，分布在 7 个 Scene；4 个已解析 Scene 的 props
保持 missing，另有 1 份脚本因 Scene unresolved 保持全局 missing。16 个
importance 均为 missing。`外套`、`铁门`、`小渔船`、`长椅`、`柜台`、`书桌`
未被当成道具资产需求。

## 4. 资产需求投影

`asset_requirement` 仍是只读派生视图行，不是新的 CandidateFact entity_kind。
投影只读取当前 revision 下 `validity=active` 的权威事实：

- Character：`scene[scene_id].cast[N].appearance`；
- Prop：`scene[scene_id].props[N].name`，可附同 slot 已确认的 `importance`；
- 同 revision 的 `entity_asset_bindings`。

道具 name 确认后按 `entity_id=scene_id + field_path=props[N].name` 精确查询
Script Core Truth `asset_type="prop"`。唯一同名 Core prop 才绑定；零个或多个都
返回 `core_asset_binding_status="unbound"` 和明确说明，不猜 asset ID。
同一 slot 被新权威事实 supersede 且新名称没有唯一 Core match 时，旧 active
binding 会转为 stale；投影同时校验当前 `authoritative_fact_id` 与 display name，
不会把旧资产绑定继承给新道具名。

Graph 节点带 `parent_scene_id`、`order_index`、`prop_slot` 和
`asset_kind="prop"`。同 revision 同 Scene slot 再确认使用稳定节点 ID，避免
supersede 后累积重复 prop 节点；不同 revision 使用不同节点，避免旧 revision
关系指向被新文本覆盖的节点。Scene 名称下游列表只读取 `scene.name`，不会被 prop
文本污染。

## 5. 非范围与非声明

- 未增加功能开关，也未调用远程 provider。
- 未实现开放词汇 NLP/LLM 道具分类或跨 Scene Prop identity。
- 未证明 provider smoke、生成媒体质量、人工接受、业务验证或发布准备度。
