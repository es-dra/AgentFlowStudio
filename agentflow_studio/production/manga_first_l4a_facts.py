from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any

from agentflow_studio.production.manga_first_l4a_aggregate import build_manga_first_episode_aggregate
from agentflow_studio.production.manga_first_l4a_checkpoints import CheckpointLedgerStore
from agentflow_studio.production.manga_first_l4a_compiler import validate_manga_first_manifest
from agentflow_studio.production.manga_first_l4a_reference_approval import build_reference_approval_gate
from agentflow_studio.production.manga_first_l4a_schema import (
    ProductionTruthManifest,
    json_digest,
    read_json_object,
    write_json_atomic,
)
from agentflow_studio.production.runtime_safe_io import safe_id


_CONTRACT = import_module("apps.api.runtime_episode_domain_contract")
_DOMAIN_STORE = import_module("apps.api.runtime_episode_domain_store")
_WORKSPACE_PROJECTION = import_module("apps.api.runtime_episode_workspace_projection")
EntityVersionRef = _CONTRACT.EntityVersionRef
ProductionProjectAggregate = _CONTRACT.ProductionProjectAggregate
TenantScope = _CONTRACT.TenantScope
AggregateNotFoundError = _DOMAIN_STORE.AggregateNotFoundError
AggregateSaveResult = _DOMAIN_STORE.AggregateSaveResult
AggregateVersionConflictError = _DOMAIN_STORE.AggregateVersionConflictError
EpisodeDomainAggregateStore = _DOMAIN_STORE.EpisodeDomainAggregateStore
build_creator_authoring_projection = _WORKSPACE_PROJECTION.build_creator_authoring_projection
build_episode_workspace_projection = _WORKSPACE_PROJECTION.build_episode_workspace_projection


MANGA_FIRST_RUNTIME_DIR = "manga_first_l4b"
MANGA_FIRST_WORKSPACE_REFS = "workspace_refs.json"
@dataclass(frozen=True)
class MangaFirstPersistenceResult:
    manifest: ProductionTruthManifest
    aggregate_result: AggregateSaveResult
    manifest_artifact: dict[str, Any]
    checkpoint_artifact: dict[str, Any]
    studio_workspace: dict[str, Any]
    gap_map: tuple[dict[str, Any], ...] = ()

def persist_manga_first_project(
    store: RuntimeStore,
    manifest_value: ProductionTruthManifest | dict[str, Any],
    *,
    scope: TenantScope,
    idempotency_key: str,
) -> MangaFirstPersistenceResult:
    manifest = validate_manga_first_manifest(manifest_value)
    aggregate_store = EpisodeDomainAggregateStore(store.root)
    aggregate = build_manga_first_episode_aggregate(manifest, scope=scope, aggregate_version=1)
    try:
        save_result = aggregate_store.save(
            aggregate,
            expected_aggregate_version=0,
            idempotency_key=idempotency_key,
            payload_digest=json_digest({"operation": "manga_first_l4b_create_truth", "manifest_sha256": manifest.manifest_sha256}),
        )
    except AggregateVersionConflictError as exc:
        if _existing_aggregate_gap_map(aggregate_store, scope=scope):
            raise AggregateVersionConflictError("existing aggregate requires a typed manga-first migration adapter") from exc
        raise
    project_dir = _project_dir(store, manifest.project_id)
    manifest_path = project_dir / "production_truth_manifest.json"
    checkpoint_path = project_dir / "checkpoint_ledger.json"
    write_json_atomic(manifest_path, _safe_manifest_artifact(manifest, save_result.aggregate_sha256))
    if not checkpoint_path.exists():
        CheckpointLedgerStore(checkpoint_path).initialize(manifest)
    manifest_ref = store.register_artifact(manifest_path, role="manga_first_production_truth_manifest")
    checkpoint_ref = store.register_artifact(checkpoint_path, role="manga_first_checkpoint_ledger")
    store.update_project_manifest(
        manifest.project_id,
        {
            "packages": [
                {
                    "artifact_id": manifest_ref["artifact_id"],
                    "artifact_type": manifest_ref["artifact_type"],
                    "role": manifest_ref["role"],
                    "manifest_sha256": manifest.manifest_sha256,
                }
            ],
            "runs": [
                {
                    "run_id": f"{safe_id(manifest.project_id)}-manga-first-l4b",
                    "artifact_type": "manga_first_l4b_production_truth",
                    "schema_version": manifest.schema_version,
                    "status": "provider_authorization_required",
                }
            ],
        },
        status="in_progress",
    )
    workspace = build_manga_first_studio_workspace(
        manifest,
        aggregate=save_result.aggregate,
        aggregate_sha256=save_result.aggregate_sha256,
        manifest_artifact=manifest_ref,
        checkpoint_artifact=checkpoint_ref,
    )
    write_json_atomic(
        project_dir / MANGA_FIRST_WORKSPACE_REFS,
        _workspace_refs(manifest, save_result.aggregate_sha256, manifest_ref, checkpoint_ref),
    )
    return MangaFirstPersistenceResult(
        manifest=manifest,
        aggregate_result=save_result,
        manifest_artifact=manifest_ref,
        checkpoint_artifact=checkpoint_ref,
        studio_workspace=workspace,
    )


def load_manga_first_studio_workspace(
    store: RuntimeStore,
    *,
    project_id: str,
    scope: TenantScope,
) -> dict[str, Any]:
    manifest_path = _project_dir(store, project_id) / "production_truth_manifest.json"
    refs = read_json_object(_project_dir(store, project_id) / MANGA_FIRST_WORKSPACE_REFS)
    payload = read_json_object(manifest_path)
    manifest = validate_manga_first_manifest(payload["manifest"])
    aggregate = EpisodeDomainAggregateStore(store.root).load(org_id=scope.org_id, project_id=scope.project_id)
    return build_manga_first_studio_workspace(
        manifest,
        aggregate=aggregate,
        aggregate_sha256=json_digest(aggregate.model_dump(mode="json")),
        manifest_artifact=dict(refs["manifest_artifact"]),
        checkpoint_artifact=dict(refs["checkpoint_artifact"]),
    )


def build_manga_first_studio_workspace(
    manifest: ProductionTruthManifest,
    *,
    aggregate: ProductionProjectAggregate,
    aggregate_sha256: str,
    manifest_artifact: dict[str, Any],
    checkpoint_artifact: dict[str, Any],
) -> dict[str, Any]:
    creator_projection = build_creator_authoring_projection(aggregate)
    episode = max(aggregate.episodes, key=lambda item: item.revision)
    episode_projection = build_episode_workspace_projection(aggregate, episode_ref=episode.as_ref())
    reference_gate = build_reference_approval_gate(aggregate)
    projection = _studio_projection_from_canonical(
        manifest,
        creator_projection=creator_projection,
        episode_projection=episode_projection,
        reference_gate=reference_gate,
    )
    return {
        "schema_version": "afs.manga_first_l4b.studio_workspace.v0.1",
        "project_id": manifest.project_id,
        "truth_authority": {
            "primary": "ProductionProjectAggregate",
            "aggregate_version": aggregate.aggregate_version,
            "aggregate_sha256": aggregate_sha256,
            "manifest_artifact": manifest_artifact,
            "checkpoint_artifact": checkpoint_artifact,
            "page_read_models": [
                "build_creator_authoring_projection",
                "build_episode_workspace_projection",
            ],
            "production_truth_manifest_role": "aggregate_backed_artifact_evidence",
            "second_fact_source_allowed": False,
        },
        "canonical_projections": {
            "creator_authoring": creator_projection,
            "episode_workspace": episode_projection,
        },
        "reference_approval_gate": reference_gate,
        "studio_projection": projection,
        "assembly_contract": manifest.assembly_contract,
        "provider_dispatch_count": 0,
        "non_claims": [
            "not_provider_smoke",
            "not_generated_media_qa",
            "not_human_acceptance",
            "not_business_validation",
            "not_owner_facing_release",
        ],
    }


def manga_first_gap_map() -> tuple[dict[str, Any], ...]:
    return (
        {
            "gap": "existing_episode_aggregate_migration",
            "status": "deferred",
            "next_minimal_path": "typed adapter that adds manga-first episode revisions against current aggregate CAS instead of replacing it",
        },
        {
            "gap": "production_database_scheduler",
            "status": "deferred",
            "next_minimal_path": "promote file-safe checkpoint semantics into Runtime production-control ledger/outbox lane",
        },
    )


def _existing_aggregate_gap_map(aggregate_store: EpisodeDomainAggregateStore, *, scope: TenantScope) -> tuple[dict[str, Any], ...]:
    try:
        aggregate_store.load(org_id=scope.org_id, project_id=scope.project_id)
    except AggregateNotFoundError:
        return ()
    return manga_first_gap_map()[:1]


def _project_dir(store: RuntimeStore, project_id: str) -> Path:
    return store.projects_dir / safe_id(project_id) / MANGA_FIRST_RUNTIME_DIR


def _workspace_refs(
    manifest: ProductionTruthManifest,
    aggregate_sha256: str,
    manifest_ref: dict[str, Any],
    checkpoint_ref: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "afs.manga_first_l4b.workspace_refs.v0.1",
        "project_id": manifest.project_id,
        "manifest_sha256": manifest.manifest_sha256,
        "aggregate_sha256": aggregate_sha256,
        "manifest_artifact": _public_artifact_ref(manifest_ref),
        "checkpoint_artifact": _public_artifact_ref(checkpoint_ref),
        "provider_dispatch_count": 0,
    }


def _public_artifact_ref(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_id": str(value["artifact_id"]),
        "artifact_type": str(value["artifact_type"]),
        "filename": str(value["filename"]),
        "role": str(value["role"]),
        "media_type": str(value["media_type"]),
    }


def _studio_projection_from_canonical(
    manifest: ProductionTruthManifest,
    *,
    creator_projection: dict[str, Any],
    episode_projection: dict[str, Any],
    reference_gate: dict[str, Any],
) -> dict[str, Any]:
    shots_by_ref = {
        _ref_key(item["ref"]): item
        for item in creator_projection.get("shots", [])
        if isinstance(item, dict) and isinstance(item.get("ref"), dict)
    }
    scenes_by_ref = {
        _ref_key(item["ref"]): item
        for item in creator_projection.get("scenes", [])
        if isinstance(item, dict) and isinstance(item.get("ref"), dict)
    }
    shot_rows = episode_projection.get("workspace", {}).get("shots", [])
    cursor = 0.0
    shot_status: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    timeline: list[dict[str, Any]] = []
    provider_ready = reference_gate.get("provider_ready") is True
    for row in shot_rows:
        if not isinstance(row, dict):
            continue
        ref = row.get("ref") if isinstance(row.get("ref"), dict) else {}
        shot_info = shots_by_ref.get(_ref_key(ref), {})
        scene_ref = shot_info.get("scene_ref") if isinstance(shot_info.get("scene_ref"), dict) else {}
        scene_info = scenes_by_ref.get(_ref_key(scene_ref), {})
        duration = float(row.get("duration_seconds") or shot_info.get("duration_seconds") or 0.0)
        shot_id = str(ref.get("entity_id") or "")
        selected = _selected_candidate_id(row)
        status = "awaiting_provider_authorization" if provider_ready else "awaiting_reference_approval"
        shot_status.append(
            {
                "shot_id": shot_id,
                "sequence": int(row.get("sequence") or 0),
                "scene_id": str(scene_ref.get("entity_id") or ""),
                "scene_title": str(scene_info.get("title") or ""),
                "title": str(shot_info.get("title") or shot_id),
                "summary": str(shot_info.get("summary") or ""),
                "status": status,
                "duration_seconds": duration,
                "candidate_count": len(row.get("candidates") or []),
                "selected_candidate_id": selected,
                "reference_approval_status": reference_gate["status"],
            }
        )
        for candidate in row.get("candidates") or []:
            if not isinstance(candidate, dict):
                continue
            candidate_ref = candidate.get("ref") if isinstance(candidate.get("ref"), dict) else {}
            candidate_rows.append(
                {
                    "candidate_id": str(candidate_ref.get("entity_id") or ""),
                    "shot_id": shot_id,
                    "status": str(candidate.get("status_label") or candidate.get("job_state") or "waiting_provider_authorization"),
                    "artifact_present": candidate.get("artifact_present") is True,
                    "fabricated_state": False,
                }
            )
        timeline.append(
            {
                "shot_id": shot_id,
                "start_seconds": f"{cursor:.3f}",
                "end_seconds": f"{cursor + duration:.3f}",
            }
        )
        cursor += duration
    return {
        "schema_version": "afs.manga_first_l4a.studio_projection.v0.1",
        "project": {
            "project_id": manifest.project_id,
            "title": str(creator_projection.get("project", {}).get("title") or manifest.story_bible["title"]),
            "workload": "manga_first",
            "status": "reference_approval_required" if not provider_ready else "provider_authorization_required",
        },
        "manifest_sha256": manifest.manifest_sha256,
        "truth_source": "canonical_episode_workspace_projection",
        "shot_status": shot_status,
        "candidates": candidate_rows,
        "timeline": timeline,
        "qa": {
            "technical_QA": "not_started",
            "visual_creative_QA": "blocked_before_audio_reference_pending" if not provider_ready else "not_started_before_provider",
            "p1_count": 0,
            "gate": "RESUMABLE_CANONICAL_PRODUCTION_AND_VISUAL_CREATIVE_QA_BEFORE_AUDIO",
        },
        "final_demo": {
            "status": "not_composed_for_new_manga_authority",
            "audio_status": "blocked_before_visual_qa",
            "duration_seconds": cursor,
        },
        "reference_approval_gate": reference_gate,
        "provider_dispatch_count": 0,
    }


def _selected_candidate_id(row: dict[str, Any]) -> str | None:
    selections = row.get("selections") if isinstance(row.get("selections"), list) else []
    for selection in selections:
        if not isinstance(selection, dict):
            continue
        candidate_ref = selection.get("candidate_ref") if isinstance(selection.get("candidate_ref"), dict) else {}
        candidate_id = str(candidate_ref.get("entity_id") or "")
        if candidate_id:
            return candidate_id
    return None


def _ref_key(ref: dict[str, Any] | EntityVersionRef) -> tuple[str, str, str]:
    if isinstance(ref, EntityVersionRef):
        return (ref.entity_type, ref.entity_id, ref.version_id)
    return (str(ref.get("entity_type") or ""), str(ref.get("entity_id") or ""), str(ref.get("version_id") or ""))


def _safe_manifest_artifact(manifest: ProductionTruthManifest, aggregate_sha256: str) -> dict[str, Any]:
    return {
        "artifact_type": "manga_first_l4b_production_truth_manifest",
        "schema_version": "afs.manga_first_l4b.production_truth_manifest_artifact.v0.1",
        "manifest": manifest.model_dump(mode="json"),
        "manifest_sha256": manifest.manifest_sha256,
        "aggregate_authority": {
            "store": "EpisodeDomainAggregateStore",
            "aggregate_sha256": aggregate_sha256,
            "second_fact_source_allowed": False,
        },
        "provider_dispatch_count": 0,
    }
