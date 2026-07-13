from __future__ import annotations

import ast
import base64
import hashlib
import inspect
import textwrap

import pytest

from agentflow.harness.json_io import write_json
from agentflow_studio.model_gateway.codex_image_handoff import _safe_outputs, completed_result_payload
from apps.api.runtime_generated_image_assets import register_generated_image_asset
from apps.api.runtime_image_assets import image_asset_metadata, public_reusable_image_asset
from apps.api.runtime_keyframe_async import _provider_outputs_from_candidate_files
from apps.api.runtime_keyframe_routes import (
    _candidate_previews,
    _candidate_records,
    _rebind_replay_candidate_authority,
    _reusable_image_assets,
)
from apps.api.runtime_store import RuntimeStore


PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


@pytest.mark.parametrize(
    "producer",
    (
        completed_result_payload,
        _safe_outputs,
        _provider_outputs_from_candidate_files,
    ),
    ids=("codex_completed_result", "codex_safe_outputs", "verified_candidate_files"),
)
def test_internal_successful_candidate_producer_inventory_sets_explicit_status(producer) -> None:
    tree = ast.parse(textwrap.dedent(inspect.getsource(producer)))
    candidate_dicts = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        keys = [key.value for key in node.keys if isinstance(key, ast.Constant) and isinstance(key.value, str)]
        if "candidate_id" in keys:
            candidate_dicts.append(node)

    assert candidate_dicts
    for candidate in candidate_dicts:
        values = {
            key.value: value.value
            for key, value in zip(candidate.keys, candidate.values)
            if isinstance(key, ast.Constant)
            and isinstance(key.value, str)
            and isinstance(value, ast.Constant)
        }
        assert values.get("status") == "succeeded"


def test_reusable_asset_authority_uses_candidate_bytes_and_filters_non_success(tmp_path) -> None:
    store = RuntimeStore(tmp_path)
    project_id = "proj_reusable_contract"
    job_id = "proj_reusable_contract-keyframe_generation-abc123"
    store.ensure_project_manifest(project_id)
    output_dir = store.run_dir(project_id, job_id)
    image_dir = output_dir / "image_candidates"
    image_dir.mkdir(parents=True)
    for candidate_id in ("candidate_001", "candidate_002", "candidate_003"):
        (image_dir / f"{candidate_id}.png").write_bytes(PNG_BYTES)

    records = _candidate_records(
        output_dir,
        [
            {"candidate_id": "candidate_001", "status": "succeeded", "sha256": "provider-value-is-not-authority"},
            {"candidate_id": "candidate_002", "status": "failed"},
            {"candidate_id": "candidate_003", "status": "retryable"},
        ],
    )
    previews = _candidate_previews(project_id, job_id, records)
    assets = _reusable_image_assets(
        store,
        project_id,
        source_node_id="image-node-001",
        job_id=job_id,
        records=records,
    )

    expected_digest = hashlib.sha256(PNG_BYTES).hexdigest()
    assert [record["candidate_id"] for record in records] == ["candidate_001"]
    assert previews[0]["sha256"] == expected_digest
    assert len(assets) == 1
    assert assets[0]["status"] == "succeeded"
    assert assets[0]["source_candidate_id"] == "candidate_001"
    assert assets[0]["source_job_id"] == job_id
    assert assets[0]["source_candidate_digest"] == expected_digest
    assert assets[0]["sha256"] == expected_digest


def test_reusable_asset_registration_rejects_false_authority_and_unsafe_ids(tmp_path) -> None:
    store = RuntimeStore(tmp_path)
    project_id = "proj_reusable_reject"
    store.ensure_project_manifest(project_id)
    image_path = store.run_dir(project_id, "job-safe") / "image_candidates" / "candidate_001.png"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(PNG_BYTES)

    with pytest.raises(ValueError, match="digest does not match"):
        register_generated_image_asset(
            store,
            project_id,
            source_node_id="image-node-001",
            source_job_id="job-safe",
            source_candidate_id="candidate_001",
            image_path=image_path,
            source_candidate_digest="0" * 64,
            source_candidate_status="succeeded",
        )
    with pytest.raises(ValueError, match="candidate_NNN"):
        register_generated_image_asset(
            store,
            project_id,
            source_node_id="image-node-001",
            source_job_id="job-safe",
            source_candidate_id="candidate-1",
            image_path=image_path,
            source_candidate_status="succeeded",
        )
    with pytest.raises(ValueError, match="safe runtime identifier"):
        register_generated_image_asset(
            store,
            project_id,
            source_node_id="image-node-001",
            source_job_id="job with spaces",
            source_candidate_id="candidate_001",
            image_path=image_path,
            source_candidate_status="succeeded",
        )
    with pytest.raises(ValueError, match="only succeeded"):
        register_generated_image_asset(
            store,
            project_id,
            source_node_id="image-node-001",
            source_job_id="job-safe",
            source_candidate_id="candidate_001",
            image_path=image_path,
            source_candidate_status="retryable",
        )


@pytest.mark.parametrize(
    ("source_status", "error"),
    [
        (None, "status is invalid"),
        ("failed", "only succeeded"),
        ("retryable", "only succeeded"),
        ("success", "status is invalid"),
        ("SUCCEEDED", "status is invalid"),
        (7, "status is invalid"),
    ],
    ids=["missing", "failed", "retryable", "alias", "not-normalized", "type-invalid"],
)
def test_direct_registration_requires_explicit_normalized_success(tmp_path, source_status, error) -> None:
    store = RuntimeStore(tmp_path)
    project_id = "proj_reusable_status_reject"
    store.ensure_project_manifest(project_id)
    image_path = store.run_dir(project_id, "job-status") / "image_candidates" / "candidate_001.png"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(PNG_BYTES)
    status_args = {} if source_status is None else {"source_candidate_status": source_status}

    with pytest.raises(ValueError, match=error):
        register_generated_image_asset(
            store,
            project_id,
            source_node_id="image-node-001",
            source_job_id="job-status",
            source_candidate_id="candidate_001",
            image_path=image_path,
            **status_args,
        )


@pytest.mark.parametrize(
    "outputs",
    [
        [{"candidate_id": "candidate_001"}],
        [{"candidate_id": "candidate_001", "status": "failed"}],
        [{"candidate_id": "candidate_001", "status": "retryable"}],
        [{"candidate_id": "candidate_001", "status": "success"}],
        [{"candidate_id": "candidate_001", "status": 7}],
        [
            {"candidate_id": "candidate_001", "status": "succeeded"},
            {"candidate_id": "candidate_001", "status": "succeeded"},
        ],
    ],
    ids=["missing", "failed", "retryable", "invalid", "type-invalid", "duplicate"],
)
def test_candidate_projection_leaves_ambiguous_authority_unbound(tmp_path, outputs) -> None:
    store = RuntimeStore(tmp_path)
    project_id = "proj_reusable_projection_reject"
    job_id = "job-projection"
    store.ensure_project_manifest(project_id)
    output_dir = store.run_dir(project_id, job_id)
    image_path = output_dir / "image_candidates" / "candidate_001.png"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(PNG_BYTES)

    records = _candidate_records(output_dir, outputs)

    assert records == []
    assert _candidate_previews(project_id, job_id, records) == []
    assert _reusable_image_assets(
        store,
        project_id,
        source_node_id="image-node-001",
        job_id=job_id,
        records=records,
    ) == []


def test_existing_additive_generated_asset_digest_is_upgraded_only_from_matching_bytes(tmp_path) -> None:
    store = RuntimeStore(tmp_path)
    project_id = "proj_reusable_compat"
    job_id = "job-compat"
    store.ensure_project_manifest(project_id)
    image_path = store.run_dir(project_id, job_id) / "image_candidates" / "candidate_001.png"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(PNG_BYTES)

    registered = register_generated_image_asset(
        store,
        project_id,
        source_node_id="image-node-001",
        source_job_id=job_id,
        source_candidate_id="candidate_001",
        image_path=image_path,
        source_candidate_status="succeeded",
    )
    metadata = image_asset_metadata(store, project_id, registered["asset"]["asset_id"])
    metadata.pop("source_candidate_digest")
    metadata_path = (
        store.projects_dir
        / project_id
        / "image_assets"
        / registered["asset"]["asset_id"]
        / "image_asset.json"
    )
    write_json(metadata_path, metadata)

    with pytest.raises(ValueError):
        public_reusable_image_asset(metadata)

    repeated = register_generated_image_asset(
        store,
        project_id,
        source_node_id="image-node-001",
        source_job_id=job_id,
        source_candidate_id="candidate_001",
        image_path=image_path,
        source_candidate_status="succeeded",
    )
    assert repeated["asset"]["source_candidate_digest"] == hashlib.sha256(PNG_BYTES).hexdigest()

    rebound = _rebind_replay_candidate_authority(
        store,
        project_id,
        source_node_id="image-node-001",
        response={
            "job": {"job_id": job_id},
            "candidate_previews": [{"candidate_id": "candidate_001", "sha256": "legacy-value"}],
            "reusable_image_assets": [repeated["asset"]],
        },
    )
    assert rebound["candidate_previews"][0]["sha256"] == hashlib.sha256(PNG_BYTES).hexdigest()
    assert rebound["reusable_image_assets"][0]["status"] == "succeeded"
    assert rebound["reusable_image_assets"][0]["source_candidate_digest"] == hashlib.sha256(PNG_BYTES).hexdigest()


@pytest.mark.parametrize(
    "asset_statuses",
    [
        [None],
        ["failed"],
        ["retryable"],
        ["success"],
        [7],
        ["succeeded", "succeeded"],
    ],
    ids=["missing", "failed", "retryable", "invalid", "type-invalid", "duplicate"],
)
def test_replay_leaves_ambiguous_asset_authority_unbound(tmp_path, asset_statuses) -> None:
    store = RuntimeStore(tmp_path)
    project_id = "proj_reusable_replay_reject"
    job_id = "job-replay"
    store.ensure_project_manifest(project_id)
    image_path = store.run_dir(project_id, job_id) / "image_candidates" / "candidate_001.png"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(PNG_BYTES)
    registered = register_generated_image_asset(
        store,
        project_id,
        source_node_id="image-node-001",
        source_job_id=job_id,
        source_candidate_id="candidate_001",
        image_path=image_path,
        source_candidate_status="succeeded",
    )
    assets = []
    for status in asset_statuses:
        asset = dict(registered["asset"])
        if status is None:
            asset.pop("status")
        else:
            asset["status"] = status
        assets.append(asset)

    rebound = _rebind_replay_candidate_authority(
        store,
        project_id,
        source_node_id="image-node-001",
        response={
            "job": {"job_id": job_id},
            "candidate_previews": [{"candidate_id": "candidate_001"}],
            "reusable_image_assets": assets,
        },
    )

    assert rebound["candidate_previews"] == []
    assert rebound["reusable_image_assets"] == []


def test_replay_rebind_keeps_digest_conflict_unbound(tmp_path) -> None:
    store = RuntimeStore(tmp_path)
    project_id = "proj_reusable_conflict"
    job_id = "job-conflict"
    store.ensure_project_manifest(project_id)
    image_path = store.run_dir(project_id, job_id) / "image_candidates" / "candidate_001.png"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(PNG_BYTES)
    registered = register_generated_image_asset(
        store,
        project_id,
        source_node_id="image-node-001",
        source_job_id=job_id,
        source_candidate_id="candidate_001",
        image_path=image_path,
        source_candidate_status="succeeded",
    )
    metadata = image_asset_metadata(store, project_id, registered["asset"]["asset_id"])
    metadata["sha256"] = "0" * 64
    metadata_path = (
        store.projects_dir
        / project_id
        / "image_assets"
        / registered["asset"]["asset_id"]
        / "image_asset.json"
    )
    write_json(metadata_path, metadata)

    rebound = _rebind_replay_candidate_authority(
        store,
        project_id,
        source_node_id="image-node-001",
        response={
            "job": {"job_id": job_id},
            "candidate_previews": [{"candidate_id": "candidate_001"}],
            "reusable_image_assets": [metadata],
        },
    )

    assert rebound["candidate_previews"] == []
    assert rebound["reusable_image_assets"] == []
