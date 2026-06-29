# AFS Asset Card Image Handoff Credential Fix - 2026-06-29

## Summary

Asset-card image generation could fail before queuing a `codex_image` handoff
job when the local Codex account was `auth_type: none` but its account-pool
entry still carried a stale or placeholder `credential_env`. Runtime surfaced
this as the safe generic block `Image provider configuration is not ready`,
which matched the Studio screenshot failure.

The fix keeps credential checks strict for API-key based provider accounts, but
skips credential env validation for explicit no-auth local accounts.

## Changed Files

- `agentflow_studio/model_gateway/provider_account_pool.py`
- `tests/test_codex_image_handoff.py`
- `TASK_TRACKER.md`
- `DEVLOG.md`

## Verification

```powershell
python -m pytest tests\test_codex_image_handoff.py -q
python -m pytest tests\test_provider_adapter_registry.py -q
```

Result:

```text
16 passed
27 passed
```

The project-standard `.venv\Scripts\python.exe` entrypoint was not present in
this checkout, so verification used the available `python` command.

## Provider Gates

- `AFS_ALLOW_REMOTE_IMAGE` was only set inside unit tests via monkeypatch.
- No live provider call was made.
- LLM, ASR, video, and external download gates were not opened.

## Boundaries

- No secret, token, provider key, signed URL, local media byte, or provider raw
  response was read or written.
- No private Company OS source content was copied into the repo.
- The fix allows Runtime to queue the local handoff job. A running image worker
  is still required for live asset image completion.

