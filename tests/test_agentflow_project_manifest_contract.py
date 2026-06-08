from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from agentflow.contracts.project_manifest import validate_project_manifest

EXAMPLE_MANIFEST = Path("examples/agentflow/project_manifest.example.json")


def test_agentflow_project_manifest_v0_1_contract_is_local_project_workbench() -> None:
    payload = json.loads(EXAMPLE_MANIFEST.read_text(encoding="utf-8"))

    validate_project_manifest(payload)

    assert payload["artifact_type"] == "agentflow_project_manifest"
    assert payload["schema_version"] == "0.1.0"
    assert payload["project_type"] == "short_video_campaign"
    assert payload["goal"]
    assert isinstance(payload["source_assets"], list)
    assert isinstance(payload["runs"], list)
    assert isinstance(payload["packages"], list)
    assert isinstance(payload["feedback_refs"], list)
    assert isinstance(payload["profile_version_refs"], list)
    assert payload["status"] in {"in_progress", "blocked", "ready_for_next_round"}
    assert payload["does_not_store_private_asset_bytes"] is True
    assert payload["does_not_store_secrets"] is True
    assert payload["does_not_auto_sync"] is True


def test_agentflow_project_manifest_rejects_private_paths_or_secrets() -> None:
    payload = json.loads(EXAMPLE_MANIFEST.read_text(encoding="utf-8"))
    unsafe = deepcopy(payload)
    unsafe["source_assets"] = [{"asset_id": "local", "ref": "D:\\private\\material.mp4"}]

    with pytest.raises(ValueError, match="private"):
        validate_project_manifest(unsafe)


def test_agentflow_project_manifest_requires_runtime_refs_to_be_lists() -> None:
    payload = json.loads(EXAMPLE_MANIFEST.read_text(encoding="utf-8"))
    invalid = deepcopy(payload)
    invalid["runs"] = "run:round-1"

    with pytest.raises(ValueError, match="runs"):
        validate_project_manifest(invalid)
