# AFS Browser QA Loop 004 浏览器接管记录

日期：2026-06-14  
分支：`codex/afs-agent-browser-repair-loop-004`  
声明边界：本记录只代表 runtime/browser verification，不是 human acceptance，也不是 business validation。

## 本轮范围

本轮验证的是 preflight 之后的 Studio 修复闭环：

- 生成前固定资产携带确认层；
- “本次不携带”整项 fixed asset 的一次性排除；
- 资产详情弹层改为从 Runtime 读取 visual asset 详情；
- drawer 内 image asset 的“固定为人物 / 固定为场景”入口；
- 项目下拉中当前项目和最近项目不被 QA/smoke/debug 折叠误伤；
- Kling I2V 视频规格弹层不再显示当前不支持的声音控制。

本记录不保存 secret、provider raw response、signed URL、本地私有素材路径或媒体字节。

## 证据位置

代表性浏览器证据保存在：

```text
runs/agent_browser_qa_loop_004/
```

文件：

- `fixed-asset-carry-confirmation.png`
- `asset-detail-runtime-popover.png`
- `video-spec-no-sound.png`
- `browser_logs_safe.json`

已验证路径的浏览器 console warning/error 为空。

## QA 夹具

项目 id：

```text
loop004-browser-qa
```

夹具包含：

- 一个已固定的人物资产源节点；
- 一个通过 `reference` 边连接的下游图片生成节点；
- 一个 Kling I2V 视频节点，用于 prompt bar 和规格弹层验证。

说明：夹具通过 API 脚本写入，部分中文标题在该脚本路径里显示为 `????`。这是夹具序列化噪声，不代表 Studio 正常 UI 创建路径的中文显示问题。

## 发现与修复

### P1：旧模型 id 导致图片节点被误判为不支持生成

现象：

- 图片节点 UI 显示 `MiniMax image-01`；
- 点击生成却进入“当前版本仅图片节点支持真实生成”的错误分支；
- 没有进入 keyframe preflight。

根因：

- `findModel()` 会为了展示回退到默认 MiniMax 模型；
- `isRemoteImageModel()` 却直接检查原始 `node.params.model`；
- 旧项目状态里的 `minimax_image_01` 与当前预设 `minimax-image-01` 不一致，导致显示层与发送层分裂。

修复：

- `isRemoteImageModel()` 和 `isRemoteVideoModel()` 改为通过 `findModel()` 解析；
- 显示模型和发送模型共用同一套解释；
- 已在 `tests/test_web_studio_static.py` 增加静态回归。

### P1：取消固定资产确认后 Runtime 状态未持久恢复

现象：

- 在“生成前确认”点取消后，浏览器内存中的节点恢复；
- 但 Runtime `studio-state` 可能仍保存 `generating`；
- 刷新后节点状态会错误地停在生成中。

根因：

- 取消分支调用 `restoreCancelledGeneration(...)` 后直接返回；
- 没有执行 `flushRuntimeSave`。

修复：

- keyframe 和 video 的取消分支都在恢复状态后立即 flush Runtime save；
- 已在 `tests/test_web_studio_static.py` 增加静态护栏。

## 已验证行为

### 固定资产携带确认

结果：通过。

- preflight 解析到 fixed assets 时，Studio 会打开 `生成前确认`；
- 确认层始终列出本次携带资产；
- 即使词法级冲突检测没有命中，也会提示“固定资产仍会约束结果”；
- 主体参考图会在资产行标注；
- 确认前不会提交 provider。

### 一次性资产排除

结果：通过。

- 勾选资产并点击 `本次不携带选中项` 后，会重新 preflight；
- 后续请求显示 `本次未携带固定资产`；
- Runtime 状态中不再保留 `temporaryAssetExclusions`；
- 下一次再点生成，固定资产会重新进入携带确认层，证明排除没有静默延续。

### Runtime-backed 资产详情弹层

结果：通过。

- 点击 fixed asset badge 后显示资产详情；
- 弹层展示状态、签名、特征卡、锁定项、来源节点；
- 弹层提供 `从当前节点移除` 和 `本次不携带`。

### Kling I2V 声音控件隐藏

结果：通过。

- 视频 prompt bar 显示 `9:16 · 720P · 5s`；
- 打开规格弹层后只显示比例、分辨率、时长；
- 不再显示当前 provider descriptor 未声明支持的 `声音` 选项。

## 剩余风险

- 本轮没有声明 MiniMax 图片质量、人物身份相似度或 Kling 视频质量通过；
- 真实 MiniMax 提交在一次排除资产后的路径里返回 provider 就绪类安全失败，该失败不影响 preflight / exclusion 语义验证，但完整 live image acceptance 仍需人工和 provider 环境共同验证；
- 创意质量、资产相似度、首帧忠实度必须由人按 runbook 评分。

## 下一轮建议

合入本分支后继续跑完整角色矩阵：

1. 小白路径：新建项目 -> T2I -> 优化 -> 生成 -> 固定资产；
2. 创作者路径：上传参考图 -> I2I 编辑 -> 固定资产携带 -> 一次性排除；
3. 资产管理员路径：drawer 详情 -> 退役 -> badge 失效提示；
4. 视频路径：显式首帧 -> Kling submit/poll/preview；
5. 破坏性路径：快速切项目、刷新、重复提交、取消弹窗。

收口条件保持不变：连续两轮完整角色矩阵零新增 P0/P1。
