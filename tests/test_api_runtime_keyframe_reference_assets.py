from __future__ import annotations

import base64
import json
from types import SimpleNamespace
from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.runtime_keyframes import _reference_images
from apps.api.runtime_image_assets import resolve_reference_images
from apps.api.runtime_models import KeyframeGenerationRequest
from apps.api.runtime_service import create_runtime_app
from apps.api.runtime_store import RuntimeStore


PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)
PNG_B64 = base64.b64encode(PNG_BYTES).decode("ascii")


def test_reference_image_resolution_respects_zero_provider_slots(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    upload = client.post(
        "/projects/proj_zero_slots/image-assets",
        json={
            "node_id": "asset-card-draft-node",
            "filename": "candidate.png",
            "mime_type": "image/png",
            "data_base64": PNG_B64,
            "role": "character_reference",
            "generated_at": "2026-06-23T10:00:00+08:00",
        },
    )
    assert upload.status_code == 200
    asset_id = upload.json()["asset"]["asset_id"]

    assert resolve_reference_images(RuntimeStore(tmp_path), "proj_zero_slots", [asset_id], limit=0) == []


def test_uploaded_image_asset_can_drive_connected_keyframe_reference(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    captured: dict[str, object] = {}

    def fake_dispatch(capability, service_id, request):
        captured["subject_reference_image_path"] = request.subject_reference_image_path
        captured["prompt"] = request.prompt
        output_dir = Path(request.output_dir)
        image_dir = output_dir / "image_candidates"
        image_dir.mkdir(parents=True, exist_ok=True)
        image_path = image_dir / "candidate_001.jpg"
        image_path.write_bytes(b"\xff\xd8fake-runtime-jpeg")
        return {
            "outputs": [
                {
                    "candidate_id": "candidate_001",
                    "image_path": "image_candidates/candidate_001.jpg",
                    "byte_count": image_path.stat().st_size,
                    "sha256": "fake-sha256",
                    "width": 720,
                    "height": 1280,
                    "aspect_ratio": "720:1280",
                    "provider_url_persisted": False,
                }
            ],
            "input_image": {
                "path_persisted": False,
                "byte_count": len(PNG_BYTES),
                "sha256": "sha256:fake-ref",
                "mime_type": "image/png",
            },
        }

    monkeypatch.setattr("apps.api.runtime_keyframes.load_provider_registry", lambda: _FakeRegistry(fake_dispatch))
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    upload = client.post(
        "/projects/proj_connected_refs/image-assets",
        json={
            "node_id": "view-front-node",
            "filename": "front.png",
            "mime_type": "image/png",
            "data_base64": PNG_B64,
            "role": "character_reference",
            "generated_at": "2026-06-12T10:25:00+08:00",
        },
    )
    assert upload.status_code == 200
    asset = upload.json()["asset"]
    preview = client.get(asset["preview_url"])
    assert preview.status_code == 200
    assert preview.content == PNG_BYTES

    result = client.post(
        "/projects/proj_connected_refs/keyframe-generations",
        json={
            "node_id": "image-node-with-upstream-ref",
            "prompt_text": "Use the connected three-view reference to create a rain rooftop keyframe.",
            "optimized_prompt": "Use the connected reference image to preserve identity.",
            "target_platform": "short_video",
            "style": "cinematic",
            "aspect_ratio": "9:16",
            "candidate_count": 1,
            "asset_refs": [asset["asset_id"]],
            "seed": 120612,
            "generated_at": "2026-06-12T10:26:00+08:00",
        },
    )

    assert result.status_code == 200
    payload = result.json()
    plan = client.get(f"/artifacts/{payload['artifacts']['keyframe_request_plan']['artifact_id']}").json()["payload"]
    serialized = json.dumps({"payload": payload, "plan": plan}, ensure_ascii=False).lower()

    subject_path = Path(str(captured["subject_reference_image_path"]))
    assert subject_path.exists()
    assert subject_path.name == "source.png"
    assert plan["reference_image_count"] == 1
    assert plan["subject_reference_asset_id"] == asset["asset_id"]
    assert plan["reference_images"][0]["asset_id"] == asset["asset_id"]
    assert "只保留与用户目标不冲突的相关主体特征" in str(captured["prompt"])
    assert "不要把无关背景、服装、图表、界面文字或旧失败风格带入结果" in str(captured["prompt"])
    assert "Preserve the reference face, clothing, silhouette" not in str(captured["prompt"])
    assert "data_base64" not in serialized
    assert "c:\\" not in serialized
    assert "d:\\" not in serialized


def test_uploaded_image_asset_survives_context_bundle_reference_fallback(tmp_path, monkeypatch) -> None:
    store = RuntimeStore(tmp_path)
    project_id = "proj_context_ref_fallback"
    asset_id = "img_uploaded_ref"
    asset_dir = tmp_path / "projects" / project_id / "image_assets" / asset_id
    asset_dir.mkdir(parents=True)
    (asset_dir / "source.png").write_bytes(PNG_BYTES)
    (asset_dir / "image_asset.json").write_text(
        json.dumps(
            {
                "artifact_type": "agentflow_uploaded_image_asset",
                "schema_version": "0.1.0",
                "project_id": project_id,
                "asset_id": asset_id,
                "source_node_id": "node_2",
                "role": "reference_image",
                "filename": "front.png",
                "mime_type": "image/png",
                "file_suffix": ".png",
                "byte_count": len(PNG_BYTES),
                "sha256": "fake-sha256",
                "width": 1,
                "height": 1,
                "aspect_ratio": "1:1",
                "preview_url": f"/projects/{project_id}/image-assets/{asset_id}/preview",
            }
        ),
        encoding="utf-8",
    )
    request = KeyframeGenerationRequest(
        node_id="node_2",
        prompt_text="Move the uploaded character to a desert while preserving identity.",
        optimized_prompt="Move the uploaded character to a desert while preserving identity.",
        asset_refs=[asset_id],
        context_subgraph={
            "target_node_id": "node_2",
            "nodes": [{"id": "node_2", "type": "image", "image_asset_refs": [asset_id]}],
            "edges": [],
        },
        generated_at="2026-06-12T10:26:00+08:00",
    )

    refs = _reference_images(
        store,
        project_id,
        request,
        {"reference_image_channel": []},
        limit=1,
    )

    assert len(refs) == 1
    assert refs[0]["path"] == asset_dir / "source.png"
    assert refs[0]["public"]["asset_id"] == asset_id


def test_generated_keyframe_asset_can_drive_next_connected_reference(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    captured: dict[str, object] = {"subject_paths": []}

    def fake_dispatch(capability, service_id, request):
        captured["subject_paths"].append(request.subject_reference_image_path)
        output_dir = Path(request.output_dir)
        image_dir = output_dir / "image_candidates"
        image_dir.mkdir(parents=True, exist_ok=True)
        image_path = image_dir / "candidate_001.png"
        image_path.write_bytes(PNG_BYTES)
        return {
            "outputs": [
                {
                    "candidate_id": "candidate_001",
                    "image_path": "image_candidates/candidate_001.png",
                    "byte_count": image_path.stat().st_size,
                    "sha256": "fake-sha256",
                    "width": 1,
                    "height": 1,
                    "aspect_ratio": "1:1",
                    "provider_url_persisted": False,
                }
            ]
        }

    monkeypatch.setattr("apps.api.runtime_keyframes.load_provider_registry", lambda: _FakeRegistry(fake_dispatch))
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    first = client.post(
        "/projects/proj_generated_refs/keyframe-generations",
        json={
            "node_id": "character-reference-node",
            "prompt_text": "Create a reusable character reference keyframe.",
            "optimized_prompt": "A front-facing controlled character reference image.",
            "target_platform": "short_video",
            "style": "cinematic",
            "aspect_ratio": "9:16",
            "candidate_count": 1,
            "generated_at": "2026-06-12T10:26:00+08:00",
        },
    )
    assert first.status_code == 200
    generated_asset = first.json()["reusable_image_assets"][0]
    assert generated_asset["source_candidate_id"] == "candidate_001"

    second = client.post(
        "/projects/proj_generated_refs/keyframe-generations",
        json={
            "node_id": "downstream-rain-rooftop-node",
            "prompt_text": "Use the connected character reference for a rain rooftop keyframe.",
            "optimized_prompt": "Preserve the connected reference character while changing scene to a rain rooftop.",
            "target_platform": "short_video",
            "style": "cinematic",
            "aspect_ratio": "9:16",
            "candidate_count": 1,
            "asset_refs": [generated_asset["asset_id"]],
            "generated_at": "2026-06-12T10:27:00+08:00",
        },
    )
    assert second.status_code == 200
    payload = second.json()
    plan = client.get(f"/artifacts/{payload['artifacts']['keyframe_request_plan']['artifact_id']}").json()["payload"]
    serialized = json.dumps({"payload": payload, "plan": plan}, ensure_ascii=False).lower()

    assert captured["subject_paths"][0] is None
    subject_path = Path(str(captured["subject_paths"][1]))
    assert subject_path.exists()
    assert subject_path.name == "source.png"
    assert plan["reference_image_count"] == 1
    assert plan["subject_reference_asset_id"] == generated_asset["asset_id"]
    assert plan["reference_images"][0]["asset_id"] == generated_asset["asset_id"]
    assert "image_candidates/candidate_001.png" not in serialized
    assert "c:\\" not in serialized
    assert "d:\\" not in serialized


def test_asset_card_revision_uses_ordered_reference_images_and_partial_revision_guard(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    captured: dict[str, object] = {}

    def fake_dispatch(capability, service_id, request):
        captured["reference_paths"] = list(request.reference_image_paths)
        captured["subject_reference_image_path"] = request.subject_reference_image_path
        captured["edit_source_image_path"] = getattr(request, "edit_source_image_path", None)
        captured["edit_reference_image_paths"] = list(getattr(request, "edit_reference_image_paths", ()))
        captured["image_operation"] = getattr(request, "image_operation", "generate")
        captured["image_input_fidelity"] = getattr(request, "image_input_fidelity", None)
        captured["prompt"] = request.prompt
        output_dir = Path(request.output_dir)
        image_dir = output_dir / "image_candidates"
        image_dir.mkdir(parents=True, exist_ok=True)
        image_path = image_dir / "candidate_001.png"
        image_path.write_bytes(PNG_BYTES)
        return {
            "outputs": [
                {
                    "candidate_id": "candidate_001",
                    "image_path": "image_candidates/candidate_001.png",
                    "byte_count": image_path.stat().st_size,
                    "sha256": "fake-sha256",
                    "width": 1,
                    "height": 1,
                    "aspect_ratio": "1:1",
                    "provider_url_persisted": False,
                }
            ]
        }

    monkeypatch.setattr(
        "apps.api.runtime_keyframes.load_provider_registry",
        lambda: _FakeRegistry(fake_dispatch, _FakeDescriptor(reference_image_slots=2)),
    )
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_asset_card_revision_refs"
    first_ref = _upload_reference(client, project_id, "old-candidate.png")
    second_ref = _upload_reference(client, project_id, "detail.png")

    result = client.post(
        f"/projects/{project_id}/keyframe-generations",
        json={
            "node_id": "asset-card-node",
            "prompt_text": "Regenerate the robot asset reference sheet after a card edit.",
            "optimized_prompt": "Regenerate the robot asset reference sheet after a card edit.",
            "target_platform": "short_video",
            "style": "cinematic",
            "aspect_ratio": "16:9",
            "candidate_count": 1,
            "asset_refs": [first_ref, second_ref],
            "node_parameters": {
                "node_role": "asset_card_draft",
                "asset_card_revision": {
                    "mode": "image_guided_partial_revision",
                    "reference_assets": [
                        {"asset_id": first_ref, "role": "identity_layout_anchor", "priority": 1},
                        {"asset_id": second_ref, "role": "secondary_identity_reference", "priority": 2},
                    ],
                    "changed_fields": [
                        {"field": "appearance", "label": "外形辨识", "from": "金属机身", "to": "毛绒机身"},
                        {"field": "wardrobe", "label": "服装/外观", "from": "无传统服装", "to": "穿着传统服装"},
                    ],
                    "preserve_locks": ["保持体态比例", "保持正侧背视图一致"],
                },
            },
            "generated_at": "2026-06-23T13:20:00+08:00",
        },
    )

    assert result.status_code == 200
    payload = result.json()
    plan = client.get(f"/artifacts/{payload['artifacts']['keyframe_request_plan']['artifact_id']}").json()["payload"]
    assert [item["asset_id"] for item in plan["reference_images"]] == [first_ref, second_ref]
    assert Path(str(captured["reference_paths"][0])).name == "source.png"
    assert captured["subject_reference_image_path"] == captured["reference_paths"][0]
    assert captured["edit_source_image_path"] == captured["reference_paths"][0]
    assert captured["edit_reference_image_paths"] == captured["reference_paths"]
    assert captured["image_operation"] == "edit"
    assert captured["image_input_fidelity"] == "high"
    assert plan["image_operation"] == "edit"
    assert plan["edit_source_asset_id"] == first_ref
    assert "Asset-card revision mode" in str(captured["prompt"])
    assert "primary visual source of truth" in str(captured["prompt"])
    assert "The changed fields are the only editable delta" in str(captured["prompt"])
    assert "参考图只作为本次显式连线的视觉参考" not in str(captured["prompt"])
    assert "参考图只补充相关视觉线索" not in str(captured["prompt"])
    assert "Apply only the changed asset-card details" in str(captured["prompt"])
    assert "Revision strength: conservative low-change pass" in str(captured["prompt"])
    assert "Wardrobe edit scope: add clothing as an outer garment layer only" in str(captured["prompt"])
    assert "Plush/fabric material must read as a surface covering on the same existing robot frame" in str(captured["prompt"])
    assert "Do not turn the subject into a toy, chibi, mascot" in str(captured["prompt"])
    assert "外形辨识: 毛绒机身" in str(captured["prompt"])
    assert "服装/外观: 穿着传统服装" in str(captured["prompt"])


def test_image_relay_openai_route_uses_edit_for_reference_asset_even_with_legacy_zero_slots(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    captured: dict[str, object] = {}

    def fake_dispatch(capability, service_id, request):
        captured["service_id"] = service_id
        captured["reference_paths"] = list(request.reference_image_paths)
        captured["edit_source_image_path"] = getattr(request, "edit_source_image_path", None)
        captured["edit_reference_image_paths"] = list(getattr(request, "edit_reference_image_paths", ()))
        captured["image_operation"] = getattr(request, "image_operation", "generate")
        output_dir = Path(request.output_dir)
        image_dir = output_dir / "image_candidates"
        image_dir.mkdir(parents=True, exist_ok=True)
        image_path = image_dir / "candidate_001.png"
        image_path.write_bytes(PNG_BYTES)
        return {
            "outputs": [
                {
                    "candidate_id": "candidate_001",
                    "image_path": "image_candidates/candidate_001.png",
                    "byte_count": image_path.stat().st_size,
                    "sha256": "fake-sha256",
                    "width": 1,
                    "height": 1,
                    "aspect_ratio": "1:1",
                    "provider_url_persisted": False,
                }
            ]
        }

    monkeypatch.setattr(
        "apps.api.runtime_keyframes.load_provider_registry",
        lambda: _FakeRegistry(
            fake_dispatch,
            _FakeDescriptor(reference_image_slots=0),
            services={"image_relay": {"request_format": "openai_images"}},
        ),
    )
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_image_relay_openai_refs"
    asset_id = _upload_reference(client, project_id, "library-reference.png")

    result = client.post(
        f"/projects/{project_id}/keyframe-generations",
        json={
            "node_id": "image-node-with-library-ref",
            "prompt_text": "Use the selected library reference for a new keyframe.",
            "optimized_prompt": "Use the selected library reference for a new keyframe.",
            "target_platform": "short_video",
            "style": "cinematic",
            "aspect_ratio": "9:16",
            "candidate_count": 1,
            "provider_service_id": "image_relay",
            "asset_refs": [asset_id],
            "generated_at": "2026-06-26T10:26:00+08:00",
        },
    )

    assert result.status_code == 200
    payload = result.json()
    plan = client.get(f"/artifacts/{payload['artifacts']['keyframe_request_plan']['artifact_id']}").json()["payload"]
    assert captured["service_id"] == "image_relay"
    assert len(captured["reference_paths"]) == 1
    assert captured["edit_source_image_path"] == captured["reference_paths"][0]
    assert captured["edit_reference_image_paths"] == captured["reference_paths"]
    assert captured["image_operation"] == "edit"
    assert plan["provider"] == "image_relay"
    assert plan["reference_image_count"] == 1
    assert plan["image_operation"] == "edit"


def test_tiny_keyframe_reference_blocks_before_remote_provider_dispatch(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")

    class GuardedRegistry:
        def descriptor(self, service_id: str):
            return _FakeDescriptor(min_reference_image_edge_px=256)

        def dispatch(self, capability: str, service_id: str, request):
            raise AssertionError("tiny reference image should be blocked before provider dispatch")

    monkeypatch.setattr("apps.api.runtime_keyframes.load_provider_registry", lambda: GuardedRegistry())
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    upload = client.post(
        "/projects/proj_tiny_ref_guard/image-assets",
        json={
            "node_id": "tiny-ref-node",
            "filename": "tiny.png",
            "mime_type": "image/png",
            "data_base64": PNG_B64,
            "role": "character_reference",
            "generated_at": "2026-06-12T10:25:00+08:00",
        },
    )
    assert upload.status_code == 200
    asset_id = upload.json()["asset"]["asset_id"]

    result = client.post(
        "/projects/proj_tiny_ref_guard/keyframe-generations",
        json={
            "node_id": "image-node-with-tiny-ref",
            "prompt_text": "Use the tiny reference image for a portrait.",
            "optimized_prompt": "Use the tiny reference image for a portrait.",
            "target_platform": "short_video",
            "style": "cinematic",
            "aspect_ratio": "9:16",
            "candidate_count": 1,
            "asset_refs": [asset_id],
            "generated_at": "2026-06-12T10:26:00+08:00",
        },
    )

    assert result.status_code == 200
    payload = result.json()
    assert payload["job"]["status"] == "blocked"
    assert payload["provider_calls_started"] is False
    assert payload["safe_manifest"]["provider_calls_started"] is False
    assert payload["safe_manifest"]["blocks"][0]["block_id"] == "remote_image_reference_image_too_small"


class _FakeDescriptor:
    required_gate = "AFS_ALLOW_REMOTE_IMAGE"

    def __init__(self, min_reference_image_edge_px: int = 0, reference_image_slots: int = 1) -> None:
        self.min_reference_image_edge_px = min_reference_image_edge_px
        self.reference_image_slots = reference_image_slots
        self.prompt_char_limit = 1500


class _FakeRegistry:
    def __init__(self, dispatch, descriptor: _FakeDescriptor | None = None, services: dict | None = None) -> None:
        self._dispatch = dispatch
        self._descriptor = descriptor or _FakeDescriptor()
        self.store = SimpleNamespace(services=services or {})

    def descriptor(self, service_id: str) -> _FakeDescriptor:
        return self._descriptor

    def dispatch(self, capability: str, service_id: str, request):
        return self._dispatch(capability, service_id, request)


def _upload_reference(client: TestClient, project_id: str, filename: str) -> str:
    upload = client.post(
        f"/projects/{project_id}/image-assets",
        json={
            "node_id": "asset-card-node",
            "filename": filename,
            "mime_type": "image/png",
            "data_base64": PNG_B64,
            "role": "character_reference",
            "generated_at": "2026-06-23T13:19:00+08:00",
        },
    )
    assert upload.status_code == 200
    return upload.json()["asset"]["asset_id"]


def test_keyframe_request_plan_includes_structured_keyframe_plan(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_keyframe_plan"
    client.post("/projects", json={"project_id": project_id, "goal": "Keyframe plan"})

    response = client.post(
        f"/projects/{project_id}/keyframe-generations",
        json={
            "node_id": "keyframe_robot_rooftop",
            "prompt_text": "A future robot watches stars on a rural rooftop platform.",
            "optimized_prompt": "Medium keyframe of a future robot on a rooftop under stars; no chairs or eaves.",
            "target_platform": "short_video",
            "style": "cinematic",
            "aspect_ratio": "9:16",
            "candidate_count": 1,
            "generated_at": "2026-06-27T10:10:00+08:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    plan = client.get(f"/artifacts/{payload['artifacts']['keyframe_request_plan']['artifact_id']}").json()["payload"]
    keyframe_plan = plan["keyframe_plan"]

    assert keyframe_plan["frame_role"] == "story_continuity_keyframe"
    assert "unrequested chair" in keyframe_plan["forbidden_changes"]
    assert "unrequested eaves" in keyframe_plan["forbidden_changes"]
    assert "rooftop platform geometry" in keyframe_plan["scene_locks"]
    assert keyframe_plan["candidate_assets_are_editable"] is True


def test_keyframe_plan_uses_context_subgraph_asset_graph(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_keyframe_asset_graph"
    client.post("/projects", json={"project_id": project_id, "goal": "Keyframe asset graph"})
    asset_graph = {
        "artifact_type": "agentflow_asset_graph",
        "asset_count": 2,
        "assets": [
            {
                "graph_asset_id": "graph:character:future_robot",
                "asset_id": "asset_robot",
                "asset_type": "character",
                "label": "future robot",
                "role": "story_character",
                "status": "candidate",
                "confidence": 0.91,
                "continuity_locks": ["plush robot head shell", "white mechanical body proportions"],
                "negative_locks": ["do not replace plush shell with metal skull"],
            },
            {
                "graph_asset_id": "graph:scene:rooftop_platform",
                "asset_id": "asset_rooftop",
                "asset_type": "scene",
                "label": "rural rooftop platform",
                "role": "scene_anchor",
                "status": "candidate",
                "confidence": 0.87,
                "continuity_locks": ["flat rural rooftop boundary", "open sky relationship"],
                "negative_locks": ["do not add unapproved eaves"],
            },
        ],
        "unsupported_additions": [{"shot_id": "shot_01", "addition": "chair"}],
    }

    response = client.post(
        f"/projects/{project_id}/keyframe-generations",
        json={
            "node_id": "keyframe_robot_rooftop_graph",
            "prompt_text": "A future robot watches stars on a rural rooftop platform.",
            "optimized_prompt": "Medium keyframe of a future robot on a rooftop under stars; no chairs or eaves.",
            "target_platform": "short_video",
            "style": "cinematic",
            "aspect_ratio": "9:16",
            "candidate_count": 1,
            "context_subgraph": {
                "target_node_id": "keyframe_robot_rooftop_graph",
                "nodes": [
                    {
                        "id": "storyboard_01",
                        "type": "storyboard",
                        "node_parameters": {"asset_graph": asset_graph},
                    }
                ],
                "edges": [],
            },
            "generated_at": "2026-06-28T10:10:00+08:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    plan = client.get(f"/artifacts/{payload['artifacts']['keyframe_request_plan']['artifact_id']}").json()["payload"]
    keyframe_plan = plan["keyframe_plan"]
    graph_context = keyframe_plan["asset_graph_context"]

    assert graph_context["asset_count"] == 2
    assert "graph:character:future_robot" in graph_context["graph_asset_ids"]
    assert any(item.get("graph_asset_id") == "graph:scene:rooftop_platform" for item in keyframe_plan["asset_locks"])
    assert "plush robot head shell" in str(keyframe_plan["asset_locks"])
    assert "flat rural rooftop boundary" in keyframe_plan["scene_locks"]
    assert "do not add unapproved eaves" in keyframe_plan["forbidden_changes"]


def test_keyframe_plan_includes_professional_reference(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_keyframe_prof_ref"
    client.post("/projects", json={"project_id": project_id, "goal": "Keyframe professional reference"})

    response = client.post(
        f"/projects/{project_id}/keyframe-generations",
        json={
            "node_id": "keyframe_prof_ref",
            "prompt_text": "A future robot watches stars on a rural rooftop platform.",
            "optimized_prompt": "Medium keyframe of a future robot on a rooftop under stars; no chairs or eaves.",
            "target_platform": "short_video",
            "style": "cinematic",
            "aspect_ratio": "9:16",
            "candidate_count": 1,
            "generated_at": "2026-06-27T10:25:00+08:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    plan = client.get(f"/artifacts/{payload['artifacts']['keyframe_request_plan']['artifact_id']}").json()["payload"]
    reference = plan["keyframe_plan"]["professional_reference"]
    scenario = plan["keyframe_plan"]["director_scenario"]

    assert {"night", "rooftop", "single_frame"} <= set(reference["tags"])
    assert "moderate-to-deep" in reference["depth_of_field"]["decision"]
    assert "unapproved chair or stool" in reference["scene_continuity"]["avoid"]
    assert reference["writes_company_kb"] is False
    assert scenario["primary_scenario"] == "general_short_video"
    assert scenario["writes_company_kb"] is False
