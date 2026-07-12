from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from apps.api.runtime_store import RuntimeStore


pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows long-path semantics")


def _system_path(path: Path) -> str:
    resolved = str(path.resolve())
    if resolved.startswith("\\\\?\\"):
        return resolved
    if resolved.startswith("\\\\"):
        return "\\\\?\\UNC\\" + resolved[2:]
    return "\\\\?\\" + resolved


def _long_artifact_path(root: Path, filename: str) -> Path:
    path = root / "runs" / "project"
    for index in range(5):
        path /= f"segment-{index}-" + ("x" * 36)
    os.makedirs(_system_path(path), exist_ok=True)
    artifact_path = path / filename
    assert len(str(artifact_path.resolve())) > 260
    return artifact_path


def test_runtime_store_registers_and_reads_long_path_json_artifact(tmp_path) -> None:
    store = RuntimeStore(tmp_path)
    path = _long_artifact_path(tmp_path, "manifest.json")
    with open(_system_path(path), "w", encoding="utf-8") as handle:
        json.dump({"artifact_type": "long_path_manifest", "value": 7}, handle)

    ref = store.register_artifact(path, role="safe_manifest")
    result = store.read_artifact(ref["artifact_id"])

    assert result["payload"] == {"artifact_type": "long_path_manifest", "value": 7}


def test_runtime_store_registers_and_reads_long_path_text_artifact(tmp_path) -> None:
    store = RuntimeStore(tmp_path)
    path = _long_artifact_path(tmp_path, "notes.md")
    with open(_system_path(path), "w", encoding="utf-8") as handle:
        handle.write("safe long-path artifact")

    ref = store.register_artifact(path, role="review_note")
    result = store.read_artifact(ref["artifact_id"])

    assert result["text"] == "safe long-path artifact"
