# AFS Human Acceptance Runbook 004 人工验收手册

日期：2026-06-14  
目的：给人工验收一个明确入口，把 runtime/browser verification 升级为 human acceptance。

## 声明边界

在你按本手册走完之前：

- 测试通过只代表工程验证；
- 浏览器 QA 只代表浏览器与 Runtime 路径验证；
- provider smoke 只代表 provider 调用链有证据；
- 以上都不是 human acceptance，也不是 business validation。

人工验收只从你亲自执行以下路径并记录通过/失败开始。

## 证据保留规则

每个失败只保留：

- project id；
- node id 或 job id；
- safe manifest / artifact id；
- 一张代表截图；
- 简短复现步骤。

不要保存：

- provider raw response；
- provider key、token、cookie；
- signed URL；
- 本地私有素材绝对路径；
- Runtime safe preview/artifact 流程之外的生成媒体字节。

## 路径 1：项目创建与刷新持久化

步骤：

1. 打开 `/studio/`。
2. 新建一个项目。
3. 添加一个图片节点，输入简短提示词。
4. 刷新页面。
5. 切换到另一个项目，再切回来。

通过标准：

- 项目下拉、URL、drawer 项目名、画布内容一致；
- 不出现其他项目的节点；
- 刷新后保留节点提示词、预览图、固定资产和连线；
- 不出现原生 `prompt`、`confirm`、`alert` 弹窗。

只能由人判断：

- 新建项目和切换项目对内测成员是否直观。

## 路径 2：T2I 文生图

步骤：

1. 新建一个没有上传图、没有连线资产的图片节点。
2. 输入一个新人物或新场景提示词。
3. 点击提示词优化。
4. 生成一张图。

通过标准：

- 优化结果是文生图扩写语气，而不是图生图最小变更语气；
- 没有 fixed asset 时不弹携带确认层；
- 生成成功时通过 safe preview 显示图片，失败时给出可理解的安全失败；
- UI 不暴露 provider raw、secret-like 字符串或本地路径。

只能由人判断：

- 图像质量；
- 提示词遵守程度；
- 优化提示词是否真正有帮助。

## 路径 3：I2I 参考图编辑

步骤：

1. 在图片节点上传参考图。
2. 输入局部修改指令，例如发型、服装或背景变化。
3. 优化提示词。
4. 生成一张图。

通过标准：

- 优化结果使用图生图编辑 / 最小变更语言；
- 请求明确使用 Runtime image asset 引用；
- 生成预览来自 `/projects/.../preview` 安全端点；
- 失败时用户层文案清楚，技术细节不抢占主要说明。

只能由人判断：

- 参考人物身份是否保住；
- 修改是否太弱、太破坏或刚好合适；
- 画面是否可用于后续资产固定。

## 路径 4：固定资产

步骤：

1. 从上传图或生成图选择 `固定为人物资产` 或 `固定为场景资产`。
2. 填写结构化特征卡字段。
3. 添加不可变锁定项。
4. 确认固定。
5. 刷新项目并重新打开资产。

通过标准：

- 固定资产必须填写签名；
- 固定资产至少有一项特征卡字段；
- `不采用` 路径不强制完整特征卡；
- 刷新后 drawer 和节点 badge 仍能看到资产；
- 资产详情弹层能显示 Runtime 返回的状态、签名、特征卡、锁定项和来源节点。

只能由人判断：

- 手填特征卡成本是否能被内测成员接受；
- 标签和签名是否自然、准确。

## 路径 5：固定资产携带与一次性排除

步骤：

1. 把 fixed character asset 源节点用 reference 边连到图片生成节点。
2. 在生成节点输入可能冲突的提示词。
3. 点击生成。
4. 阅读 `生成前确认`。
5. 第一次点取消。
6. 第二次点生成，勾选资产，点击 `本次不携带选中项`。
7. 根据 provider 状态继续生成或停在 preflight 后。
8. 第三次再点生成。

通过标准：

- 只要本次会携带 fixed asset，就必须弹确认层；
- 即使没有检测到明显冲突，也必须列出携带资产；
- 主体参考图有标注；
- 取消后节点状态和 Runtime 保存状态都恢复到取消前；
- `本次不携带` 只排除本次请求，不修改资产本体；
- 第三次生成时资产会重新进入确认层。

只能由人判断：

- 这层确认是否足以解释“男性资产覆盖女性提示词”这类问题。

## 路径 6：Kling I2V

步骤：

1. 新建或选择视频节点。
2. 上传或选择一张 image asset，显式设为首帧。
3. 检查视频规格：比例、分辨率、时长。
4. 提交一条 Kling I2V。
5. 轮询到成功或可恢复失败。
6. 刷新页面，确认 job 仍可继续轮询或预览。

通过标准：

- 不使用隐式首帧；
- provider descriptor 没声明音频能力时不显示声音选项；
- candidate count 为 1；
- 付费视频提交前确认信息清楚；
- 预览通过 Runtime safe endpoint；
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
