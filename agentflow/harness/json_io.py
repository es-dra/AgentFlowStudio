from __future__ import annotations

import json
import os
import errno
import random
import tempfile
import threading
import time
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterator

from pydantic import BaseModel


_WINDOWS_LOCK_TIMEOUT_SECONDS = 30.0
_WINDOWS_LOCK_INITIAL_DELAY_SECONDS = 0.005
_WINDOWS_LOCK_MAX_DELAY_SECONDS = 0.1
_RETRIABLE_WINDOWS_LOCK_ERRNOS = {
    errno.EACCES,
    errno.EAGAIN,
    getattr(errno, "EDEADLK", 36),
    getattr(errno, "EWOULDBLOCK", errno.EAGAIN),
}


def write_json(path: str | Path, data: Any) -> Path:
    output_path = Path(path)
    os.makedirs(system_path(output_path.parent), exist_ok=True)
    text = json.dumps(_to_jsonable(data), ensure_ascii=False, indent=2)
    with exclusive_file_lock(_lock_path(output_path)):
        fd, temp_name = tempfile.mkstemp(
            prefix=".tmp-",
            suffix=".tmp",
            dir=system_path(output_path.parent),
            text=True,
        )
        temp_path = Path(temp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(system_path(temp_path), system_path(output_path))
            _fsync_dir(output_path.parent)
        finally:
            try:
                os.unlink(system_path(temp_path))
            except FileNotFoundError:
                pass
    return output_path


@contextmanager
def exclusive_file_lock(path: str | Path) -> Iterator[None]:
    lock_path = Path(path)
    os.makedirs(system_path(lock_path.parent), exist_ok=True)
    with open(system_path(lock_path), "a+b") as handle:
        _lock_handle(handle, lock_path)
        try:
            yield
        finally:
            _unlock_handle(handle)


def _to_jsonable(data: Any) -> Any:
    if isinstance(data, BaseModel):
        return data.model_dump(mode="json")
    if isinstance(data, list):
        return [_to_jsonable(item) for item in data]
    if isinstance(data, tuple):
        return [_to_jsonable(item) for item in data]
    if isinstance(data, dict):
        return {key: _to_jsonable(value) for key, value in data.items()}
    return data


def _lock_path(path: Path) -> Path:
    lock_identity = os.path.normcase(path.name) if os.name == "nt" else path.name
    digest = sha256(lock_identity.encode("utf-8")).hexdigest()
    return path.with_name(f".json-lock-{digest}.lock")


def _lock_handle(handle: Any, path: Path) -> None:
    if os.name == "nt":
        _lock_windows_handle(handle, path)
        return
    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)


def _lock_windows_handle(handle: Any, path: Path) -> None:
    import msvcrt

    deadline = time.monotonic() + _WINDOWS_LOCK_TIMEOUT_SECONDS
    delay = _WINDOWS_LOCK_INITIAL_DELAY_SECONDS
    attempts = 0
    rng = random.Random((os.getpid() << 16) ^ threading.get_ident() ^ time.monotonic_ns())
    while True:
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            return
        except OSError as exc:
            if not _is_retriable_windows_lock_error(exc):
                raise
            attempts += 1
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(
                    "timed out acquiring JSON lock "
                    f"{path.name!r} after {attempts} attempts; "
                    f"last errno={getattr(exc, 'errno', None)}"
                ) from exc
            sleep_for = min(delay + rng.uniform(0, delay), remaining)
            time.sleep(sleep_for)
            delay = min(delay * 1.5, _WINDOWS_LOCK_MAX_DELAY_SECONDS)


def _is_retriable_windows_lock_error(exc: OSError) -> bool:
    return getattr(exc, "errno", None) in _RETRIABLE_WINDOWS_LOCK_ERRNOS


def _unlock_handle(handle: Any) -> None:
    if os.name == "nt":
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        return
    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def system_path(path: str | Path) -> str:
    platform_path = Path(path)
    if os.name != "nt":
        return str(platform_path)
    resolved = str(platform_path.resolve())
    if resolved.startswith("\\\\?\\"):
        return resolved
    if resolved.startswith("\\\\"):
        return "\\\\?\\UNC\\" + resolved[2:]
    return "\\\\?\\" + resolved


def _fsync_dir(path: Path) -> None:
    if os.name == "nt":
        return
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
