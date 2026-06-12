# Provider Adapter v0.1 Contract

中文摘要：本契约定义 AFS 本地 provider 中转站的最小公共接口。Runtime 只能通过
`ProviderRegistry.dispatch(...)` 调度 provider；服务能力由 descriptor 描述，账号由
本地 account pool 选择，真实 secret 只存在于环境变量或 ignored local config 中。

AFS 使用本地轻量 provider adapter 层，不引入外部网关。Runtime 只面向统一
registry，不直接 import 具体 provider smoke、SDK wrapper 或账号实现。

## Descriptor

每个 `services.*` 必须带 `descriptor`。示例见 `configs/providers.example.json`。

关键字段：

- `modality`: `llm | image | video | asr`
- `execution_mode`: `sync | async`
- `capabilities`: 服务支持的能力列表，必须包含 `modality`
- `account_pool_id`: 可选账号池 id；缺省时兼容旧 `account_ref`
- `reference_image_slots`: adapter 可接受的参考图位数
- `supported_aspect_ratios`: adapter 支持的画幅
- `prompt_char_limit`: provider prompt 字符上限
- `seed_supported`: 是否支持 seed
- `cost_hint` / `rate_limit_hint`: 只写公开提示，不写真实成本或账号策略
- `required_gate`: 必须是 `AFS_ALLOW_REMOTE_*`

Runtime 已消费 `prompt_char_limit` 和 `reference_image_slots`，因此 MiniMax 的
1500 字符与单参考图限制只是服务配置，不再是 resolver 的架构假设。

## Account Pool

账号池只存在于 ignored local config 或 example config。仓库不得提交真实 key。

账号池 entry 支持：

- `account_id`
- `service_id`
- `credential_env`
- `enabled_capabilities`
- `enabled`
- `priority`
- `weight`
- `concurrency_limit`
- `health_state`

选择规则：按 `priority` 升序、再按 `account_id` 稳定排序。`enabled=false` 或
`health_state=disabled` 不参与调度。`credential_env` 只检查变量是否存在，不读取
或写入变量值。trace、manifest、OpenAPI 和前端响应不得暴露 secret。

## Lifecycle

所有 adapter 实现同一生命周期：

```text
validate -> translate -> submit -> poll -> normalize -> safe_error
```

同步 provider 的 `submit` 可以返回 already-complete task；异步 provider 必须把
提交和轮询拆开。fake video adapter 只用于本地 contract 验证，不代表真实 video
provider smoke。

## Runtime Dispatch

Runtime 唯一调度入口：

```python
registry.dispatch(capability, service_id, request)
```

已接入：

- `minimax_image`: image / sync
- `minimax_m3`: OpenAI-compatible LLM / sync
- `fake_video`: video / async contract test only

Kling 等真实 video adapter 属于后续切片。真实 provider 调用仍必须单独开启对应
gate；image 授权不代表 LLM、ASR、video 或下载授权。
