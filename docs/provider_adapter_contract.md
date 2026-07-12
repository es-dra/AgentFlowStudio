# Provider Adapter v0.1 / v0.2 / v0.3 Contract

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

## Image Edit Capability Fields

`provider_descriptor.v0.3` may add `image_edit_capabilities` for image providers.
The field is capability metadata only; it does not execute provider calls, wire
Runtime local-edit routes, or claim provider QA.

Absent `image_edit_capabilities` is the v0.1/v0.2 blocked default:

- `supports_image_edit=false`
- `supports_true_local_edit=false`
- no supported local-edit scope kinds
- no fallback modes
- `local_edit_truth_label=blocked_no_supported_local_edit`

Registry consumers can distinguish this absent-field default with
`descriptor.image_edit_capabilities_present`.

Supported local-edit scope kinds are derived from explicit descriptor flags:

- `supports_mask_asset` -> `mask_asset`
- `supports_bbox_region` -> `bbox`
- `supports_polygon_region` -> `polygon`
- `supports_semantic_region` -> `semantic_region`

Fallback labels are intentionally separate from true local edit:

- `provider_full_frame_edit`
- `full_regeneration_fallback`
- `reference_image_to_image_fallback`

`fallback_modes` must not contain `true_local_edit`. A full-frame,
reference-guided, or image-to-image path is not true local edit unless a later
descriptor and evaluator explicitly classify it as a lower-precision capability.
`ProviderDispatchRequest.image_operation`, `edit_source_image_path`,
`edit_reference_image_paths`, and `image_input_fidelity` are adapter inputs, not
capability claims by themselves.

See `docs/provider_adapter_v03_image_edit_addendum.md` for the scoped image-edit
descriptor addendum.

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
