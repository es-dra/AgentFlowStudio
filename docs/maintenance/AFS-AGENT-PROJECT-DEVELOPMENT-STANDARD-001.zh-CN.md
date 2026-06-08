# AFS / COS Agent 项目开发规范候选稿

状态：candidate / repo execution projection。

本文件不是 COS active rule，也不是 Company memory 晋升结果。它是基于当前 AFS 后端基线、本地知识库工程规则、Harness-first 候选规则、全局开发技能约束整理出的项目规范候选稿，用于提升 vibecoding 后项目的可读性、可维护性和可交接性。

## 一句话规则

任何 Agent 项目开发，都必须先定义：

```text
contract
artifact
harness
verification
provider gate
handoff
```

再写实现代码。

如果一个功能不能说清楚输入、输出、证据、验证命令和边界，它就还不是工程任务，只是想法。

## 适用范围

适用于：

- AFS 后端、CLI、Runtime Service、Web workbench。
- COS / Memory OS 相关的本地规则投影。
- Provider、生成媒体、Agent workflow、context runtime、memory candidate 相关任务。
- 后续外部前端团队接入前后的接口和 artifact 协作。

不直接适用于：

- 公司战略判断。
- 商业验证。
- 人工内容审美验收。
- COS active rule 自动晋升。

## 来源约束

本候选稿吸收了这些原则：

- `10-Startup` 是公司规则和知识库源头。
- AFS repo 只保存 execution-facing projection。
- 项目开发遵循 `Orient -> Frame -> Plan -> Execute -> Verify -> Record -> Handoff`。
- Harness-first 规则使用 execution、tooling、context、lifecycle、observability、verification、governance 七层来定义任务环境。
- Worktree / branch / subagent 必须有 owner、write scope、acceptance criteria、verification 和 integration order。
- 结构验证、runtime verification、human acceptance、business validation、durable memory promotion 必须分开。
- Provider gate 必须按 LLM、ASR、image、video、download 等 capability 分别授权。
- 测试通过、demo 成功、候选记忆存在，都不是公司长期记忆或产品验证。

## 任务分级

每个任务开始前先分类：

| 类型 | 典型任务 | 默认动作 |
|---|---|---|
| Light | 文案、单文件小修、只读说明 | 可在当前 checkout 处理 |
| Standard | 新 endpoint、新 CLI、新 contract、小型 Web view | 使用 `codex/*` 分支或 worktree |
| Deep | 跨模块架构、schema 变更、provider 适配、两轮 runtime 验证 | 独立 worktree，先写 brief 和 tests |
| Strategic | COS 规则、产品路线、跨团队接口、商业验证 | 先形成 candidate doc，不直接改 active rule |

## 每个任务必须先写清楚

最小 task brief 字段：

```text
id:
owner_role:
goal:
non_goals:
write_scope:
input_contracts:
output_artifacts:
provider_policy:
acceptance_criteria:
verification_commands:
handoff_path:
memory_impact:
integration_order:
```

如果其中三项以上说不清，先不要写代码。

## Contract-first 规则

AFS / COS 项目中的核心对象必须先有 contract，再有实现。

优先顺序：

```text
schema / dataclass / pydantic model
-> example fixture
-> validator / focused test
-> CLI or Runtime Service facade
-> UI view
-> handoff
```

禁止：

- UI 先发明隐式数据结构。
- CLI 输出只有人类可读文本，没有机器可读 artifact。
- Provider 响应体直接变成产品对象。
- 测试 fixture 混入真实私有素材、secret、signed URL。

## Artifact-first 规则

每次 Agent 执行都必须留下可审计 artifact，而不是只留下聊天记录。

最小 artifact 信息：

```text
artifact_type
schema_version
created_at / recorded_at
input_refs
output_refs
evidence_refs
blocked_refs
status
non_claims
```

artifact 可以作为 evidence，但不能自动成为：

- human acceptance。
- business validation。
- durable Company memory。
- COS active rule。

## Harness-first 规则

评价 Agent 项目时，不评价“模型聪不聪明”，而评价：

```text
model + harness
```

每条执行链要能回答：

| 层 | 必须回答 |
|---|---|
| Execution | 在哪里运行，读写哪些目录，是否可复现 |
| Tooling | 调哪些工具，输入输出是什么，失败如何处理 |
| Context | 模型看见什么上下文，来源是什么，是否过期 |
| Lifecycle | 如何拆分、重试、暂停、交接、完成 |
| Observability | 如何记录状态、成本、失败、重试、证据 |
| Verification | 如何验证结构、runtime、人类反馈和商业结果 |
| Governance | 哪些动作需要 gate，谁能批准，如何审计 |

## 模块可维护性规则

默认模块规则：

| 文件长度 | 处理 |
|---|---|
| `<= 300` 行 | 理想状态 |
| `301-500` 行 | 可接受但需要关注 |
| `> 500` 行 | 需要拆分计划或明确理由 |
| `> 1000` 行 | 不应作为稳定产品代码保留 |

拆分方向：

- contract / model 单独放。
- store / repository 单独放。
- service orchestration 单独放。
- CLI adapter 单独放。
- API route 单独放。
- Web render helper 单独放。
- provider transport、provider runtime、provider report 不混在一个文件。

一个文件只承担一种主要责任。跨模块只通过公开函数、类或 contract 通信，不共享隐式全局状态。

## TDD 和验证规则

确定性逻辑必须先有 focused tests。推荐顺序：

```text
contract example test
-> validator test
-> CLI/API facade test
-> integration smoke
-> full pytest only when touching shared registry / schema / facade
```

完成声明前必须跑对应验证。不能把“我看起来改好了”写成 done。

## Provider Gate 规则

默认不调用远程 provider。

授权必须按 capability 写清楚：

```text
AFS_ALLOW_REMOTE_LLM
AFS_ALLOW_REMOTE_ASR
AFS_ALLOW_REMOTE_IMAGE
AFS_ALLOW_REMOTE_VIDEO
AFS_ALLOW_EXTERNAL_DOWNLOAD
```

Provider smoke 只证明 provider route / request / safe manifest 能工作，不证明内容被接受、不证明商业价值、不证明可上线。

Provider 相关 artifact 禁止保存：

- API key。
- cookie。
- token。
- signed URL。
- provider 原始响应体中的敏感字段。
- 私有素材字节。
- 生成媒体字节。
- 未脱敏本地私有路径。

## Dirty Worktree 规则

脏工作区不是继续堆代码的理由。

每次开发前必须区分：

```text
本轮我改的
用户已有改动
其他任务遗留改动
ignored runtime evidence
```

禁止：

- 为了方便直接 reset。
- 把无关改动混进本轮成果。
- 因为工作区脏就放弃 in-scope 清理。
- 把“保护用户改动”当成保留死代码的理由。

## Subagent / 外部团队协作规则

外部团队、前端团队、subagent 都只能拿到 bounded task。

必须给他们：

```text
目标
非目标
接口
样例
禁止事项
验收方式
证据路径
交接格式
```

不能只说“帮我做一个工作台”。应该交付可执行的对接包、API contract、UI requirements、request fixture 和 claim boundary。

## Handoff 必填

每个切片完成后写 handoff：

```text
what changed
files changed
how to run
verification results
provider calls made or not made
artifacts produced
known risks
non-claims
next step
```

没有 handoff 的功能，不算真正交付。

## COS 映射方式

AFS 中形成的工程经验进入 COS 时，必须走候选流程：

```text
repo evidence
-> candidate feedback packet
-> human review
-> limited rule
-> active rule
```

AI 可以提出 candidate，不能自动提升为 active rule。

`10-Startup` 是源头知识库。AFS repo 只保留执行投影、接口文档、验证报告和候选建议。

## 当前 AFS 可维护性下一步

建议按这个顺序推进，不要一次性大重构：

1. 建立 dirty worktree ownership ledger，标记哪些改动属于后端基线、provider 修复、Web view、local internal-test。
2. 将 Runtime Service v0.1 作为前后端唯一对接面，避免前端直接耦合 CLI 内部细节。
3. 对 `apps/api`、`apps/cli`、`agentflow/memory` 做 line count 和 responsibility audit。
4. 把 provider transport、runtime、safe manifest、smoke report 的职责继续拆清。
5. 压缩 `DEVLOG.md` 长叙事，只保留索引和 evidence pointer。
6. 把旧 `Company` 路径语言统一投影为 `10-Startup`，但单独做 docs-only 切片。
7. 为外部前端团队固定 request / response fixture，不让 UI 自造数据结构。
8. 每个新功能先补 focused tests，再补 facade，再补 UI。

## 最小 Definition of Done

一个 AFS Agent 项目切片只有同时满足以下条件，才算完成：

1. contract 或 artifact shape 明确。
2. request / response example 可读。
3. focused tests 通过。
4. CLI 或 Runtime Service facade 可调用。
5. 生成物写入 allowed / ignored runtime path。
6. provider gate 和 secret 边界明确。
7. handoff 记录 verification、risk、non-claim。
8. tracker 或 devlog 有简短 evidence pointer。
