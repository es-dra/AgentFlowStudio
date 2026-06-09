# AFS Web UI 中文术语表

状态：阶段 0 产品语言冻结
日期：2026-06-09

## 产品定位

| 英文/工程对象 | UI 显示 | 使用边界 |
|---|---|---|
| Workbench | 工作台 | 顶层产品入口 |
| Runtime Service | 运行服务 | 只在状态条和诊断里出现 |
| Project Manifest | 项目档案 | 作为项目事实来源，不展示为工程主语 |
| Provider Gate | Provider 预检 | 不等于真实模型调用 |
| Artifact | 产物引用 | 默认隐藏内部 id，只在详情/诊断里展开 |
| Job / Run | 任务 | 面向用户显示进度、阻塞和产物 |
| Raw feedback | 原始反馈 | 只是证据，不是记忆 |
| Candidate memory | 候选记忆 | 可用于下一轮，但不是 durable memory |
| Durable memory | 持久记忆 | 当前 UI 不主动宣称写入 |

## 一级工作区

| 内部 view | 中文显示 | 用户任务 |
|---|---|---|
| `Projects` | 项目 | 创建、打开、导入、查看项目状态 |
| `Create` | 创作画布 | 规划内容链路、选择当前步骤、查看检查器 |
| `Assets` | 素材库 | 添加安全素材摘要和参考约束 |
| `Storyboard` | 分镜台 | 查看镜头序列和当前分镜状态 |
| `Review` | 审片室 | 对候选结果做保留、修改或拒绝 |
| `Style Memory` | 项目记忆 | 查看候选记忆、复用约束和下一轮上下文 |
| `Jobs` | 任务中心 | 查看运行任务、阻塞和 Provider 预检 |
| `Settings` | 诊断 | 查看连接、内部 id、安全边界和高级证据 |

## 文案原则

- 首屏使用产品语言，不使用工程入口语言。
- `project_id`、`job_id`、`artifact_id` 默认只出现在诊断、详情抽屉或产物引用按钮。
- Provider 状态必须说明是预检还是真实调用；默认不调用真实 provider。
- 记忆相关状态必须区分原始反馈、候选记忆、profile version 和 durable memory。
- 所有按钮必须表达用户动作，例如“创建项目”“生成画布草稿”“记录审片决定”，避免只写 API 动词。
