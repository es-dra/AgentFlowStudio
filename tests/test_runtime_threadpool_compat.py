from __future__ import annotations

import anyio

from apps.api.runtime_threadpool_compat import configure_runtime_threadpool_compat


def test_runtime_threadpool_compat_allows_sync_call_to_complete() -> None:
    configure_runtime_threadpool_compat()

    async def run() -> int:
        return await anyio.to_thread.run_sync(lambda: 42)

    assert anyio.run(run) == 42
