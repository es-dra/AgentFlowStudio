# Configs

Commit only example configuration files.

- `models.example.yaml` is the committed template.
- `models.yaml` is the local override and is ignored by git.
- The default provider is `mock`; OpenAI-compatible providers must be explicitly configured locally.

Remote LLM calls must remain disabled unless `NARRATOCUT_ALLOW_REMOTE_LLM=true`.
