# AFS Web 重建设计说明

## 目标

先做一条真正能跑通的 Web 生产流程：用户输入剧本或创作目标，前端调用 Runtime Service 生成安全分镜 artifact，结果回到画布和 artifact 面板，并支持反馈与下一轮复用。

## 产品形态

界面应像专业创作工作台，不像工程状态看板，也不继续横向照搬 LibTV 的所有入口。首页承担创作入口和项目入口，画布承担第一条生产链路。

## 第一条纵切

```text
项目入口
  -> 开始创作
  -> 剧本到分镜节点
  -> Runtime Service script draft plan
  -> safe storyboard artifact
  -> 画布结果和反馈控件
  -> 第二轮候选约束
```

## UI 方向

- 深色创作工作台，强调媒体生产层级，不做营销页。
- 首页优先显示开始创作、最近项目和实用模板。
- 画布优先服务当前生产流程；暂时隐藏或弱化不能服务纵切的横向 demo。
- 文案中文优先，清楚说明 provider gate 状态。
- 不做会员、折扣、VIP、点数或虚假商业层。

## 工程边界

- 浏览器只调用 Runtime Service。
- 前端只能使用 `project_id`、`job_id`、`artifact_id`、safe summary、safe manifest 和 OpenAPI。
- 前端不得接触 provider secret、本地绝对路径、signed URL、provider 原始响应或媒体字节。
- 第一条 provider 能力只从 LLM/script 开始；图片和视频必须等独立 gate 与 contract。

## 验收标准

- 用户能在画布输入项目目标或剧本简述，并运行脚本草案动作。
- 前端调用 `/provider/script-draft-plan`，不触碰 CLI 内部。
- 生成的 safe artifact 能从 UI 打开。
- UI 明确区分 gate-closed 规划和真实 provider 执行。
- 首屏和画布不再像工程状态面板。
- focused tests、maintenance audit 和浏览器 QA 有新鲜证据。
