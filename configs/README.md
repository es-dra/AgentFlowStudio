# Config Directory

中文摘要：本目录只提交示例配置和安全契约，不提交本地密钥、真实 provider 配置、
provider 原始响应、signed URL、媒体字节或机器相关绝对路径。真实模型接入时，
本地只使用 ignored 配置和环境变量；仓库内只保留可审计的模板。

## 文件边界

- `models.example.yaml`：旧 `ModelGateway` 的 OpenAI-compatible LLM 示例配置。
- `models.yaml`：本地旧 LLM gateway 覆盖配置，已被 `.gitignore` 忽略。
- `providers.example.json`：新的统一 provider registry 示例，覆盖 image、LLM、
  fake async video、descriptor 和 account pool。
- `providers.local.json`：本地 provider registry 配置，已被 `.gitignore` 忽略。
- `ffmpeg.example.yaml` / `ffmpeg.yaml`：FFmpeg 示例配置和本地覆盖。
- `tool_catalog.yaml` 与 `tool_catalog/`：工具目录示例。
- `platform_profiles/`：平台 profile 示例。

## Provider Gate

远程 provider 默认关闭，必须按能力单独授权：

```powershell
$env:AFS_ALLOW_REMOTE_LLM="true"
$env:AFS_ALLOW_REMOTE_ASR="true"
$env:AFS_ALLOW_REMOTE_IMAGE="true"
$env:AFS_ALLOW_REMOTE_VIDEO="true"
```

打开 image gate 不代表授权 LLM、ASR、video 或外部下载。每次真实调用前都要确认
本轮任务是否明确授权对应能力。

## 统一 Provider Registry

新的 provider 中转站使用 `configs/providers.example.json` 作为模板：

```powershell
$env:AFS_PROVIDER_CONFIG="$PWD\configs\providers.local.json"
$env:MINIMAX_API_KEY="<local-test-key>"
$env:AFS_OPENAI_COMPATIBLE_API_KEY="<local-test-key>"
```

registry 读取 `services.*.descriptor` 判断 provider 能力，读取 `account_pools.*`
做本地账号选择。账号池只保存环境变量名称，不保存 secret 值。Runtime trace、
manifest、OpenAPI 和前端响应只能写 safe summary。

## 旧 LLM Config

`configs/models.yaml` 仍用于旧 `ModelGateway` 兼容测试。新的 Runtime provider
工作应优先使用 `AFS_PROVIDER_CONFIG` 和 `ProviderRegistry.dispatch(...)`。等
registry-backed live LLM smoke 通过后，再决定是否删除旧配置路径。
