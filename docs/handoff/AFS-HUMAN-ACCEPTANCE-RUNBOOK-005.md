# AFS Human Acceptance Runbook 005 人工验收手册

日期：2026-06-14

目的：给人工验收一个明确入口。Loop 005 已完成的是 runtime/browser verification 和 provider smoke 证据；只有你本人按本手册走完并记录通过/失败后，才能把对应路径升级为 human acceptance。

## 证据保留规则

失败时只保留：

- project id；
- node id 或 job id；
- safe manifest / artifact id；
- 一张代表截图；
- 简短复现步骤。

不要保存或粘贴：

- provider 原始响应；
- provider key、token、cookie 或账号信息；
- signed URL；
- 本地私有素材绝对路径；
- Runtime safe preview / artifact 路由之外的生成媒体字节。

## 路径 1：项目创建、切换、刷新

步骤：

1. 打开 `/studio/`。
2. 新建一个项目。
3. 添加一个图片节点并输入短提示词。
4. 刷新页面。
5. 切换到另一个项目，再切回。

通过标准：

- URL、项目下拉、drawer 标题、画布内容一致。
- 不出现其他项目的节点。
- 刷新后保留提示词、预览图、固定资产和连线。
- 不出现原生 `prompt`、`confirm`、`alert` 系统弹窗。

只能由人判断：

- 项目创建和切换对普通内测成员是否直观。

## 路径 2：T2I 文生图

步骤：

1. 创建一个没有上传图、没有上游图、没有连线固定资产的图片节点。
2. 输入新人物或新场景提示词。
3. 优化提示词。
4. 生成一张图片。

通过标准：

- 优化结果是文生图扩写语气，不是图生图最小变更语气。
- 没有 fixed asset 时不弹携带确认层。
- 生成图通过 Runtime safe preview 显示。
- 用户层错误不暴露 provider raw、secret、signed URL 或本地路径。

只能由人判断：

- 图像质量；
- 提示词遵守程度；
- 优化提示词是否真的有帮助。

## 路径 3：I2I 图生图

步骤：

1. 上传或选择一张参考图。
2. 输入窄范围编辑指令，例如发型、服装或背景变化。
3. 优化提示词。
4. 生成一张图片。

通过标准：

- 优化结果使用参考图保持 / 最小变更语气。
- 请求使用 Runtime image asset id，不使用本地路径。
- 生成预览来自 Runtime safe preview endpoint。

只能由人判断：

- 身份是否保住；
- 修改是否太弱、太破坏，或刚好合适。

## 路径 4：固定资产

步骤：

1. 从上传图或生成候选中选择“固定为人物资产”或“固定为场景资产”。
2. 填写 signature、至少一个 feature card 字段和锁定项。
3. 确认固定。
4. 刷新项目并重新打开资产详情。

通过标准：

- 固定资产必须填写 signature。
- 固定资产至少有一项 feature card 字段。
- “不采用”路径不强制完整 feature card。
- 刷新后 drawer 和节点 badge 仍能看到资产。
- 资产详情由 Runtime 按 asset id 返回，展示状态、签名、特征卡、锁定项和来源节点。

只能由人判断：

- 手填特征卡成本是否能被内测成员接受；
- 标签和签名是否自然、准确。

## 路径 5：固定资产携带与本次排除

步骤：

1. 用 reference 边把 fixed character asset 源节点连到图片生成节点。
2. 在生成节点输入可能冲突的提示词。
3. 点击生成并阅读“生成前确认”。
4. 第一次点击取消。
5. 第二次点击生成，选择某个资产“本次不携带”。
6. 第三次再次点击生成。

通过标准：

- 只要本次会携带 fixed asset，就必须出现确认层。
- 即使没有检测到明显冲突，也必须列出携带资产。
- 主体参考图有标注。
- 取消不会提交。
- “本次不携带”只排除本次请求，不修改资产本身。
- 第三次生成时资产会重新进入确认层。

只能由人判断：

- 这层确认是否足以解释“男性固定资产覆盖女性提示词”这类问题。

## 路径 6：Kling I2V

步骤：

1. 创建或选择视频节点。
2. 选择一张 image asset，并显式设置为首帧。
3. 检查比例、分辨率、时长和成本确认。
4. 提交一条 Kling I2V。
5. 轮询到成功或可恢复失败。
6. 刷新页面，确认 job 仍可继续轮询或预览。

通过标准：

- 不使用隐式首帧。
- provider descriptor 没声明音频能力时，不显示声音选项。
- candidate count 为 1。
- 视频预览使用 Runtime safe preview endpoint。
- 刷新不丢 job 状态。

只能由人判断：

- 首帧忠实度；
- 时序身份保持；
- 运动指令遵守；
- 画面稳定性。

## 验收记录模板

```text
Human acceptance run id:
Date:
Project id:

Path 1 project persistence: pass/fail
Path 2 T2I: pass/fail
Path 3 I2I: pass/fail
Path 4 fixed asset: pass/fail
Path 5 carry/exclusion: pass/fail
Path 6 Kling I2V: pass/fail

Human-only quality notes:
- MiniMax identity similarity:
- MiniMax prompt adherence:
- Asset fixed-card UX:
- Kling first-frame fidelity:
- Kling motion adherence:
- Kling stability:

Blocking issues:
Evidence paths:
Decision: accepted / needs fixes / inconclusive
```
