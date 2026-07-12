from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

from agentflow.harness.json_io import write_json


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
