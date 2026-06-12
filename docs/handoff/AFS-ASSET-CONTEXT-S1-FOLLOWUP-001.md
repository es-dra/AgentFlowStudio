# AFS-ASSET-CONTEXT-S1-FOLLOWUP-001 Handoff

中文摘要:本次收尾修补 S1 完成审计中发现的三个缺口——预算只记录不执行、冲突检测硬编码占位、上游摘要与偏好段恒为空——并交付特征卡模板、A/B/C runbook 与内测手册三份文档。代码改动集中在 context budget / resolver / keyframes 三个文件加一个新词表模块,不触碰 provider 管线、gate 体系与前端契约。

分支:`codex/afs-asset-context-s1-followup-001`(基于 master `7536eba`)。

## 改动清单

### 代码

| 文件 | 改动 |
|---|---|
| `apps/api/runtime_attribute_vocabulary.py` | 新增。属性词表(发色/发长/发型/眼色/服装色/体态/面部标记,中英对照,发色用窗口正则匹配"black short hair"类复合表述)+ `find_lock_conflicts` 词法冲突检测。低召回 best-effort,仅供 UI 警告。 |
| `apps/api/runtime_context_budget.py` | 重写。`apply_context_budget` 真执行分段裁剪:锁定+身份段永不裁;可见提示词保底 550 且可用身份段剩余空间;场景 250 / 上游 150 / 偏好 100 依序消费剩余预算;预留 8 字符分隔符余量;超限(身份段极长)时保住身份与可见保底并置 `overflow_beyond_total`。optimize 模式只报告不裁剪。`context_warnings` 改用词表检测,警告携带 attribute/lock_value/prompt_value/connected/detection 字段。 |
| `apps/api/runtime_context_resolver.py` | `_connected_asset_refs` 同时返回节点跳数;新增 `_upstream_summary_lines`(上游 1-3 跳带 prompt 的节点,按跳数排序取 3 条,每条 120 字符);`_text_channel` 填充 upstream/preference 段;新增 `style_preference` 参数;`apply_context_budget` 接入,bundle 的 text_channel 即裁剪后内容;`provider_prompt_from_bundle` 改为身份段先行——provider 硬截断的损失顺序与优先级序一致(锁定 > 用户文本)。 |
| `apps/api/runtime_keyframes.py` | `_context_bundle` 传入 `style_preference=request.style`。 |

### 测试

- `tests/test_runtime_attribute_vocabulary_and_budget.py`:新增。词表中英冲突/同值不冲突/词边界/窗口匹配;预算瀑布五种形态(全短、长可见、身份溢出、低优先封顶、optimize 只读)。
- `tests/test_api_runtime_context_resolver.py`:追加三个端到端用例——预算保底与锁定永不裁、上游摘要与偏好段入 provider prompt、词表冲突警告与"强制独立于检测"。

### 文档

- `docs/visual_asset_feature_card_template.zh-CN.md`:特征卡三层结构、人物/场景字段、填写规则、与预算的关系。
- `docs/abc_comparison_runbook.zh-CN.md`:三臂定义、前置授权、评分表、字段有效性观察、判定标准。
- `docs/afs_studio_internal_test_handbook.zh-CN.md`:内测成员全流程手册与必测清单。

## 行为变更说明

1. provider prompt 段落顺序变为:身份/锁定 → 可见提示词 → 场景/导演 → 上游摘要 → 偏好。
2. 新路径 provider prompt 现在包含上游节点摘要与 `style preference: <style>`(此前两段恒为空)。
3. 冲突警告条目新增字段;旧的 `black short hair` 硬编码行为被词表泛化覆盖(原用例语义保持)。

## 验证状态(诚实声明)

- 已验证:词表与预算模块全部逻辑在隔离环境逐用例通过(与仓库单测同源);resolver/keyframes 编辑后全文复核。
- 未验证:仓库全量 pytest 与浏览器 QA 未在本环境运行(沙盒无法运行 Windows venv 且 PyPI 不可达)。**合并前必须在本机执行:**

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_runtime_attribute_vocabulary_and_budget.py tests/test_api_runtime_context_resolver.py -q
.\.venv\Scripts\python.exe -m pytest -q
node --check apps/studio/src/main.js
.\.venv\Scripts\python.exe tools/maintenance_audit.py
```

- 本次为 runtime verification 收尾,不声明 human acceptance、provider smoke、business validation 或 durable memory。

## 后续

1. 本机跑全量测试后提交本分支(建议在 Windows 侧提交,沙盒 git 对编辑后文件存在视图滞后,不可在沙盒提交)。
2. 开启 `AFS_ALLOW_REMOTE_IMAGE` 跑真实 A/B/C(按 `docs/abc_comparison_runbook.zh-CN.md`)。
3. Provider adapter contract 设计与重构(下一任务,见对话规划)。
