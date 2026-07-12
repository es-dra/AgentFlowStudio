from __future__ import annotations

import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from agentflow.harness.json_io import exclusive_file_lock, write_json


def _system_path(path: Path) -> str:
    resolved = str(path.resolve())
    if resolved.startswith("\\\\?\\"):
        return resolved
    if resolved.startswith("\\\\"):
        return "\\\\?\\UNC\\" + resolved[2:]
    return "\\\\?\\" + resolved


def _long_directory(tmp_path: Path) -> Path:
    path = tmp_path
    for index in range(6):
        path /= f"segment-{index}-" + ("x" * 36)
    os.makedirs(_system_path(path), exist_ok=True)
    assert len(str(path.resolve())) > 260
    return path


def _long_json_filename() -> str:
    filename = ("state-" + ("y" * 232)) + ".json"
    assert len(filename) == 243
    assert len(filename + ".lock") <= 255
    return filename


def test_write_json_atomic_concurrent_writes_keep_valid_json(tmp_path) -> None:
    path = tmp_path / "state.json"

    def write_value(index: int) -> None:
        write_json(path, {"index": index, "values": list(range(25))})

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(write_value, range(40)))

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload["index"], int)
    assert payload["values"] == list(range(25))
    assert (tmp_path / "state.json.lock").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows long-path semantics")
def test_write_json_supports_windows_long_paths_without_temp_residue(tmp_path) -> None:
    directory = _long_directory(tmp_path)
    path = directory / _long_json_filename()

    returned = write_json(path, {"status": "ready", "value": 7})

    with open(_system_path(path), encoding="utf-8") as handle:
        assert json.load(handle) == {"status": "ready", "value": 7}
    assert returned == path
    assert os.path.exists(_system_path(directory / f"{path.name}.lock"))
    with os.scandir(_system_path(directory)) as entries:
        assert not [entry.name for entry in entries if entry.name.endswith(".tmp")]


@pytest.mark.skipif(os.name != "nt", reason="Windows long-path semantics")
def test_write_json_concurrent_writes_support_windows_long_paths(tmp_path) -> None:
    directory = _long_directory(tmp_path)
    path = directory / _long_json_filename()

    def write_value(index: int) -> None:
        write_json(path, {"index": index, "values": list(range(25))})

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(write_value, range(40)))

    with open(_system_path(path), encoding="utf-8") as handle:
        payload = json.load(handle)
    assert isinstance(payload["index"], int)
    assert payload["values"] == list(range(25))
    with os.scandir(_system_path(directory)) as entries:
        assert not [entry.name for entry in entries if entry.name.endswith(".tmp")]


@pytest.mark.skipif(os.name != "nt", reason="Windows long-path semantics")
def test_exclusive_file_lock_serializes_windows_long_path_access(tmp_path) -> None:
    lock_path = _long_directory(tmp_path) / "state.json.lock"
    entered = threading.Event()
    release = threading.Event()
    second_entered = threading.Event()

    def first_holder() -> None:
        with exclusive_file_lock(lock_path):
            entered.set()
            assert release.wait(timeout=5)

    def second_holder() -> None:
        assert entered.wait(timeout=5)
        with exclusive_file_lock(lock_path):
            second_entered.set()

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(first_holder)
        second = executor.submit(second_holder)
        assert entered.wait(timeout=5)
        assert not second_entered.wait(timeout=0.2)
        release.set()
        first.result(timeout=5)
        second.result(timeout=5)

    assert second_entered.is_set()
