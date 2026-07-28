# Studio Web 设计 QA

## 结果

通过当前垂直切片的实现级设计检查。未发现 P0 或 P1 问题。

本报告证明的是本地产品壳、交互和响应式表现，不证明服务端写入、Provider
生成、媒体质量、人工验收或商业交付。

## 对照范围

| 工作面 | 设计参照 | 浏览器状态 |
| --- | --- | --- |
| 项目概览 | `docs/design/visuals/v0.2/V03-project-overview.png` | `surface=overview&source=fixture` |
| 制作画布 | `docs/design/visuals/v0.2/V04-production-canvas.png` | `surface=canvas&entity=shot-03&source=fixture` |
| 生成审核 | `docs/design/visuals/v0.2/V08-generation-review-master.png` | `surface=review&candidate=candidate-shot-03-video-v2&source=fixture` |
| 局部返工 | `docs/design/visuals/v0.2/V09-local-rework-preview.png` | 审核工作面打开“预览局部返工” |
| 合成交付 | `docs/design/visuals/v0.2/V10-delivery.png` | `surface=delivery&source=fixture` |

设计参照与实现截图在同一张左右对照图中检查。临时证据目录：

`C:\Users\chenzy\AppData\Local\Temp\afs-studio-web-qa`

## 视口

- 桌面：浏览器外框请求 `1488 × 1058`，页面实际视口 `1352 × 962`。
- 窄屏：浏览器外框请求 `720 × 900`，页面实际视口 `654 × 818`。
- 窄屏概览和审核均无水平页面溢出；项目工作面导航与审核队列使用受控横向滚动。

## 已验证交互

- 项目概览的主动作进入镜头 03 审核。
- 制作画布对象选择和“定位当前任务”保持 URL 对象状态。
- 审核候选聚焦更新候选和实体参数。
- 媒体预览可在本地播放/暂停状态间切换，不冒充真实视频播放。
- 局部返工预览可打开，可用 Escape 关闭；确认动作保持禁用。
- 右侧创作助手默认收起，可展开并保留当前工作面上下文，可用 Escape 收起。
- 交付阻塞项可聚焦，并通过“继续处理阻塞项”回到对应审核或画布对象。
- `loading`、`empty`、`error`、`stale`、`forbidden` 五种状态均可到达。
- live 模式读取失败时不会静默回退到 fixture。
- 浏览器控制台没有 error 或 warning。

## 视觉判断

- 布局：全局顶栏、左侧全局轨道、项目工作面导航、主工作区和右侧助手轨道稳定。
- 密度：延续 v0.2 的紧凑生产工具密度，没有扩张为营销卡片式界面。
- 字体与层级：中文标题、对象名、状态、辅助说明的层级清晰，无明显拥挤或截断。
- 颜色：深色中性表面、青色主动作、琥珀色待决策和绿色完成态映射一致。
- 图标：统一使用 Tabler 线性图标，没有 emoji、手绘 SVG 或 CSS 图形替代。
- 可访问性：语义按钮、区域标签、焦点环、跳过链接和 reduced-motion 规则存在。

## 已知且有意保留的差异

- v0.2 视觉稿中的灯塔、人物和港口画面是概念表现，不是已获准写入产品的媒体资产。
  当前实现按任务要求复用仓库既有图片 fixture，因此主体画面不同；不会用设计截图冒充项目结果。
- 视觉稿部分页面显示展开的智能工作区；当前任务明确要求右侧助手默认收起，因此实现以收起态为默认。
- 当前 BFF v0.1 没有媒体 URL、命令预览或确认写入路由。live 模式只渲染信封中真实存在的
  摘要，所有权威写动作保持关闭；fixture 模式显式标记为界面样例。
