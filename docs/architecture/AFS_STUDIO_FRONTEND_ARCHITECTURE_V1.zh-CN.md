# AFS Studio 前端架构 v1

AFS Studio 是当前唯一用户侧 Web 前端。它使用无限画布创作图谱来承载提示词优先的内容生产流程。成熟节点式创作工具只是交互参考，产品模型以 AFS 自己的流程为准。

## 产品模型

```text
创作意图
  -> 剧本 / 分镜
  -> 人物与场景参考
  -> 导演台调度
  -> 关键帧与片段提示词
  -> 本地预览或显式授权后的 provider 任务
```

用户可见的提示词记忆能力必须保持很小：每个 prompt 输入位可以打开一个锚定的“优化”浮层。专业知识、项目上下文、人物/场景摘要、用户偏好、trace、provider 状态和记忆装配都在 Runtime Service 后台完成。

## 当前文件

```text
apps/studio/                         当前前端包
apps/api/runtime_studio_static.py    /studio/ 静态挂载，禁用缓存
apps/api/runtime_prompt_memory_*     提示词优化 API 与装配逻辑
```

旧 Workbench 和 memory-workbench 已从产品路径删除。不要在这些名称下新增用户侧页面。

## 画布行为

- 画布支持平移、缩放、框选、双击建节点、拖动节点、网格吸附、节点局部操作和贝塞尔连线。
- 节点是 AFS 创作流程对象：文本意图、图片/关键帧意图、视频片段意图、音频意图、脚本/分镜意图、导演台、资源输入和合成。
- 连线表达创作依赖、参考关系和生成流向；它只是图谱关系，不代表真实 provider 已执行。
- 选中节点拥有 prompt bar；提示词优化必须锚定在输入位附近，不能变成独立工程页面。

## UI 边界

用户 UI 可以展示：

- 节点标签
- 显性资产
- prompt 文本
- 用户版优化提示词分段
- 本地预览状态
- safe summary

用户 UI 不能展示：

- provider secret 或原始响应
- 本地绝对路径
- signed URL
- 媒体字节
- rule id
- trace 内部字段
- 知识权重
- 隐藏记忆候选
- 后端 gate 术语

## 维护规则

- Studio 模块保持单一职责，超过项目行数阈值时继续拆分。
- 提示词优化作为可复用的节点输入组件维护。
- 导演台是镜头意图、机位、阻挡和灯光上下文，不是静态资产页面。
- 浏览器 QA 必须覆盖 Studio 画布、添加节点菜单、提示词优化浮层、节点连线、导演台和 console error。

## 验证

核心命令：

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_prompt_memory_loop.py tests\test_api_runtime_prompt_node_contract.py tests\test_web_studio_static.py -q
.\.venv\Scripts\python.exe -m pytest
git diff --check
```

Runtime-hosted QA：

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main runtime-service --host 127.0.0.1 --port 8806
```

打开 `http://127.0.0.1:8806/studio/`，在 provider gate 关闭的前提下验证画布流程。
