# 配置目录

本目录只提交示例配置和可审计配置契约，不提交本地密钥或真实 provider 配置。

## 文件边界

- `models.example.yaml`：提交到 Git 的模型配置模板。
- `models.yaml`：本地覆盖配置，已被 `.gitignore` 忽略。
- `ffmpeg.example.yaml`：提交到 Git 的 FFmpeg 配置模板。
- `ffmpeg.yaml`：本地覆盖配置，已被 `.gitignore` 忽略。
- `tool_catalog.yaml`：工具目录契约索引，引用 `tool_catalog/` 下的分片；字段名可能包含 `api_key` / `token` 这类 schema 名称，但不得写入真实值。
- `tool_catalog/`：工具目录契约分片，按 workflow 领域拆分，避免单个配置文件膨胀。
- `platform_profiles/`：平台 profile 示例和约束。

## Provider Gate

远程能力默认关闭，必须显式授权：

```powershell
$env:AFS_ALLOW_REMOTE_LLM="true"
$env:AFS_ALLOW_REMOTE_ASR="true"
$env:AFS_ALLOW_REMOTE_IMAGE="true"
```

PosterFlow 图片 provider 通过 `AFS_IMAGE_PROVIDER` 选择：

- `openai_compatible`：读取 `AFS_IMAGE_BASE_URL`、`AFS_IMAGE_API_KEY`、`AFS_IMAGE_MODEL`。
- `minimax`：使用 MiniMax 原生图片生成 API；未设置本地 base URL / model 时使用默认服务地址和模型。

所有 provider key 只能放在本地环境变量或 ignored 本地配置里，不能进入仓库。
