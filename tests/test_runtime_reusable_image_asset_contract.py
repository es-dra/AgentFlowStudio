from __future__ import annotations

import ast
import base64
import hashlib
import inspect
import json
import textwrap
from pathlib import Path

import pytest

from agentflow.harness.json_io import write_json
from agentflow_studio.model_gateway.codex_image_handoff import _safe_outputs, completed_result_payload
from agentflow_studio.model_gateway.provider_api_relay_images import write_image_outputs
from apps.api.runtime_generated_image_assets import (
    register_generated_image_asset,
    resolve_generated_candidate_authority,
)
from apps.api.runtime_image_assets import (
    image_asset_metadata,
    public_reusable_image_asset,
    resolve_reference_images,
)
from apps.api.runtime_keyframe_async import _provider_outputs_from_candidate_files
from apps.api.runtime_keyframes import _provider_outputs
from apps.api.runtime_keyframe_routes import (
    _candidate_previews,
    _candidate_records,
    _rebind_replay_candidate_authority,
    _reusable_image_assets,
    register_runtime_keyframe_routes,
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
        write_image_outputs,
        _provider_outputs_from_candidate_files,
    ),
    ids=("codex_completed_result", "codex_safe_outputs", "api_relay_writer", "verified_candidate_files"),
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


def test_trusted_image_candidate_producer_inventory_is_exhaustive_and_explicit() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    source_paths = sorted((repository_root / "agentflow_studio" / "model_gateway").glob("*image*.py"))
    source_paths.append(repository_root / "apps" / "api" / "runtime_keyframe_async.py")
    discovered: set[str] = set()
    for source_path in source_paths:
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        for function in (node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))):
            has_outputs_container = any(
                isinstance(node, ast.Dict)
                and any(isinstance(key, ast.Constant) and key.value == "outputs" for key in node.keys)
                for node in ast.walk(function)
            )
            has_outputs_append = any(
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "append"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "outputs"
                for node in ast.walk(function)
            )
            has_candidate_id = any(
                isinstance(node, ast.Dict)
                and any(isinstance(key, ast.Constant) and key.value == "candidate_id" for key in node.keys)
                for node in ast.walk(function)
            )
            if has_candidate_id and (has_outputs_container or has_outputs_append):
                discovered.add(f"{source_path.name}:{function.name}")

    assert discovered == {
        "codex_image_handoff.py:_safe_outputs",
        "codex_image_handoff.py:completed_result_payload",
        "provider_api_relay_images.py:write_image_outputs",
        "runtime_keyframe_async.py:_provider_outputs_from_candidate_files",
    }


def test_api_relay_writer_marks_verified_success_without_provider_call(tmp_path) -> None:
    outputs = write_image_outputs(
        tmp_path,
        {"data": [{"b64_json": base64.b64encode(PNG_BYTES).decode("ascii")}]},
        1,
    )

    assert outputs == [
        {
            "candidate_id": "candidate_001",
            "status": "succeeded",
            "image_path": "image_candidates/candidate_001.png",
            "byte_count": len(PNG_BYTES),
            "sha256": hashlib.sha256(PNG_BYTES).hexdigest(),
            "width": 1,
            "height": 1,
            "aspect_ratio": "1:1",
            "provider_url_persisted": False,
        }
    ]


def test_api_relay_writer_integrates_through_runtime_candidate_authority_without_provider_call(tmp_path) -> None:
    store = RuntimeStore(tmp_path)
    project_id = "proj_api_relay_authority"
    job_id = "job-api-relay-authority"
    store.ensure_project_manifest(project_id)
    output_dir = store.run_dir(project_id, job_id)
    outputs = write_image_outputs(
        output_dir,
        {"data": [{"b64_json": base64.b64encode(PNG_BYTES).decode("ascii")}]},
        1,
    )

    provider_outputs = _provider_outputs({"status": "succeeded", "outputs": outputs})
    records = _candidate_records(store, project_id, job_id, provider_outputs)
    assets = _reusable_image_assets(
        store,
        project_id,
        source_node_id="image-node-api-relay",
        job_id=job_id,
        records=records,
    )

    assert [item["candidate_id"] for item in records] == ["candidate_001"]
    assert records[0]["sha256"] == hashlib.sha256(PNG_BYTES).hexdigest()
    assert assets[0]["status"] == "succeeded"
    assert assets[0]["source_job_id"] == job_id


def test_runtime_candidate_authority_consumer_inventory_uses_one_resolver_or_thin_forwarder() -> None:
    resolver_name = resolve_generated_candidate_authority.__name__
    direct_consumers = (
        register_generated_image_asset,
        _candidate_records,
        image_asset_metadata,
        register_runtime_keyframe_routes,
    )
    for consumer in direct_consumers:
        assert resolver_name in inspect.getsource(consumer)
    assert "_candidate_records" in inspect.getsource(_rebind_replay_candidate_authority)
    reference_source = inspect.getsource(resolve_reference_images)
    assert "image_asset_metadata" in reference_source
    assert "image_asset_file_path" in reference_source


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
        store,
        project_id,
        job_id,
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


def test_registration_rejects_candidate_path_from_different_job(tmp_path) -> None:
    store = RuntimeStore(tmp_path)
    project_id = "proj_reusable_job_path"
    store.ensure_project_manifest(project_id)
    image_path = store.run_dir(project_id, "job-a") / "image_candidates" / "candidate_001.png"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(PNG_BYTES)

    with pytest.raises(ValueError, match="canonical candidate"):
        register_generated_image_asset(
            store,
            project_id,
            source_node_id="image-node-001",
            source_job_id="job-b",
            source_candidate_id="candidate_001",
            image_path=image_path,
            source_candidate_status="succeeded",
        )


def test_reregistration_rejects_mutated_persisted_bytes(tmp_path) -> None:
    store = RuntimeStore(tmp_path)
    project_id = "proj_reusable_mutated_stored"
    job_id = "job-mutated-stored"
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
    stored_path = (
        store.projects_dir
        / project_id
        / "image_assets"
        / registered["asset"]["asset_id"]
        / "source.png"
    )
    stored_path.write_bytes(b"mutated-persisted-bytes")

    assert resolve_reference_images(store, project_id, [registered["asset"]["asset_id"]]) == []
    with pytest.raises(ValueError, match="stored bytes"):
        register_generated_image_asset(
            store,
            project_id,
            source_node_id="image-node-001",
            source_job_id=job_id,
            source_candidate_id="candidate_001",
            image_path=image_path,
            source_candidate_status="succeeded",
        )


def test_reregistration_rejects_duplicate_persisted_authority(tmp_path) -> None:
    store = RuntimeStore(tmp_path)
    project_id = "proj_reusable_duplicate_metadata"
    job_id = "job-duplicate-metadata"
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
    duplicate = dict(metadata)
    duplicate["asset_id"] = "aaa_duplicate"
    duplicate_path = store.projects_dir / project_id / "image_assets" / "aaa_duplicate" / "image_asset.json"
    duplicate_path.parent.mkdir(parents=True)
    write_json(duplicate_path, duplicate)

    assert resolve_reference_images(store, project_id, [registered["asset"]["asset_id"]]) == []
    with pytest.raises(ValueError, match="unique"):
        register_generated_image_asset(
            store,
            project_id,
            source_node_id="image-node-001",
            source_job_id=job_id,
            source_candidate_id="candidate_001",
            image_path=image_path,
            source_candidate_status="succeeded",
        )


def test_deterministic_asset_id_substitution_is_unbound(tmp_path) -> None:
    store = RuntimeStore(tmp_path)
    project_id = "proj_reusable_rogue_asset_id"
    job_id = "job-rogue-asset-id"
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
    original_dir = store.projects_dir / project_id / "image_assets" / registered["asset"]["asset_id"]
    rogue_dir = original_dir.parent / "rogue_authority"
    original_dir.rename(rogue_dir)
    metadata_path = rogue_dir / "image_asset.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["asset_id"] = "rogue_authority"
    metadata["preview_url"] = f"/projects/{project_id}/image-assets/rogue_authority/preview"
    write_json(metadata_path, metadata)

    assert resolve_reference_images(store, project_id, ["rogue_authority"]) == []
    with pytest.raises(ValueError, match="deterministic"):
        image_asset_metadata(store, project_id, "rogue_authority")
    with pytest.raises(ValueError, match="deterministic"):
        register_generated_image_asset(
            store,
            project_id,
            source_node_id="image-node-001",
            source_job_id=job_id,
            source_candidate_id="candidate_001",
            image_path=image_path,
            source_candidate_status="succeeded",
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

    records = _candidate_records(store, project_id, job_id, outputs)

    assert records == []
    assert _candidate_previews(project_id, job_id, records) == []
    assert _reusable_image_assets(
        store,
        project_id,
        source_node_id="image-node-001",
        job_id=job_id,
        records=records,
    ) == []


def test_legitimate_reregistration_and_replay_pass_but_missing_persisted_digest_fails_closed(tmp_path) -> None:
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
    with pytest.raises(ValueError, match="source_candidate_digest"):
        image_asset_metadata(store, project_id, registered["asset"]["asset_id"])
    with pytest.raises(ValueError, match="source_candidate_digest"):
        register_generated_image_asset(
            store,
            project_id,
            source_node_id="image-node-001",
            source_job_id=job_id,
            source_candidate_id="candidate_001",
            image_path=image_path,
            source_candidate_status="succeeded",
        )


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
