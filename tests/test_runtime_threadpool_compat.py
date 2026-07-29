from __future__ import annotations

import anyio

from apps.api.runtime_threadpool_compat import THREADPOOL_COMPAT_ENV, configure_runtime_threadpool_compat


def test_runtime_uses_anyio_native_threadpool_by_default(monkeypatch) -> None:
    monkeypatch.delenv(THREADPOOL_COMPAT_ENV, raising=False)
    native_run_sync = anyio.to_thread.run_sync

    assert configure_runtime_threadpool_compat() is False
    assert anyio.to_thread.run_sync is native_run_sync

    async def run() -> int:
        return await anyio.to_thread.run_sync(lambda: 42)

    assert anyio.run(run) == 42
