# AFS Web Refoundation Cleanup 001

> 记录时间：2026-06-11 by Codex  
> 分支：`codex/afs-web-refoundation-vertical-001`  
> 模式：Deep / Web / Runtime Service / cleanup  
> 目标：把 Web 从横向 LibTV 仿制 RC 收束为一条能跑通的剧本到分镜生产竖线。

## 决策摘要

当前 Web RC 已经具备大量 LibTV 风格表层，但用户目标不是继续扩大节点数量，而是尽快得到高质量、可运行、可接模型的创作界面。本轮清理采用“保留底座，砍掉噪音”的策略。

## 保留

- `apps/workbench` 作为正式 Web 工作台入口。
- Runtime Service、OpenAPI、安全 artifact、safe manifest、job、trace、review feedback。
- `/provider/script-draft-plan` 作为第一条 provider-gated 竖线入口。
- provider gate 默认关闭的边界：LLM/image/video/ASR 分能力授权。
- 浏览器 QA、focused pytest、maintenance audit、`git diff --check`。

## 收束

- 首页从工程状态板和横向 showcase 收束为创作门户：最近项目、开始创作、能力入口、灵感模板。
- Create 画布从“多个仿制节点都能点”收束为“剧本输入 -> 分镜 artifact -> 反馈重生”的主链路。
- starter nodes 保留四个方向，但 image/video/audio 在第一阶段只显示 gate 状态和下一步条件。
- 文案从“仿站功能名”改为 AFS 自己的生产语言，避免误导为真实 provider 已经运行。

## 隐藏或冻结

- 会员、积分、促销、VIP、价格等 LibTV 商业表层。
- 与第一条竖线无关的全局抽屉、TV 工具箱、展示案例详情、横向 add-node 深层仿制。
- 只登记本地 intent 但不产生主链路 artifact 的按钮，在主屏默认隐藏。
- 任何“生成成功”措辞，除非有 Runtime artifact 和 fresh verification。

## 不做

- 不删除 Runtime Service 或安全 contract。
- 不触发真实 provider 调用。
- 不写入 provider secret、signed URL、本地私有素材路径或生成媒体字节。
- 不把 provider readiness、browser QA 或 runtime verification 说成人工验收。
- 不把反馈自动晋升为长期记忆或 Company OS active rule。

## 替代路径

第一阶段只实现：

```text
用户剧本/目标输入
  -> POST /provider/script-draft-plan
  -> script_storyboard_safe_artifact
  -> 画布分镜节点展示
  -> 用户反馈
  -> 第二轮候选约束
```

image/keyframe/I2V 后续依次接入，必须先建立对应 Runtime contract 和 provider gate。

## 验证

本轮每个代码切片至少运行：

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_web_workbench_foundation.py tests\test_api_runtime_llm_script_vertical.py -q
git diff --check
```

完成前追加：

```powershell
.\.venv\Scripts\python.exe tools\maintenance_audit.py
```

