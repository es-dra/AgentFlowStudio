# A/B/C 关键帧对比实验 Runbook v0.1

中文摘要:本文是 `generation_comparison_report v0.1` 的人工操作与评分规范。实验目的:用真实生成证据回答"固定资产特征卡/锁定项注入是否实际提升一致性",并观察哪些特征卡字段被模型遵守,反哺特征卡模板设计。

非声明边界:实验结果是 provider smoke 证据,不是 human acceptance、business validation 或 durable memory;评分是人工观察记录,不写入公司知识库。

## 三臂定义(已钉死,不得漂移)

| 臂 | 定义 |
|---|---|
| A | 原始提示词,无 asset_refs,无参考图,旧 provider 路径 |
| B | 新 resolver generate 模式,排除 fixed assets 注入(无特征卡/锁定/参考图) |
| C | B + fixed asset 特征卡 + 锁定项 + 主体参考图 |

## 前置条件

1. 分支测试全绿(全量 pytest)。
2. 项目内至少 1 个 fixed 人物资产(含参考图与完整特征卡)和 1 个 fixed 场景资产。
3. 显式授权:本机 shell 设置 `AFS_ALLOW_REMOTE_IMAGE=true` 与 provider 配置;image 授权不代表 LLM/ASR/video/下载授权。
4. 使用 `tools/studio_asset_context_live_comparison.py` 并带 `--allow-live-provider` 显式开关。

## 操作步骤

1. 选 3 个测试提示词:一个只含人物、一个人物+场景、一个含与锁定项冲突的描述(验证锁定压制)。
2. 每个提示词依次跑 A/B/C,各臂固定相同 seed 与画幅。
3. 每臂收集 keyframe_request_plan、candidates_summary、生成图。
4. 按评分表逐图打分,填入 report。
5. 结论与字段观察写入 report 的人工备注区。

## 评分表(每图 1-5 分,3 为及格)

| 维度 | 说明 |
|---|---|
| 身份一致性 | 人物五官/发型/体型与参考图及特征卡的相符程度 |
| 服装一致性 | 标志性服装颜色与款式是否保持 |
| 锁定项遵守 | 每条 negative_lock 单独判定:遵守/违反/不适用 |
| 场景连续性 | 空间结构、关键道具、光线基调与场景卡相符程度 |
| 提示词忠实度 | 本镜动作/构图/情绪是否按可见提示词执行 |
| 画面质量 | 无畸形、无乱码文字、无水印、构图成立 |

## 字段有效性观察(反哺模板)

对 C 臂逐项记录:`hair / face / wardrobe / palette / layout / lighting_mood` 每个字段:被遵守 / 部分遵守 / 被忽略。连续两轮被忽略的字段,在特征卡模板中标注"低效字段",考虑改写表述方式或移除。

## 判定标准

- C 显著优于 A 且优于 B(身份+服装+锁定三项平均 ≥ +1 分):资产语义有效,进入内测推广。
- C ≈ B:特征卡文本未被模型消费,优先检查预算裁剪 trace 与字段表述,再考虑 provider 能力上限。
- C 优于 B 但锁定项违反率高:锁定表述需改写为更具体的视觉语言。

## 结果去向

- 合格候选图:走"固定为资产"确认面板回流(人工确认必经)。
- 失败候选图:仅保留为实验证据,不回流。
- report 与评分:作为 adapter 选型和 S2 特征卡反推设计的输入。
