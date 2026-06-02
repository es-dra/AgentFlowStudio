# Configs

Commit only example configuration files.

- `models.example.yaml` is the committed template.
- `models.yaml` is the local override and is ignored by git.
- The default provider is `mock`; OpenAI-compatible providers must be explicitly configured locally.

Remote LLM calls must remain disabled unless `AFS_ALLOW_REMOTE_LLM=true`.
Remote image calls for PosterFlow must remain disabled unless
`AFS_ALLOW_REMOTE_IMAGE=true`.

PosterFlow image providers are selected with `AFS_IMAGE_PROVIDER`:

- `openai_compatible`: uses `AFS_IMAGE_BASE_URL`,
  `AFS_IMAGE_API_KEY`, and `AFS_IMAGE_MODEL`.
- `minimax`: uses the MiniMax native image-generation API, defaulting to
  `https://api.minimax.io` and `image-01` when base URL and model are not
  set locally.

Provider keys must stay in local environment variables only.
