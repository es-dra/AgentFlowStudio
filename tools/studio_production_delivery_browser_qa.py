from __future__ import annotations

import argparse
import binascii
import hashlib
import json
import os
import struct
import sys
import zlib
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fastapi.testclient import TestClient

from apps.api.runtime_generated_image_assets import register_generated_image_asset
from apps.api.runtime_service import create_runtime_app
from apps.api.runtime_store import RuntimeStore
from agentflow_studio.production.representative_episode import validate_representative_episode


PROJECT_ID = "afs-rainlight-project"
NODE_ID = "image_delivery_qa_001"
JOB_ID = "job_delivery_qa_001"
RUN_ID = "production_delivery_qa_001"
QA_EMAIL = "delivery-qa@local.test"
QA_PASSWORD = "Local-QA-Delivery-2026!"
QA_INVITE = "delivery-qa-invite"


def prepare_provider_free_delivery_qa(runtime_root: Path) -> dict[str, object]:
    runtime_root = Path(runtime_root).resolve()
    runtime_root.mkdir(parents=True, exist_ok=True)
    with _qa_environment(), TestClient(create_runtime_app(runtime_root=runtime_root)) as client:
        registered = client.post(
            "/auth/register",
            json={
                "email": QA_EMAIL,
                "password": QA_PASSWORD,
                "display_name": "Delivery QA",
                "invite_code": QA_INVITE,
            },
        )
        registered.raise_for_status()
        token = registered.json()["session_token"]
        headers = {"Authorization": f"Bearer {token}"}
        created = client.post(
            "/projects",
            json={"project_id": PROJECT_ID, "goal": "Provider-free authenticated production delivery UI QA"},
            headers=headers,
        )
        created.raise_for_status()

        store = RuntimeStore(runtime_root)
        store.write_job({"job_id": JOB_ID, "project_id": PROJECT_ID, "action": "keyframe_generation", "status": "succeeded"})
        candidates, authorities = _write_candidates(store)
        subject_digest = hashlib.sha256(
            json.dumps(
                {
                    "schema_version": "afs_studio_production_subject.v0.1",
                    "project_id": PROJECT_ID,
                    "node_id": NODE_ID,
                    "parent_job_id": JOB_ID,
                    "candidates": [
                        {"candidate_id": item["candidate_id"], "canonical_digest": item["canonical_digest"]}
                        for item in candidates
                    ],
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        run_response = client.post(
            f"/projects/{PROJECT_ID}/production-runs",
            json={
                "schema_version": "afs_runtime_production_run.v0.1",
                "run_id": RUN_ID,
                "idempotency_key": "create-production-delivery-qa",
                "subject_digest": subject_digest,
                "candidates": candidates,
            },
            headers=headers,
        )
        run_response.raise_for_status()
        run = run_response.json()["production_run"]
        validated = validate_representative_episode(
            REPO_ROOT / "examples" / "representative_episode" / "episode_package.json"
        )
        binding_response = client.put(
            f"/projects/{PROJECT_ID}/production-runs/{RUN_ID}/representative-episode-binding",
            json=_episode_binding_payload(run, validated.package, validated.package_sha256),
            headers=headers,
        )
        binding_response.raise_for_status()
        run = binding_response.json()["production_run"]
        selected = candidates[1]
        decision_response = client.post(
            f"/projects/{PROJECT_ID}/production-runs/{RUN_ID}/creator-decisions",
            json={
                "schema_version": "afs_creator_decision.v0.1",
                "decision_id": "decision-delivery-qa-candidate-002",
                "idempotency_key": "decision-delivery-qa-candidate-002",
                "expected_checkpoint_version": run["checkpoint"]["version"],
                "subject_digest": subject_digest,
                "decision": "select",
                "candidate_id": selected["candidate_id"],
                "candidate_digest": selected["canonical_digest"],
                "parent_revision_id": None,
                "revision_intent": "Use the cooler composition as the exact delivery baseline.",
            },
            headers=headers,
        )
        decision_response.raise_for_status()
        selected_run = decision_response.json()["production_run"]
        saved = client.put(
            f"/projects/{PROJECT_ID}/studio-state",
            json={"state": _studio_state(authorities)},
            headers=headers,
        )
        saved.raise_for_status()
        persisted_candidates = (
            saved.json()["state"]["nodes"][NODE_ID]["params"]["candidatePreviewUrls"]
        )
        required_authority_fields = {
            "canonical_digest",
            "parent_job_id",
            "project_id",
            "reusable_asset_authority",
        }
        missing_authority_fields = sorted(
            {
                field
                for item in persisted_candidates
                for field in required_authority_fields
                if field not in item
            }
        )
        return {
            "runtime_root": str(runtime_root),
            "project_id": PROJECT_ID,
            "node_id": NODE_ID,
            "job_id": JOB_ID,
            "run_id": RUN_ID,
            "email": QA_EMAIL,
            "password": QA_PASSWORD,
            "selected_candidate_id": selected["candidate_id"],
            "selected_revision_id": selected_run["selected_revision"]["revision_id"],
            "candidate_count": len(candidates),
            "episode_version_id": run["representative_episode_binding"]["episode_version_id"],
            "canon_shot_count": len(run["representative_episode_binding"]["episode_canon"]["shots"]),
            "canon_checkpoint_version": run["checkpoint"]["version"],
            "provider_calls_started": False,
            "evidence_boundary": "provider-free deterministic UI/runtime verification only",
            "browser_preflight": {
                "ready": not missing_authority_fields,
                "missing_candidate_authority_fields": missing_authority_fields,
                "persisted_candidate_count": len(persisted_candidates),
                "authoritative_canon_ready": len(run["representative_episode_binding"]["episode_canon"]["shots"]) == 15,
                "stop_reason": (
                    "authenticated Studio state cannot restore selectable candidate authority"
                    if missing_authority_fields
                    else ""
                ),
            },
        }


def _episode_binding_payload(run: dict[str, object], package: dict[str, object], package_sha256: str) -> dict[str, object]:
    project = package["project"]
    characters = package["characters"]
    scenes = package["scenes"]
    shots = package["shots"]
    assets = package["asset_manifest"]
    audio = package["audio_plan"]
    crew_plan = package["domain_crew_execution_plan"]
    arbitration = crew_plan["creator_arbitration"]
    character_versions = {item["character_id"]: item["current_version_id"] for item in characters}
    scene_versions = {item["scene_id"]: item["current_version_id"] for item in scenes}
    assets_by_id = {item["asset_id"]: item for item in assets}

    def asset_ref(asset_id: str) -> dict[str, object]:
        item = assets_by_id[asset_id]
        return {
            "asset_id": item["asset_id"],
            "current_revision_id": item["current_revision_id"],
            "status": item["status"],
            "provider_needed": item["provider_needed"],
        }

    return {
        "schema_version": "afs_representative_episode_binding.v0.1",
        "idempotency_key": "bind-rainlight-delivery-qa-v1",
        "expected_checkpoint_version": run["checkpoint"]["version"],
        "expected_subject_digest": run["subject_digest"],
        "expected_package_sha256": None,
        "package_sha256": package_sha256,
        "package_project_id": project["project_id"],
        "episode_id": project["episode_id"],
        "episode_version_id": project["current_version_id"],
        "character_refs": [
            {"entity_id": item["character_id"], "current_approved_version_id": item["current_version_id"]}
            for item in characters
        ],
        "scene_refs": [
            {"entity_id": item["scene_id"], "current_approved_version_id": item["current_version_id"]}
            for item in scenes
        ],
        "shot_refs": [
            {"entity_id": item["shot_id"], "current_approved_version_id": item["current_version_id"]}
            for item in shots
        ],
        "asset_refs": [asset_ref(item["asset_id"]) for item in assets],
        "episode_canon": {
            "episode_title": project["title"],
            "episode_version_id": project["current_version_id"],
            "duration_seconds": project["duration_seconds"],
            "characters": [
                {
                    "entity_id": item["character_id"],
                    "current_approved_version_id": item["current_version_id"],
                    "name": item["name"],
                    "appearance": item["appearance"],
                    "continuity_constraints": item["continuity_constraints"],
                }
                for item in characters
            ],
            "scenes": [
                {
                    "entity_id": item["scene_id"],
                    "current_approved_version_id": item["current_version_id"],
                    "name": item["name"],
                    "description": item["description"],
                    "style_constraints": item["style_constraints"],
                }
                for item in scenes
            ],
            "shots": [
                {
                    "ordinal": index,
                    "entity_id": item["shot_id"],
                    "current_approved_version_id": item["current_version_id"],
                    "start_seconds": item["start_seconds"],
                    "end_seconds": item["end_seconds"],
                    "scene_ref": {
                        "entity_id": item["scene_id"],
                        "current_approved_version_id": scene_versions[item["scene_id"]],
                    },
                    "character_refs": [
                        {"entity_id": ref, "current_approved_version_id": character_versions[ref]}
                        for ref in item["character_refs"]
                    ],
                    "required_asset_ids": item["required_asset_ids"],
                    "visual_action": item["script"]["visual_action"],
                    "dialogue": item["script"]["dialogue"],
                    "camera": item["camera"],
                    "motion": item["motion"],
                    "continuity_note": item["continuity_note"],
                    "quality_target": item["quality_target"],
                }
                for index, item in enumerate(shots, start=1)
            ],
            "audio": {
                "coverage_shot_refs": audio["coverage_shot_refs"],
                "dialogue_asset_ref": asset_ref(audio["dialogue_asset_id"]),
                "music_asset_ref": asset_ref(audio["music_asset_id"]),
                "sfx_asset_ref": asset_ref(audio["sfx_asset_id"]),
                "master_asset_ref": asset_ref(audio["master_asset_id"]),
                "dialogue_direction": audio["dialogue_direction"],
                "music_direction": audio["music_direction"],
                "sfx_direction": audio["sfx_direction"],
                "mix_requirements": audio["mix_requirements"],
            },
        },
        "pending_media_count": sum(item["status"] == "missing" for item in assets),
        "creator_decision_ref": arbitration["creator_decision_ref"],
        "authoritative_affected_task_refs": arbitration["authoritative_affected_task_refs"],
        "downstream_reconfirmations": crew_plan["downstream_reconfirmations"],
    }


def _write_candidates(store: RuntimeStore) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    output_dir = store.run_dir(PROJECT_ID, JOB_ID) / "image_candidates"
    output_dir.mkdir(parents=True, exist_ok=True)
    candidates: list[dict[str, object]] = []
    authorities: list[dict[str, object]] = []
    for index, color in enumerate(((222, 104, 88), (55, 132, 188)), start=1):
        candidate_id = f"candidate_{index:03d}"
        path = output_dir / f"{candidate_id}.png"
        path.write_bytes(_solid_png(240, 320, color))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        registered = register_generated_image_asset(
            store,
            PROJECT_ID,
            source_node_id=NODE_ID,
            source_job_id=JOB_ID,
            source_candidate_id=candidate_id,
            image_path=path,
            source_candidate_digest=digest,
            source_candidate_status="succeeded",
        )
        candidates.append(
            {
                "candidate_id": candidate_id,
                "canonical_digest": digest,
                "parent_job_id": JOB_ID,
                "parent_candidate_id": None,
                "parent_revision_id": None,
                "shot_id": "shot_delivery_qa_001",
                "safe_artifact_refs": [],
            }
        )
        authorities.append(registered["asset"])
    return candidates, authorities


def _studio_state(authorities: list[dict[str, object]]) -> dict[str, object]:
    candidates = []
    for authority in authorities:
        candidate_id = str(authority["source_candidate_id"])
        candidates.append(
            {
                "candidate_id": candidate_id,
                "canonical_digest": authority["source_candidate_digest"],
                "parent_job_id": JOB_ID,
                "project_id": PROJECT_ID,
                "preview_url": f"/projects/{PROJECT_ID}/keyframe-generations/{JOB_ID}/candidates/{candidate_id}/preview",
                "status": "succeeded",
                "aspect_ratio": "3:4",
                "reusable_asset_authority": authority,
            }
        )
    return {
        "meta": {
            "projectId": PROJECT_ID,
            "projectName": "Production Delivery QA",
            "canvasName": "Authenticated delivery gate",
            "seq": 1,
            "updated_at": "",
        },
        "viewport": {"x": 80, "y": 40, "scale": 0.9},
        "nodes": {
            NODE_ID: {
                "id": NODE_ID,
                "type": "image",
                "title": "Episode shot · delivery comparison",
                "x": 420,
                "y": 180,
                "w": 380,
                "h": 640,
                "prompt": "Provider-free deterministic delivery comparison.",
                "content": "",
                "status": "complete",
                "result": "Two deterministic local candidates are ready for creator arbitration and exact delivery review.",
                "previewUrl": "",
                "params": {
                    "model": "provider-free-deterministic-fixture",
                    "spec": {"ratio": "3:4"},
                    "previewAspectRatio": "3:4",
                    "lastKeyframeJobId": JOB_ID,
                    "lastKeyframeCompletedJobId": JOB_ID,
                    "candidatePreviewUrls": candidates,
                    "uploads": [],
                },
            }
        },
        "edges": {},
        "groups": {},
        "assets": [],
        "order": [NODE_ID],
    }


def _solid_png(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    signature = b"\x89PNG\r\n\x1a\n"
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    row = b"\x00" + bytes(rgb) * width
    payload = zlib.compress(row * height, level=9)
    return signature + _png_chunk(b"IHDR", header) + _png_chunk(b"IDAT", payload) + _png_chunk(b"IEND", b"")


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    checksum = binascii.crc32(kind + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", checksum)


@contextmanager
def _qa_environment() -> Iterator[None]:
    values = {
        "AFS_AUTH_ENABLED": "true",
        "AFS_INVITE_CODES": QA_INVITE,
        "AFS_ALLOW_REMOTE_LLM": "false",
        "AFS_ALLOW_REMOTE_IMAGE": "false",
        "AFS_ALLOW_REMOTE_VISION": "false",
        "AFS_ALLOW_REMOTE_VIDEO": "false",
        "AFS_ALLOW_REMOTE_ASR": "false",
    }
    before = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, value in before.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare provider-free authenticated Studio production-delivery browser QA.")
    parser.add_argument("--runtime-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare_provider_free_delivery_qa(args.runtime_root), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
