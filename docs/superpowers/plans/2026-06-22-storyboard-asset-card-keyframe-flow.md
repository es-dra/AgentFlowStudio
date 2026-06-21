# 分镜资产卡与关键帧层实现计划

> 给后续开发线程的说明：本计划记录本次已完成的实施步骤、验证证据和边界。继续开发前需要先重新读取当前分支、另一个 AFS Land 线程和服务器状态。

## 目标

把“文本剧本 -> 结构化分镜 -> 资产准备 -> 关键帧图片 -> 视频”的前半段打通到可继续迭代的工程状态：

- 分镜节点可以一键识别角色、场景、道具资产。
- 自动生成的下游图片节点先是可编辑的候选资产卡，不是固定资产。
- 用户可编辑资产卡，再生成资产图，并选择是否标记为固定资产。
- 关键帧层只读取已经固定的 `visualAssets`，未确认候选资产不会污染生成上下文。
- 道具资产成为与角色、场景同级的一等资产类型。

## 架构边界

- 前端候选资产卡写入 `params.assetCardDraft`。
- 人工确认后的固定资产才写入 `params.visualAssets`。
- Runtime 上下文、关键帧层和后续生成只读取固定资产。
- 资产卡、分镜拆分和关键帧节点创建先保持本地 deterministic 行为。
- Provider gate 不变，本次没有打开远程 LLM、图片或视频生成。

## 已完成任务

### 1. 候选资产卡

- 新增 `apps/studio/src/asset-card-drafts.js`，集中生成和规范化角色、场景、道具候选资产卡。
- 新增 `apps/studio/src/panels/asset-card-panel.js`，支持在图片节点上编辑资产卡字段。
- 调整 `apps/studio/src/shot-asset-nodes.js`，分镜下游资产节点默认写入 `assetCardDraft`，不自动写入 `visualAssets`。

### 2. 分镜节点动作

- 新增 `apps/studio/src/storyboard-node-actions.js`，承接脚本节点的“识别资产”和“生成关键帧层”动作。
- 新增 `apps/studio/src/storyboard-keyframes.js`，根据分镜和已固定资产创建关键帧图片节点。
- 调整 `node-actions.js`、`node-menu.js`、`nodes.js`，让分镜节点菜单出现对应动作，并保持入口文件拆分约束。

### 3. 道具资产类型

- 前端资产卡、资产详情、抽屉动作、节点图标、Runtime 同步全部支持 `prop`。
- Runtime Pydantic 合同允许 `character / scene / prop / video` 草稿，以及 `character / scene / prop` 固定视觉资产。
- `agentflow.algorithms.asset_card_drafting` 支持道具草稿，并拆分 helper，避免入口文件超限。

### 4. 维护拆分

- `apps/studio/src/panels/visual-asset-defaults.js` 降到 287 行。
- 新增 `apps/studio/src/panels/visual-asset-prop-defaults.js`，承接道具默认卡推断。
- `agentflow/algorithms/asset_card_drafting/__init__.py` 降到 294 行。
- 新增 `agentflow/algorithms/asset_card_drafting/_helpers.py`，承接文本推断 helper。

## 验证

```text
python -m pytest -q -> 587 passed, 520 deselected, 2 existing warnings
npm run check:studio-js -> JS syntax check passed: 107 files
python -m apps.cli.main --help -> passed
python -m apps.cli.main version -> 0.1.0
python tools/studio_full_coverage_browser_qa.py --timeout-ms 30000 -> passed
python tools/maintenance_audit.py -> failed=0, warnings only
git diff --check -> passed with CRLF/LF warnings only
```

## 非声明边界

- 这不是 human acceptance。
- 这不是 business validation。
- 这不是 provider smoke。
- 这不是 durable memory promotion。
- 这次没有合并、推送、部署或同步服务器。
- 另一个 AFS Land 线程仍需在下次合并前刷新读取。
