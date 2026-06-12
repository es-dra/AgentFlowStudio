# AFS-STUDIO-FRONTEND-POLISH-001 Handoff

中文摘要：本次为内测前的前端交互层收口，只改 `apps/studio/src`、`apps/studio/styles` 与一处浏览器 QA 工具选择器，不触碰 Runtime contract、optimizer-contract 请求构造与 director-shell。核心目标是让“固定资产”这个咽喉动作可被普通内测成员正确完成，并让携带/冲突信息说人话。

分支：与 `codex/afs-asset-context-s1-followup-001` 同分支；本仓库当前已在历史提交 `7536eba` 与 `68064ff` 中包含对应前端主体改动，本 handoff 作为独立交接记录收口。

## 改动清单

| 文件 | 改动 |
|---|---|
| `apps/studio/src/panels/visual-asset-panel.js` | 重写为结构化表单：人物/场景两套特征卡字段集，逐项输入带示例占位；锁定项快捷 chips 可从已填字段自动组词，并支持自由输入；固定前校验名称、签名、至少一项特征并内联报错；提交失败不再静默关闭面板；拒绝路径允许空卡并落证据占位；全中文。`data-field="feature_card"` 选择器被 `data-card="<key>"` 结构化字段取代。 |
| `apps/studio/src/node-result-view.js` | “本次携带”升级为人物/场景资产 chips、主体参考图标注、人话化警告、本次已解除锁定列表、预算压缩说明；导出 `humanWarning` 供 optimizer 复用。 |
| `apps/studio/src/optimizer.js` | 资产引用区中文化为“已连线/未连线/项目内可用”，连线状态着色；冲突警告复用 `humanWarning`；“本次解除”按钮带已解除状态，防重复点击。 |
| `apps/studio/src/node-actions.js` | 修正“本次”语义：`temporaryLockOverrides` 在生成请求发出后即清空，不再静默延续到下一次生成。 |
| `apps/studio/src/main.js` | 移除无功能的分享/作品库/账户按钮；`Ctrl+L` 排列改为按连线拓扑分层，上游在左、下游在右、孤立节点垫底，并含环路深度保护；新增 `?` 打开快捷键面板。 |
| `apps/studio/src/prompt-bar.js` | 移除无功能的“标记”“角色库”chips 与“翻译”按钮，待功能落地后恢复。 |
| `apps/studio/styles/modals.css` / `apps/studio/styles/node-result.css` / `apps/studio/styles/popovers.css` | 新增 `va-*` 表单、`bundle-*` 指示、`opt-source-chip` 状态样式。 |
| `tools/studio_asset_context_browser_qa.py` | 同步面板选择器：旧 `feature_card` 文本域改为三个 `data-card` 结构化字段。 |

## 验证状态

- 已验证：`visual-asset-panel` / `node-result-view` 全文与 `main.js` 新增函数在隔离 Node 22 环境通过语法检查；拓扑分层算法在 DAG、孤立节点、环路三种输入下行为正确；静态测试 marker（`visual-asset-panel`、`opt-context-assets`、`opt-inline-btn`、`context-bundle-summary`、`temporaryLockOverrides`）全部保留。
- 待本机复核：完整浏览器 QA 与全量 pytest。

建议复核命令：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_web_studio_static.py -q
.\.venv\Scripts\python.exe -m pytest -q
node --check apps/studio/src/main.js; node --check apps/studio/src/optimizer.js; node --check apps/studio/src/prompt-bar.js; node --check apps/studio/src/node-actions.js; node --check apps/studio/src/node-result-view.js; node --check apps/studio/src/panels/visual-asset-panel.js
```

本次属于 runtime verification 层面的前端收口，不声明 human acceptance 或 business validation。

## 行为变更须知

1. 固定资产时特征卡按字段逐项填写，不再手写 `key: value` 行。
2. 临时解除锁定只对下一次生成生效，生成后自动恢复锁定。
3. 分享、作品库、账户、翻译、标记、角色库入口暂不可见，功能落地后恢复。
