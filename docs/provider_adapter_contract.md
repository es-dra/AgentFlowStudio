# Provider Adapter v0.1 契约

AFS 的 provider 接入走本地轻量 adapter 层，不引入外部网关。adapter 层只负责把 Runtime 的安全请求转成具体 provider 调用，并把结果归一化为 safe manifest / safe output。

## Descriptor

每个 `services.*` provider 配置必须带 `descriptor`：

```json
{
  "schema_version": "provider_descriptor.v0.1",
  "modality": "image",
  "execution_mode": "sync",
  "reference_image_slots": 1,
  "supported_aspect_ratios": ["1:1", "4:3", "3:4", "16:9", "9:16"],
  "prompt_char_limit": 1500,
  "seed_supported": true,
  "cost_hint": "Live image generation cost depends on provider account configuration.",
  "required_gate": "AFS_ALLOW_REMOTE_IMAGE"
}
```

Runtime 直接消费两个字段：

- `prompt_char_limit`：控制上下文预算和最终 provider prompt 截断。
- `reference_image_slots`：控制 resolver 参考图通道最多传给 adapter 的图片数量。

MiniMax image 当前配置为 1 个主体参考图位。这个限制属于服务能力描述，不再是 resolver 的架构假设。

## 生命周期

所有 adapter 都实现同一生命周期：

```text
validate -> translate -> submit -> poll -> normalize
```

同步 provider 的 `submit` 可以返回 already-complete task，因此 `poll` 会立即完成；异步 provider 可复用同一个接口表达 submit/poll 分离。

`safe_error(error)` 必须在错误进入 Runtime artifact 前脱敏，不能泄露 provider config、secret、token、Authorization header、本地路径或原始响应。

## Runtime 调度

Runtime 只允许调用：

```python
registry.dispatch(capability, service_id, request)
```

`apps/api/runtime_keyframes.py` 不应直接 import MiniMax smoke 函数。旧 CLI 命令名可以保留；未来如果要把 CLI 也纳入统一调度，应在内部复用 registry。

## Gate

`descriptor.required_gate` 是该服务的能力 gate。gate 按能力单独授权：打开 `AFS_ALLOW_REMOTE_IMAGE=true` 不代表授权 LLM、ASR、video、download 或其他网络能力。

gate 关闭时，Runtime 路径不要求本地 provider config，也不得启动网络调用。
