from __future__ import annotations

import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from agentflow.harness.json_io import (
    _lock_path,
    exclusive_file_lock,
    system_path,
    write_json,
)


def _long_directory(tmp_path: Path) -> Path:
    path = tmp_path
    for index in range(6):
        path /= f"segment-{index}-" + ("x" * 36)
    os.makedirs(system_path(path), exist_ok=True)
    assert len(str(path.resolve())) > 260
    return path


def _long_json_filename() -> str:
    filename = ("state-" + ("y" * 232)) + ".json"
    assert len(filename) == 243
    return filename


def _maximum_length_json_filename() -> str:
    filename = ("state-" + ("z" * 244)) + ".json"
    assert len(filename) == 255
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
    assert _lock_path(tmp_path / "state.json").exists()


def test_lock_path_name_is_bounded_for_maximum_length_filename(tmp_path) -> None:
    path = tmp_path / _maximum_length_json_filename()

    lock_path = _lock_path(path)

    assert lock_path.parent == tmp_path
    assert len(lock_path.name) <= 255
    assert lock_path.name.startswith(".json-lock-")


def test_system_path_is_plain_string_on_non_windows(tmp_path) -> None:
    if os.name == "nt":
        pytest.skip("non-Windows path form")

    assert system_path(tmp_path / "state.json") == str(tmp_path / "state.json")


@pytest.mark.skipif(os.name != "nt", reason="Windows long-path semantics")
def test_write_json_supports_windows_long_paths_without_temp_residue(tmp_path) -> None:
    directory = _long_directory(tmp_path)
    path = directory / _long_json_filename()

    returned = write_json(path, {"status": "ready", "value": 7})

    with open(system_path(path), encoding="utf-8") as handle:
        assert json.load(handle) == {"status": "ready", "value": 7}
    assert returned == path
    assert os.path.exists(system_path(_lock_path(path)))
    with os.scandir(system_path(directory)) as entries:
        assert not [entry.name for entry in entries if entry.name.endswith(".tmp")]


@pytest.mark.skipif(os.name != "nt", reason="Windows long-path semantics")
def test_write_json_concurrent_writes_support_windows_long_paths(tmp_path) -> None:
    directory = _long_directory(tmp_path)
    path = directory / _long_json_filename()

    def write_value(index: int) -> None:
        write_json(path, {"index": index, "values": list(range(25))})

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(write_value, range(40)))

    with open(system_path(path), encoding="utf-8") as handle:
        payload = json.load(handle)
    assert isinstance(payload["index"], int)
    assert payload["values"] == list(range(25))
    with os.scandir(system_path(directory)) as entries:
        assert not [entry.name for entry in entries if entry.name.endswith(".tmp")]


@pytest.mark.skipif(os.name != "nt", reason="Windows filename boundary semantics")
def test_write_json_supports_maximum_length_windows_filename(tmp_path) -> None:
    path = tmp_path / _maximum_length_json_filename()

    write_json(path, {"status": "ready"})

    with open(system_path(path), encoding="utf-8") as handle:
        assert json.load(handle) == {"status": "ready"}
    assert len(_lock_path(path).name) <= 255
    assert os.path.exists(system_path(_lock_path(path)))


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
