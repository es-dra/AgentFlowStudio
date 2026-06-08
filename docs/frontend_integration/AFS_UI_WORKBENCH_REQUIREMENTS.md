# AFS UI Workbench 需求

状态：第一轮外部前端实现的产品/UI 要求。

## 目标

构建一个本地 canvas-style operator workbench，对接 AFS Runtime Service v0.1。

UI 要帮助测试人员快速回答：

- 当前打开哪个项目？
- 当前是哪一轮 run？
- 正在 review 哪个 artifact？
- 哪些 refs included，哪些 refs blocked？
- 哪些 feedback 是 raw evidence，哪些是 candidate、profile version 或 durable memory？
- 下一步动作是什么？

## 第一屏

第一屏必须是实际项目工作台，不是 landing page。

必需区域：

1. Project rail
2. Canvas / pipeline graph
3. Selected node inspector
4. Artifact/report panel
5. Feedback/action panel

## Canvas Nodes

最小节点：

```text
Project
Source Assets
Round 1 Asset Test
Tester Feedback
Candidate Update
Promotion Decision
Profile Version
Context Projection
Round 2 Validation
Provider Gate
```

Node status values：

```text
queued
running
succeeded
failed
blocked
cancelled
not_started
ready_not_run
needs_review
```

## Inspector Requirements

选中节点时展示：

- node status；
- backing `job_id`；
- backing `artifact_id`；
- artifact type；
- key facts；
- blockers；
- non-claims。

Asset review 必须展示：

- character / scene / profile version；
- included refs；
- blocked refs and reasons；
- feedback result：`kept`、`partially_kept`、`failed`、`unknown`；
- next recommendation；
- boundary labels：
  - not human acceptance；
  - not business validation；
  - not durable memory。

## Feedback UX

UI 必须区分：

| State | Meaning |
|---|---|
| raw feedback | tester evidence only |
| candidate | suggested memory/profile update |
| promotion decision | explicit reviewed decision |
| profile version | versioned reusable context source |
| durable memory | not implemented in this slice |

除非后端 artifact 明确声明 durable memory 已写入，否则不要显示 “saved to memory”。

## Provider UX

Provider panel 默认是 safe preflight mode。

展示：

- provider capability；
- gate status；
- blockers；
- provider calls 是否 started；
- redacted metadata status。

禁止展示：

- provider config path；
- API keys；
- signed URLs；
- provider response body；
- private media paths；
- generated media bytes。

## Error UX

直接使用后端 blockers，不要改写成泛化错误。

示例：

- `project_materials_missing`
- `profile_version_missing`
- `context_projection_not_ready`
- `provider_validation_not_requested`
- `provider_config_missing`
- `image_gate_not_enabled`
- `video_gate_not_enabled`

`blocked` 不等于 `failed`。blocked node 仍可能有可用 artifact。

## Minimum Acceptance

第一版前端可接受条件：

1. 连接 `/health`。
2. 创建或打开 project manifest。
3. 启动 Round 1 asset test run。
4. 渲染 pass/block/non-claim facts。
5. 通过 `/feedback` 记录 raw feedback。
6. 从 Round 1 `job_id` 启动 Round 2 validation。
7. 渲染 included refs 和 blocked refs。
8. 通过 `/provider/validation-plan` 渲染 provider readiness/blocker state。
9. 不显示或存储 private local paths、secrets、signed URLs、media bytes。

## Not In Scope

- SaaS account system。
- Database-backed collaboration。
- Cloud sync。
- Browser-side workflow execution。
- Direct provider execution from browser。
- Multi-user permission model。
- Business validation dashboard。
- Durable COS memory promotion。
