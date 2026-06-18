from __future__ import annotations

import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor
from collections.abc import Callable
from typing import Any, TypeVar

import anyio.to_thread


T = TypeVar("T")


def configure_runtime_threadpool_compat() -> None:
    """Keep FastAPI sync routes usable when anyio's thread bridge is unavailable."""
    if getattr(anyio.to_thread.run_sync, "_afs_asyncio_threadpool", False):
        return

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
        with ThreadPoolExecutor(max_workers=1, thread_name_prefix="afs-runtime-sync") as executor:
            return await loop.run_in_executor(executor, call)

    run_sync._afs_asyncio_threadpool = True  # type: ignore[attr-defined]
    anyio.to_thread.run_sync = run_sync  # type: ignore[assignment]


__all__ = ("configure_runtime_threadpool_compat",)
