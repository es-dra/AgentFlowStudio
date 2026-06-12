# AFS Provider Gateway v0.1 维护账本

日期：2026-06-12

中文摘要：本维护账本记录 Provider Gateway v0.1 的架构决策和边界。本轮不引入
New API、LiteLLM 或其他外部网关，不提交真实 key；只把 Runtime provider 调度
收敛到本地 `ProviderRegistry.dispatch(...)`、descriptor 和 account pool。

## 决策

- Provider 中转站采用本地轻量 adapter 层。
- 新 provider 接入必须是 descriptor、adapter、gate test、safe manifest test 的组合。
- 账号池只保存账号引用、能力、优先级、并发提示和 credential env 名称。
- secret 值只允许存在于环境变量或 ignored local config，不进入仓库、trace、
  manifest、OpenAPI 或前端响应。

## 本轮改动

- `CompanyProviderSecrets` 保留 `account_pools` 字段。
- 新增 `provider_account_pool.py`，负责账号池解析、确定性选择和 credential env
  存在性检查。
- `provider_adapter.py` 回到 contract / registry 职责。
- 新增 `provider_adapter_impl.py`，承载 MiniMax image、OpenAI-compatible LLM 和
  fake async video adapter。
- Runtime prompt enhancement 改走 registry-backed LLM dispatch。
- `configs/providers.example.json` 成为统一 provider registry 示例。
- `docs/provider_adapter_contract.md`、`configs/README.md` 已更新为可读契约。

## 保留边界

- 真实 provider 调用仍然必须显式开启对应能力 gate。
- image gate 不授权 LLM、ASR、video 或 external download。
- fake async video adapter 不代表 Kling 已接入。
- 旧 `ModelGateway` 仍保留兼容测试；后续 registry-backed live LLM smoke 通过后，
  再决定是保留 shim 还是删除旧 config 路径。

## 验证

```text
tests/test_provider_adapter_registry.py: 11 passed
focused provider/keyframe/resolver/prompt set: 42 passed, 1 Starlette/httpx warning
full pytest: 838 passed, 1 Starlette/httpx warning
Studio JS node --check: passed 35 files
maintenance_audit: failed=0, warning=1 existing oversized-files warning
git diff --check: passed with Windows CRLF notices only
```

没有真实 provider call。
