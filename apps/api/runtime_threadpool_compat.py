from __future__ import annotations

import asyncio
import functools
import os
from concurrent.futures import ThreadPoolExecutor
from collections.abc import Callable
from typing import Any, TypeVar

import anyio.to_thread


T = TypeVar("T")
THREADPOOL_COMPAT_ENV = "AFS_ENABLE_THREADPOOL_COMPAT"
THREADPOOL_WORKERS_ENV = "AFS_RUNTIME_SYNC_WORKERS"
_EXECUTOR: ThreadPoolExecutor | None = None


def configure_runtime_threadpool_compat(*, enabled: bool | None = None) -> bool:
    """Install the legacy bridge only for an explicitly enabled emergency fallback.

    AnyIO already provides a shared, capacity-limited worker pool for sync
    FastAPI routes. Replacing it unconditionally created and destroyed a new
    one-worker executor for every request.
    """
    if enabled is None:
        enabled = str(os.environ.get(THREADPOOL_COMPAT_ENV, "")).strip().lower() in {"1", "true", "yes", "on"}
    if not enabled:
        return False
    if getattr(anyio.to_thread.run_sync, "_afs_asyncio_threadpool", False):
        return True

    global _EXECUTOR
    if _EXECUTOR is None:
        try:
            configured_workers = int(str(os.environ.get(THREADPOOL_WORKERS_ENV, "")).strip())
        except ValueError:
            configured_workers = 0
        default_workers = min(32, (os.cpu_count() or 1) + 4)
        _EXECUTOR = ThreadPoolExecutor(
            max_workers=max(1, min(configured_workers or default_workers, 64)),
            thread_name_prefix="afs-runtime-sync-fallback",
        )

    async def run_sync(
        func: Callable[..., T],
        *args: Any,
        abandon_on_cancel: bool = False,
        cancellable: bool | None = None,
        limiter: Any = None,
    ) -> T:
        del abandon_on_cancel, cancellable, limiter
        loop = asyncio.get_running_loop()
        call = functools.partial(func, *args)
        return await loop.run_in_executor(_EXECUTOR, call)

    run_sync._afs_asyncio_threadpool = True  # type: ignore[attr-defined]
    anyio.to_thread.run_sync = run_sync  # type: ignore[assignment]
    return True


__all__ = ("THREADPOOL_COMPAT_ENV", "configure_runtime_threadpool_compat")
