# AFS Asset Card Image Worker Codex Home Fix - 2026-06-29

## Summary

After the `codex_image` handoff submission fix, asset-card image generation can
still fail if the deployed worker starts `codex exec` with an empty job-scoped
Codex home. The worker previously overwrote `AFS_CODEX_HOME` for every job,
which could discard the server's configured Codex authentication/runtime state.

This pass preserves explicit `AFS_CODEX_HOME` or `CODEX_HOME` values and only
uses a job-scoped `.codex-home` fallback when no Codex home is configured.

Runtime polling also preserves safe worker failure blocks so the Studio node can
show whether the worker command is unavailable, timed out, or failed to write a
candidate image instead of always surfacing a generic provider-not-ready reason.

## Changed Files

- `agentflow_studio/model_gateway/codex_image_worker.py`
- `agentflow_studio/model_gateway/codex_runtime_env.py`
- `agentflow_studio/model_gateway/codex_image_handoff.py`
- `apps/api/runtime_keyframe_async.py`
- `tests/test_codex_image_handoff.py`
- `tests/test_codex_runtime_env.py`
- `TASK_TRACKER.md`
- `DEVLOG.md`

## Verification

```powershell
python -m pytest tests\test_codex_image_handoff.py -q
python -m pytest tests\test_codex_runtime_env.py -q
python -m pytest tests\test_provider_adapter_registry.py -q
```

Result:

```text
18 passed
5 passed
27 passed
```

## Provider Gates

- `AFS_ALLOW_REMOTE_IMAGE` was only set inside unit tests via monkeypatch.
- No live provider call was made.
- LLM, ASR, video, and external download gates were not opened.

## Server Retest Notes

After deploy, check:

```bash
systemctl status afs-runtime-zhaowei --no-pager -l
systemctl list-units --type=service --all | grep -E 'afs|codex|image|worker'
```

If the image worker has a separate service, restart it after pulling the code.
If the next Studio failure still appears, inspect the safe node reason and the
worker service journal. Expected safe reasons now include:

- `Image generation worker command is not available.`
- `Image generation worker timed out before creating a usable image.`
- `Image generation worker did not create a usable image.`
- `Image generation worker configuration is not ready.`

Do not print or commit real Codex auth files, provider keys, signed URLs, or raw
provider responses.

