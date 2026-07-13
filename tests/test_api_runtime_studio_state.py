from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.runtime_errors import response_contains_unsafe_marker
from apps.api.runtime_service import create_runtime_app
from apps.api.runtime_studio_state import sanitize_studio_state


def test_studio_state_can_save_and_restore_safe_canvas(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "studio-state-demo"
    client.post("/projects", json={"project_id": project_id, "goal": "Studio state test"})
    state = {
        "meta": {"projectName": "AFS Studio", "canvasName": "画布 1", "seq": 9},
        "viewport": {"x": -120, "y": 80, "scale": 0.82},
        "nodes": {
            "director_1": {
                "id": "director_1",
                "type": "director",
                "title": "二维导演台",
                "x": 10,
                "y": 20,
                "prompt": "",
                "params": {
                    "directorSetup": {
                        "view": "top_down_2d",
                        "cameras": [{"name": "A Cam", "fov": 45}],
                        "subjects": [{"name": "男孩", "x": 44, "y": 52}],
                        "lights": [{"name": "Key Light", "intensity": 72}],
                    },
                    "uploads": [{
                        "asset_id": "img_safe_reference_001",
                        "role": "generated_keyframe_reference",
                        "filename": "candidate_001.png",
                        "mime_type": "image/png",
                        "byte_count": 68,
                        "sha256": "abc123",
                        "width": 1,
                        "height": 1,
                        "aspect_ratio": "1:1",
                        "preview_url": "/projects/studio-state-demo/image-assets/img_safe_reference_001/preview",
                    }],
                    "previewAspectRatio": "1:1",
                },
            },
            "image_2": {"id": "image_2", "type": "image", "title": "关键帧", "x": 360, "y": 20, "prompt": "昏暗房间"},
        },
        "edges": {"edge_3": {"id": "edge_3", "from": "director_1", "to": "image_2", "relation_type": "director"}},
        "order": ["director_1", "image_2"],
        "assets": [
            {
                "id": "asset_1",
                "kind": "director_setup",
                "title": "夜间卧室布光",
                "safe_summary": "1 个机位 / 1 个主体 / 3 盏灯",
                "thumbnail_ref": "director-board",
                "source_node_id": "director_1",
            }
        ],
    }

    saved = client.put(f"/projects/{project_id}/studio-state", json={"state": state})
    assert saved.status_code == 200
    payload = saved.json()
    assert payload["saved"] is True
    assert payload["state_version"]
    assert payload["saved_at"]
    assert payload["state"]["edges"]["edge_3"]["relation_type"] == "director"
    assert payload["state"]["assets"][0]["source_node_id"] == "director_1"

    restored = client.get(f"/projects/{project_id}/studio-state")
    assert restored.status_code == 200
    assert restored.json()["source"] == "runtime"
    assert restored.json()["state_version"] == payload["state_version"]
    assert restored.json()["saved_at"] == payload["saved_at"]
    restored_params = restored.json()["state"]["nodes"]["director_1"]["params"]
    assert restored_params["directorSetup"]["view"] == "top_down_2d"
    assert restored_params["uploads"][0]["asset_id"] == "img_safe_reference_001"
    assert restored_params["previewAspectRatio"] == "1:1"


def test_studio_state_uses_expected_version_to_prevent_stale_overwrite(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "studio-version-conflict"
    client.post("/projects", json={"project_id": project_id, "goal": "Studio version conflict"})

    first = client.put(
        f"/projects/{project_id}/studio-state",
        json={"state": {"meta": {"projectName": "First"}, "nodes": {"text_1": {"type": "text"}}}},
    )
    assert first.status_code == 200
    version = first.json()["state_version"]

    second = client.put(
        f"/projects/{project_id}/studio-state",
        json={
            "expected_version": version,
            "state": {"meta": {"projectName": "Second"}, "nodes": {"text_2": {"type": "text"}}},
        },
    )
    assert second.status_code == 200

    stale = client.put(
        f"/projects/{project_id}/studio-state",
        json={
            "expected_version": version,
            "state": {"meta": {"projectName": "Stale"}, "nodes": {"text_3": {"type": "text"}}},
        },
    )
    assert stale.status_code == 409
    detail = stale.json()["detail"]
    assert detail["error"] == "studio_state_conflict"
    assert detail["detail_code"] == "invalid_request"
    assert detail["status"] == "failed"
    assert detail["retryable"] is True
    assert detail["project_id"] == project_id
    assert detail["action"] == "studio_state"
    assert detail["stage"] == "state_conflict"
    assert detail["details"]["raw_detail"] == "studio state version conflict"
    assert response_contains_unsafe_marker(stale.json()) is False


def test_studio_state_preserves_generation_progress_and_safe_candidates(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AFS_AUTH_ALLOW_OPEN_SIGNUP", "true")
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "studio-progress-demo"
    candidate_digest = "a" * 64
    registered = client.post(
        "/auth/register",
        json={
            "email": "studio-projection@example.com",
            "password": "strong-password-123",
            "display_name": "Studio Projection",
        },
    )
    assert registered.status_code == 200
    headers = {"Authorization": f"Bearer {registered.json()['session_token']}"}
    client.post(
        "/projects",
        json={"project_id": project_id, "goal": "Studio progress state test"},
        headers=headers,
    )
    candidate_url = (
        "/projects/studio-progress-demo/keyframe-generations/"
        "job_keyframe_001/candidates/candidate_001/preview"
    )
    state = {
        "nodes": {
            "image_1": {
                "id": "image_1",
                "type": "image",
                "title": "生成中",
                "status": "generating",
                "params": {
                    "progressPercent": 42,
                    "jobProgress": {
                        "percent": 42,
                        "label": "图片生成进行中",
                        "hint": "任务正在处理",
                        "status": "running",
                        "terminal": False,
                    },
                    "terminalProgress": {"percent": 100, "label": "图片生成已完成", "terminal": True},
                    "candidatePreviewUrls": [
                        {
                            "url": candidate_url,
                            "candidate_id": "candidate_001",
                            "canonical_digest": candidate_digest,
                            "parent_job_id": "job_keyframe_001",
                            "project_id": project_id,
                            "reusable_asset_authority": {
                                "schema_version": "afs_studio_reusable_asset_authority.v0.1",
                                "asset_id": "asset_safe_001",
                                "role": "generated_keyframe_reference",
                                "source_kind": "keyframe_candidate",
                                "status": "succeeded",
                                "source_job_id": "job_keyframe_001",
                                "source_candidate_id": "candidate_001",
                                "source_candidate_digest": candidate_digest,
                                "sha256": candidate_digest,
                                "internal_note": "must not cross the projection boundary",
                            },
                            "width": 1536,
                            "height": 864,
                            "aspect_ratio": "16:9",
                            "artifact_id": "artifact_safe_001",
                        }
                    ],
                },
            }
        },
        "order": ["image_1"],
    }

    saved = client.put(f"/projects/{project_id}/studio-state", json={"state": state}, headers=headers)
    assert saved.status_code == 200
    restored = client.get(f"/projects/{project_id}/studio-state", headers=headers).json()["state"]
    params = restored["nodes"]["image_1"]["params"]
    assert params["progressPercent"] == 42
    assert params["jobProgress"]["label"] == "图片生成进行中"
    assert params["terminalProgress"]["percent"] == 100
    assert params["candidatePreviewUrls"][0]["url"] == candidate_url
    assert params["candidatePreviewUrls"][0]["preview_url"] == candidate_url
    assert params["candidatePreviewUrls"][0]["artifact_id"] == "artifact_safe_001"
    assert params["candidatePreviewUrls"][0]["candidate_id"] == "candidate_001"
    assert params["candidatePreviewUrls"][0]["canonical_digest"] == candidate_digest
    assert params["candidatePreviewUrls"][0]["parent_job_id"] == "job_keyframe_001"
    assert params["candidatePreviewUrls"][0]["project_id"] == project_id
    assert params["candidatePreviewUrls"][0]["reusable_asset_authority"] == {
        "schema_version": "afs_studio_reusable_asset_authority.v0.1",
        "asset_id": "asset_safe_001",
        "role": "generated_keyframe_reference",
        "source_kind": "keyframe_candidate",
        "status": "succeeded",
        "source_job_id": "job_keyframe_001",
        "source_candidate_id": "candidate_001",
        "source_candidate_digest": candidate_digest,
        "sha256": candidate_digest,
    }
    assert "internal_note" not in params["candidatePreviewUrls"][0]["reusable_asset_authority"]


def test_studio_state_candidate_authority_mismatches_fail_closed(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "studio-authority-mismatch"
    job_id = "job_keyframe_001"
    candidate_id = "candidate_001"
    candidate_digest = "a" * 64
    client.post("/projects", json={"project_id": project_id, "goal": "Studio authority mismatch test"})
    candidate_url = (
        f"/projects/{project_id}/keyframe-generations/{job_id}/"
        f"candidates/{candidate_id}/preview"
    )
    authority = {
        "schema_version": "afs_studio_reusable_asset_authority.v0.1",
        "asset_id": "asset_safe_001",
        "role": "generated_keyframe_reference",
        "source_kind": "keyframe_candidate",
        "status": "succeeded",
        "source_job_id": job_id,
        "source_candidate_id": candidate_id,
        "source_candidate_digest": candidate_digest,
        "sha256": candidate_digest,
    }
    candidate = {
        "url": candidate_url,
        "candidate_id": candidate_id,
        "canonical_digest": candidate_digest,
        "parent_job_id": job_id,
        "project_id": project_id,
        "reusable_asset_authority": authority,
    }
    variants = {
        "candidate_id": {**candidate, "candidate_id": "candidate_002"},
        "parent_job_id": {**candidate, "parent_job_id": "job_keyframe_002"},
        "project_id": {**candidate, "project_id": "another-project"},
        "canonical_digest": {**candidate, "canonical_digest": "b" * 64},
        "schema_version": {
            **candidate,
            "reusable_asset_authority": {**authority, "schema_version": "afs_studio_reusable_asset_authority.v9"},
        },
        "asset_id": {
            **candidate,
            "reusable_asset_authority": {**authority, "asset_id": "unsafe asset id"},
        },
        "role": {
            **candidate,
            "reusable_asset_authority": {**authority, "role": "unreviewed_reference"},
        },
        "source_kind": {
            **candidate,
            "reusable_asset_authority": {**authority, "source_kind": "uploaded_asset"},
        },
        "status": {
            **candidate,
            "reusable_asset_authority": {**authority, "status": "retryable"},
        },
        "source_job_id": {
            **candidate,
            "reusable_asset_authority": {**authority, "source_job_id": "job_keyframe_002"},
        },
        "source_candidate_id": {
            **candidate,
            "reusable_asset_authority": {**authority, "source_candidate_id": "candidate_002"},
        },
        "source_candidate_digest": {
            **candidate,
            "reusable_asset_authority": {**authority, "source_candidate_digest": "b" * 64},
        },
        "sha256": {
            **candidate,
            "reusable_asset_authority": {**authority, "sha256": "b" * 64},
        },
    }

    protected_keys = {
        "candidate_id",
        "canonical_digest",
        "parent_job_id",
        "project_id",
        "reusable_asset_authority",
    }
    for field, variant in variants.items():
        state = {
            "nodes": {
                "image_1": {
                    "id": "image_1",
                    "type": "image",
                    "params": {"candidatePreviewUrls": [variant]},
                }
            }
        }
        saved = client.put(f"/projects/{project_id}/studio-state", json={"state": state})
        assert saved.status_code == 200, field
        projected = saved.json()["state"]["nodes"]["image_1"]["params"]["candidatePreviewUrls"][0]
        assert projected["url"] == candidate_url, field
        assert protected_keys.isdisjoint(projected), field


def test_studio_state_preserves_public_generation_and_model_context_summaries(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "studio-public-generation-summary"
    client.post("/projects", json={"project_id": project_id, "goal": "Studio public summary state test"})
    state = {
        "nodes": {
            "image_1": {
                "id": "image_1",
                "type": "image",
                "title": "关键帧",
                "status": "error",
                "params": {
                    "lastModelCallContextId": "mctx_public_001",
                    "lastModelCallContextSummary": {
                        "context_id": "mctx_public_001",
                        "schema_version": "afs_model_call_context.v0.1",
                        "operation_intent": "prompt_optimize",
                        "generation_target": "prompt",
                        "artifact": {"artifact_id": "artifact_mctx_001", "filename": "model_call_context.json"},
                        "context_sources": {"context_bundle_present": True, "included_asset_count": 1},
                        "asset_context": {"context_eligible_asset_count": 1, "draft_assets_enter_context": False},
                        "reference_context": {"reference_image_count": 0},
                        "provider_constraints": {"capability": "llm", "provider_gate": "AFS_ALLOW_REMOTE_LLM"},
                        "trace_summary": {"warning_ids": ["w1"], "feedback_context_overlay_ids": ["ov1"]},
                        "safety_boundary": {"no_provider_raw": True, "no_local_path": True, "no_media_bytes": True},
                    },
                    "lastGenerationManifest": {
                        "status": "blocked",
                        "batch_status": "failed",
                        "stage": "provider_request_read",
                        "failure_class": "provider_timeout",
                        "output_count": 0,
                        "reference_image_count": 0,
                        "retry_count": 1,
                        "provider_calls_started": True,
                        "provider_diagnostics": {
                            "provider_stage": "provider_request_read",
                            "failure_class": "provider_timeout",
                            "error_type": "ModelGatewayError",
                            "reason": "API relay request timed out while reading provider result",
                            "required_gate": "AFS_ALLOW_REMOTE_IMAGE",
                            "retry_count": 1,
                            "attempt_count": 2,
                            "provider_elapsed_ms": 244000.1,
                        },
                        "blocks": [
                            {
                                "block_id": "remote_image_provider_not_ready",
                                "reason": "API relay request timed out while reading provider result",
                                "required_gate": "AFS_ALLOW_REMOTE_IMAGE",
                                "failure_class": "provider_timeout",
                                "provider_stage": "provider_request_read",
                                "retry_count": 1,
                                "attempt_count": 2,
                            }
                        ],
                    },
                    "generationStatusDetail": "No complete output is available.",
                    "generationBlockedReason": "API relay request timed out while reading provider result",
                    "generationNextAction": "Retry failed items only.",
                    "generationPolicyStatus": "failed",
                    "generationSafeRefs": [{"label": "job", "value": "job_001"}],
                },
            }
        },
        "order": ["image_1"],
    }

    saved = client.put(f"/projects/{project_id}/studio-state", json={"state": state})

    assert saved.status_code == 200
    params = saved.json()["state"]["nodes"]["image_1"]["params"]
    assert params["lastModelCallContextId"] == "mctx_public_001"
    assert params["lastModelCallContextSummary"]["safety_boundary"]["no_provider_raw"] is True
    assert params["lastModelCallContextSummary"]["trace_summary"]["warning_ids"] == ["w1"]
    manifest = params["lastGenerationManifest"]
    assert manifest["stage"] == "provider_request_read"
    assert manifest["failure_class"] == "provider_timeout"
    assert manifest["provider_diagnostics"]["attempt_count"] == 2
    assert manifest["blocks"][0]["provider_stage"] == "provider_request_read"
    serialized = str(params).lower()
    assert "raw_provider_response_stored" not in serialized
    assert "provider_raw_persisted" not in serialized


def test_studio_state_rejects_secrets_local_paths_and_provider_raw(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "studio-state-unsafe"
    client.post("/projects", json={"project_id": project_id, "goal": "Studio state safety test"})
    unsafe_payloads = [
        {"nodes": {"a": {"prompt": "sk-test-secret", "api_key": "x"}}},
        {"nodes": {"a": {"prompt": "C:\\Users\\secret\\image.png"}}},
        {"assets": [{"id": "a", "provider_raw": {"text": "raw"}}]},
        {"nodes": {"a": {"params": {"provider_config": "unsafe"}}}},
        {"nodes": {"a": {"params": {"signed_url": "https://example.invalid/signed"}}}},
        {"nodes": {"a": {"params": {"candidatePreviewUrls": [{"url": "https://example.invalid/private.png"}]}}}},
    ]

    for state in unsafe_payloads:
        response = client.put(f"/projects/{project_id}/studio-state", json={"state": state})
        assert response.status_code == 400


def test_sanitize_studio_state_keeps_only_safe_node_and_asset_fields() -> None:
    sanitized = sanitize_studio_state(
        {
            "nodes": {
                "node 1": {
                    "type": "image",
                    "title": "关键帧",
                    "x": 1,
                    "y": 2,
                    "params": {
                        "model": "safe-model",
                        "draft": "ignored",
                        "styleRef": "电影感",
                        "uploads": [{"asset_id": "img_safe"}],
                        "previewAspectRatio": "1:1",
                    },
                    "private": "ignored",
                }
            },
            "edges": {"edge 1": {"from": "node 1", "to": "node 2", "relation_type": "reference"}},
            "assets": [{"id": "asset 1", "kind": "keyframe", "title": "镜头 1", "summary": "安全摘要"}],
        }
    )

    node = next(iter(sanitized["nodes"].values()))
    assert node["params"] == {
        "model": "safe-model",
        "styleRef": "电影感",
        "uploads": [{"asset_id": "img_safe"}],
        "previewAspectRatio": "1:1",
    }
    assert "private" not in node
    assert next(iter(sanitized["edges"].values()))["relation_type"] == "reference"
    assert sanitized["assets"][0]["safe_summary"] == "安全摘要"


def test_studio_state_preserves_safe_asset_ids_and_feature_cards() -> None:
    sanitized = sanitize_studio_state(
        {
            "assets": [
                {
                    "id": "asset 1",
                    "kind": "visual_asset",
                    "title": "Zhou Tong",
                    "safe_summary": "black short hair",
                    "asset_id": "vas_abc123",
                    "visual_asset_id": "vas_abc123",
                    "asset_type": "character",
                    "signature": "black short hair in school uniform",
                    "feature_card": {"hair": "black short hair", "wardrobe": "blue white school uniform"},
                    "negative_locks": ["keep face identity", "keep uniform"],
                    "preview_url": "/projects/studio-state-demo/image-assets/img_safe_reference_001/preview",
                }
            ],
        },
        project_id="studio-state-demo",
    )

    asset = sanitized["assets"][0]
    assert asset["asset_id"] == "vas_abc123"
    assert asset["visual_asset_id"] == "vas_abc123"
    assert asset["asset_type"] == "character"
    assert asset["signature"] == "black short hair in school uniform"
    assert asset["feature_card"]["hair"] == "black short hair"
    assert asset["negative_locks"] == ["keep face identity", "keep uniform"]
    assert asset["preview_url"].endswith("/image-assets/img_safe_reference_001/preview")


def test_studio_state_preserves_safe_video_lifecycle_fields(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "studio-video-state"
    client.post("/projects", json={"project_id": project_id, "goal": "Studio video state test"})
    state = {
        "nodes": {
            "video_1": {
                "id": "video_1",
                "type": "video",
                "title": "Seedance I2V",
                "previewUrl": "/projects/studio-video-state/image-assets/img_first_001/preview",
                "params": {
                    "model": "seedance_i2v",
                    "firstFrameImageAssetId": "img_first_001",
                    "lastFrameImageAssetId": "img_last_001",
                    "lastVideoJobId": "video_job_001",
                    "lastVideoPreviewUrl": (
                        "/projects/studio-video-state/video-generations/"
                        "video_job_001/candidates/candidate_001/preview"
                    ),
                    "videoInputSource": {
                        "source_mode": "upstream_generated_image",
                        "source_asset_id": "img_first_001",
                        "source_node_id": "keyframe_1",
                        "source_job_id": "keyframe_job_001",
                        "visual_asset_id": "unsafe/path/ignored",
                        "role": "ignored_role",
                        "extra": "ignored",
                    },
                    "quotaOverrideConfirmed": True,
                },
                "status": "generating",
            }
        }
    }

    saved = client.put(f"/projects/{project_id}/studio-state", json={"state": state})
    assert saved.status_code == 200

    restored = client.get(f"/projects/{project_id}/studio-state")
    params = restored.json()["state"]["nodes"]["video_1"]["params"]
    assert params["firstFrameImageAssetId"] == "img_first_001"
    assert params["lastFrameImageAssetId"] == "img_last_001"
    assert params["lastVideoJobId"] == "video_job_001"
    assert params["lastVideoPreviewUrl"].endswith("/video-generations/video_job_001/candidates/candidate_001/preview")
    assert params["videoInputSource"] == {
        "source_mode": "upstream_generated_image",
        "source_asset_id": "img_first_001",
        "source_node_id": "keyframe_1",
        "source_job_id": "keyframe_job_001",
        "visual_asset_id": "unsafe-path-ignored",
        "role": "first_frame",
    }
    assert params["quotaOverrideConfirmed"] is True
    assert "previewUrl" not in restored.json()["state"]["nodes"]["video_1"]


def test_studio_state_prunes_media_filenames_before_global_safety_scan(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "studio-media-filename-state"
    client.post("/projects", json={"project_id": project_id, "goal": "Studio media filename pruning test"})
    video_preview = (
        "/projects/studio-media-filename-state/video-generations/"
        "video_job_001/candidates/candidate_001/preview"
    )
    image_preview = "/projects/studio-media-filename-state/image-assets/img_ref_001/preview"
    state = {
        "nodes": {
            "video_1": {
                "id": "video_1",
                "type": "video",
                "title": "视频结果",
                "params": {
                    "uploads": [
                        {
                            "asset_id": "video_candidate_001",
                            "filename": "candidate_001.mp4",
                            "role": "generated_video_reference",
                            "preview_url": video_preview,
                        },
                        {
                            "asset_id": "img_ref_001",
                            "filename": "reference.png",
                            "role": "reference_image",
                            "preview_url": image_preview,
                        },
                    ],
                    "lastVideoPreviewUrl": video_preview,
                },
            }
        },
        "assets": [
            {
                "id": "asset_video_1",
                "kind": "video_reference",
                "title": "candidate_001.mp4",
                "safe_summary": "candidate_001.mp4",
                "thumbnail_ref": "candidate_001.mp4",
                "asset_id": "video_candidate_001",
                "preview_url": video_preview,
                "status": "ready",
            }
        ],
        "order": ["video_1"],
    }

    saved = client.put(f"/projects/{project_id}/studio-state", json={"state": state})

    assert saved.status_code == 200
    saved_state = saved.json()["state"]
    serialized = str(saved_state).lower()
    assert ".mp4" not in serialized
    assert saved_state["nodes"]["video_1"]["params"]["uploads"][0]["asset_id"] == "video_candidate_001"
    assert "filename" not in saved_state["nodes"]["video_1"]["params"]["uploads"][0]
    assert saved_state["nodes"]["video_1"]["params"]["uploads"][1]["filename"] == "reference.png"
    assert saved_state["assets"][0]["asset_id"] == "video_candidate_001"
    assert saved_state["assets"][0]["preview_url"] == video_preview


def test_studio_state_preserves_safe_context_bundle_summary() -> None:
    sanitized = sanitize_studio_state(
        {
            "nodes": {
                "image_1": {
                    "type": "image",
                    "params": {
                        "lastContextBundle": {
                            "schema_version": "0.1",
                            "resolver_version": "resolver-v1",
                            "mode": "generate",
                            "subject_reference_asset_id": "vas_character_001",
                            "included_assets": [
                                {
                                    "asset_id": "vas_character_001",
                                    "asset_type": "character",
                                    "label": "Character A",
                                    "signature": "black short hair",
                                    "feature_card_hash": "hash123",
                                    "subject_reference": True,
                                }
                            ],
                            "excluded_assets": [
                                {
                                    "asset_id": "vas_character_002",
                                    "asset_type": "character",
                                    "label": "Character B",
                                    "reason": "degraded_to_signature_over_limit",
                                }
                            ],
                            "warnings": [
                                {
                                    "warning_id": "best_effort_lock_conflict",
                                    "asset_id": "vas_character_001",
                                    "lock_text": "keep black short hair",
                                    "attribute": "hair_color",
                                    "lock_value": "black",
                                    "prompt_value": "red",
                                }
                            ],
                            "temporary_lock_overrides": [
                                {
                                    "asset_id": "vas_character_001",
                                    "lock_text": "keep black short hair",
                                    "reason": "one-off-ui-unlock",
                                }
                            ],
                            "budget": {
                                "enforcement_applied": True,
                                "segments": {"visible_prompt": {"allocated": 550, "used": 420, "truncated": False}},
                            },
                            "text_channel": {"provider_prompt": "not persisted"},
                            "provider_raw": {"unsafe": True},
                        }
                    },
                }
            }
        }
    )

    bundle = sanitized["nodes"]["image_1"]["params"]["lastContextBundle"]
    assert bundle["included_assets"][0]["asset_id"] == "vas_character_001"
    assert bundle["included_assets"][0]["subject_reference"] is True
    assert bundle["excluded_assets"][0]["reason"] == "degraded_to_signature_over_limit"
    assert bundle["warnings"][0]["prompt_value"] == "red"
    assert bundle["temporary_lock_overrides"][0]["lock_text"] == "keep black short hair"
    assert bundle["budget"]["segments"]["visible_prompt"]["allocated"] == 550
    assert "text_channel" not in bundle
    assert "provider_raw" not in bundle


def test_studio_state_rejects_unsafe_video_preview_url(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "studio-video-state-unsafe"
    client.post("/projects", json={"project_id": project_id, "goal": "Studio video state safety test"})

    response = client.put(
        f"/projects/{project_id}/studio-state",
        json={
            "state": {
                "nodes": {
                    "video_1": {
                        "type": "video",
                        "params": {
                            "lastVideoPreviewUrl": "D:\\provider\\raw\\candidate_001.mp4",
                        },
                    }
                }
            }
        },
    )

    assert response.status_code == 400
