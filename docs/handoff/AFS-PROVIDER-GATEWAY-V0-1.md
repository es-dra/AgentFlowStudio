# AFS Provider Gateway v0.1 Handoff

中文摘要：本交接记录说明 Provider Gateway v0.1 的实际落地范围。本轮保留
AFS 自建轻量 adapter/registry 路线，不引入外部网关；新增账号池选择、
OpenAI-compatible LLM dispatch 和 fake async video 生命周期验证。没有开启真实
provider gate，也没有产生人工验收或业务验证结论。

## 已完成

- `ProviderDescriptor` 扩展了 `capabilities`、可选 `account_pool_id`、
  `rate_limit_hint`、`prompt_char_limit` 和 `reference_image_slots`。
- 新增本地 `account_pools.*` 配置契约，按 priority 和 account id 做确定性选择。
- 账号池只检查 `credential_env` 是否存在，不读取、不记录、不返回 secret 值。
- MiniMax image 继续走 `ProviderRegistry.dispatch(...)`。
- Runtime prompt enhancement 已从旧 `ModelGateway.from_config_path` 切到
  `llm / minimax_m3` registry dispatch。
- 新增 fake async video adapter，用来验证 `submit -> poll -> normalize` 生命周期。
- `configs/providers.example.json` 已扩展为 image、LLM、fake video 的统一模板。

## 当前接口

- `ProviderRegistry.dispatch(capability, service_id, request)`
- `ProviderDispatchRequest`
- `ProviderDescriptor`
- `configs/providers.example.json` 中的 `account_pools.*`

Runtime keyframe generation 已消费 descriptor 驱动的 prompt 字符预算和参考图位。
Runtime prompt enhancement 已消费 registry-backed LLM dispatch。

## 验证

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_provider_adapter_registry.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_provider_adapter_registry.py tests\test_api_runtime_creative_agent_keyframes.py tests\test_api_runtime_keyframe_reference_assets.py tests\test_api_runtime_context_resolver.py tests\test_api_runtime_prompt_memory_loop.py tests\test_openai_compatible_provider.py -q
```

最近本地结果：

```text
provider registry: 11 passed
focused provider/keyframe/resolver/prompt set: 42 passed, 1 Starlette/httpx warning
full pytest: 838 passed, 1 Starlette/httpx warning
Studio JS node --check: passed 35 files
maintenance_audit: failed=0, warning=1 existing oversized-files warning
git diff --check: passed with Windows CRLF notices only
```

## 边界

- 没有开启真实 provider gate。
- 没有发起 image、LLM、ASR、video 或外部下载 provider call。
- fake video 只是生命周期 contract 测试，不是 Kling adapter。
- Kling adapter 属于后续 v0.2 切片。
- `configs/providers.local.json` 仍是 ignored 本地状态，本轮只更新 example config。
- 本轮结论是 runtime verification，不是 human acceptance、business validation 或
  durable-memory promotion。
