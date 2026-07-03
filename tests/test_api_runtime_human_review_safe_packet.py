from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from agentflow.harness.json_io import write_json
from apps.api.runtime_human_review_safe_packet import (
    build_safe_human_review_packet,
    select_safe_human_review_packet_sources,
)
from apps.api.runtime_keyframe_payloads import (
    keyframe_candidate_summary,
    keyframe_review_preview_refs,
    keyframe_safe_manifest,
)
from apps.api.runtime_models import KeyframeGenerationRequest, PromptOptimizationRequest
from apps.api.runtime_prompt_review_summary import prompt_optimization_review_summary
from apps.api.runtime_service import create_runtime_app
from apps.api.runtime_store import RuntimeStore


FORBIDDEN_PACKET_FRAGMENTS = (
    "/home/",
    "c:\\",
    "d:\\",
    "signed_url",
    "provider_raw",
    "raw_response",
    "media_bytes",
    "image_bytes",
    "file_bytes",
    "data_base64",
    "api_key",
    "access_token",
    "authorization",
    "bearer ",
    "session",
    "token",
    "cookie",
    "password",
    "api key",
    "auth ",
    "client_secret",
    "private-key",
    "provider key",
)
FORBIDDEN_PROMPT_REVIEW_VALUES = (
    "alpha001",
    "bravo002",
    "charlie003",
    "delta004",
    "echo005",
    "foxtrot006",
    "golf007",
    "hotel008",
    "india009",
    "juliet010",
    "kilo011",
)
FORBIDDEN_PROMPT_REVIEW_LABELS = (
    "password",
    "token",
    "access_token",
    "auth",
    "authorization",
    "cookie",
    "session",
    "api key",
    "secret",
    "bearer",
    "client_secret",
    "private-key",
    "provider key",
)


def test_keyframe_review_preview_refs_persist_on_manifest_and_candidate_summary() -> None:
    request = _keyframe_request()
    outputs = [_safe_output()]
    refs = keyframe_review_preview_refs("safe-review-proj", "job_keyframe_001", outputs)

    summary = keyframe_candidate_summary(
        request,
        "A bounded prompt.",
        outputs,
        ["not human acceptance"],
        project_id="safe-review-proj",
        job_id="job_keyframe_001",
    )
    manifest = keyframe_safe_manifest(
        "safe-review-proj",
        request,
        status="succeeded",
        provider_gate={"capability": "image", "env": "AFS_ALLOW_REMOTE_IMAGE", "status": "ready_not_run"},
        blocks=[],
        provider_calls_started=False,
        output_count=1,
        reference_image_count=0,
        retry_count=0,
        context_bundle=None,
        non_claims=["not human acceptance"],
        job_id="job_keyframe_001",
        review_preview_refs=refs,
    )

    assert refs == [
        {
            "job_id": "job_keyframe_001",
            "candidate_id": "candidate_001",
            "safe_preview_ref": "/projects/safe-review-proj/keyframe-generations/job_keyframe_001/candidates/candidate_001/preview",
            "byte_count": 68,
            "sha256": "a" * 64,
            "width": 720,
            "height": 1280,
            "aspect_ratio": "9:16",
        }
    ]
    assert summary["review_preview_refs"] == refs
    assert manifest["review_preview_refs"] == refs
    assert manifest["review_preview_ref_policy"] == "safe_route_and_metadata_only"


def test_prompt_optimization_writes_safe_review_summary_artifact(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_LLM", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    response = client.post(
        "/projects/safe-prompt-review/prompt-optimizations",
        json={
            "node_id": "image-prompt-review",
            "node_type": "image",
            "prompt_text": "A calm portrait in a small studio.",
            "generation_target": "keyframe",
            "target_platform": "short_video",
            "style": "restrained cinematic",
            "generated_at": "2026-07-04T02:00:00+08:00",
        },
    )

    response.raise_for_status()
    payload = response.json()
    artifacts = payload["artifacts"]
    summary_artifact = artifacts["prompt_optimization_review_summary"]
    summary = client.get(f"/artifacts/{summary_artifact['artifact_id']}").json()["payload"]
    manifest = client.get(f"/artifacts/{artifacts['prompt_optimization_safe_manifest']['artifact_id']}").json()["payload"]

    assert summary["artifact_type"] == "agentflow_prompt_optimization_review_summary"
    assert summary["optimized_prompt_char_count"] == len(payload["optimized_prompt"])
    assert summary["optimized_prompt_text"]
    assert summary["source_artifact_id"] == artifacts["creative_brief"]["artifact_id"]
    assert manifest["prompt_review_summary_ref"] == "prompt_optimization_review_summary.json"
    assert "prompt_optimization_review_summary.json" in manifest["safe_artifacts"]


def test_prompt_review_summary_redacts_secret_like_labels_and_values(tmp_path) -> None:
    summary = _prompt_review_summary_from_text(tmp_path, _secret_like_prompt_text())
    text = summary["optimized_prompt_text"].lower()
    serialized = json.dumps(summary, ensure_ascii=False).lower()

    assert "[redacted]" in text
    for value in FORBIDDEN_PROMPT_REVIEW_VALUES:
        assert value not in serialized
    for label in FORBIDDEN_PROMPT_REVIEW_LABELS:
        assert label not in text


def test_safe_packet_uses_redacted_prompt_summary_and_rejects_unsafe_prompt_text(tmp_path) -> None:
    manifest = _safe_keyframe_manifest()
    summary = _prompt_review_summary_from_text(tmp_path, _secret_like_prompt_text())
    packet = build_safe_human_review_packet("safe-review-proj", manifest, summary)
    serialized = json.dumps(packet, ensure_ascii=False).lower()

    _assert_packet_safe(packet)
    assert "[redacted]" in packet["prompt_summary"]["optimized_prompt_text"]
    for value in FORBIDDEN_PROMPT_REVIEW_VALUES:
        assert value not in serialized

    unsafe_summary = {
        **_safe_prompt_summary(),
        "optimized_prompt_text": "Authorization: Bearer packet-leak-value",
    }
    with pytest.raises(ValueError, match="forbidden private or raw field"):
        build_safe_human_review_packet("safe-review-proj", manifest, unsafe_summary)


def test_safe_packet_builder_fails_closed_when_preview_or_prompt_fields_are_missing() -> None:
    manifest = _safe_keyframe_manifest()
    prompt_summary = _safe_prompt_summary()

    missing_preview = {**manifest, "review_preview_refs": []}
    with pytest.raises(ValueError, match="review_preview_refs"):
        build_safe_human_review_packet("safe-review-proj", missing_preview, prompt_summary)

    missing_prompt = {**prompt_summary}
    missing_prompt.pop("source_artifact_id")
    with pytest.raises(ValueError, match="prompt review summary missing fields"):
        build_safe_human_review_packet("safe-review-proj", manifest, missing_prompt)


def test_safe_packet_builder_excludes_forbidden_source_fields_and_selector_builds_happy_path(tmp_path) -> None:
    manifest = {
        **_safe_keyframe_manifest(),
        "provider_raw_response": {"signed_url": "https://private.example.test/raw"},
        "outputs": [{"image_path": "/home/private/candidate_001.png"}],
    }
    prompt_summary = {
        **_safe_prompt_summary(),
        "raw_auth_session_cookie_password": "bearer secret-token cookie=session",
    }
    packet = build_safe_human_review_packet("safe-review-proj", manifest, prompt_summary)
    _assert_packet_safe(packet)
    assert packet["packet_state"] == "ready_for_redacted_human_review_packet"
    assert packet["keyframe_review_previews"][0]["safe_preview_ref"].endswith("/candidate_001/preview")
    assert packet["prompt_summary"]["source_artifact_id"] == "runs-safe-review-proj-prompt-job-creative_brief"

    store = RuntimeStore(tmp_path)
    output_dir = store.run_dir("safe-review-proj", "safe-review-source")
    output_dir.mkdir(parents=True)
    manifest_path = write_json(output_dir / "keyframe_generation_safe_manifest.json", _safe_keyframe_manifest())
    prompt_path = write_json(output_dir / "prompt_optimization_review_summary.json", _safe_prompt_summary())
    manifest_artifact = store.register_artifact(manifest_path, role="keyframe_generation_safe_manifest")
    prompt_artifact = store.register_artifact(prompt_path, role="prompt_optimization_review_summary")

    selected = select_safe_human_review_packet_sources(
        store,
        "safe-review-proj",
        keyframe_safe_manifest_artifact_id=manifest_artifact["artifact_id"],
        prompt_review_summary_artifact_id=prompt_artifact["artifact_id"],
    )

    _assert_packet_safe(selected)
    assert selected["source_artifact_ids"]["keyframe_safe_manifest"] == manifest_artifact["artifact_id"]
    assert selected["source_artifact_ids"]["prompt_review_summary"] == prompt_artifact["artifact_id"]


def _safe_keyframe_manifest() -> dict:
    request = _keyframe_request()
    refs = keyframe_review_preview_refs("safe-review-proj", "job_keyframe_001", [_safe_output()])
    return keyframe_safe_manifest(
        "safe-review-proj",
        request,
        status="succeeded",
        provider_gate={"capability": "image", "env": "AFS_ALLOW_REMOTE_IMAGE", "status": "ready_not_run"},
        blocks=[],
        provider_calls_started=False,
        output_count=1,
        reference_image_count=0,
        retry_count=0,
        context_bundle=None,
        non_claims=["not human acceptance"],
        job_id="job_keyframe_001",
        review_preview_refs=refs,
    )


def _safe_prompt_summary() -> dict:
    return {
        "artifact_type": "agentflow_prompt_optimization_review_summary",
        "schema_version": "0.1.0",
        "project_id": "safe-review-proj",
        "node_id": "image-prompt-review",
        "source_artifact_id": "runs-safe-review-proj-prompt-job-creative_brief",
        "source_artifact_role": "creative_brief",
        "optimized_prompt_char_count": 38,
        "optimized_prompt_text": "A calm portrait, safe for local review.",
        "optimized_prompt_text_truncated": False,
    }


def _prompt_review_summary_from_text(tmp_path, prompt_text: str) -> dict:
    store = RuntimeStore(tmp_path)
    output_dir = store.run_dir("safe-review-proj", "prompt-review-redaction")
    return prompt_optimization_review_summary(
        store,
        output_dir,
        project_id="safe-review-proj",
        request=_prompt_request(),
        optimized_prompt=prompt_text,
    )


def _secret_like_prompt_text() -> str:
    return "\n".join(
        [
            'password = "alpha001"',
            '"token": "bravo002"',
            "access_token: 'charlie003'",
            "auth delta004",
            "Authorization: Bearer echo005",
            "Cookie: session=foxtrot006; theme=public",
            "api key golf007",
            "secret = hotel008",
            "client_secret: india009",
            "private-key = juliet010",
            'provider key: "kilo011"',
            "A calm portrait, safe for local review.",
        ]
    )


def _prompt_request() -> PromptOptimizationRequest:
    return PromptOptimizationRequest(
        node_id="image-prompt-review",
        node_type="image",
        prompt_text="A calm portrait.",
        generation_target="keyframe",
        target_platform="short_video",
        style="restrained cinematic",
        generated_at="2026-07-04T02:00:00+08:00",
    )


def _keyframe_request() -> KeyframeGenerationRequest:
    return KeyframeGenerationRequest(
        node_id="image-review",
        prompt_text="A calm portrait.",
        optimized_prompt="A calm portrait.",
        candidate_count=1,
        generated_at="2026-07-04T02:00:00+08:00",
    )


def _safe_output() -> dict:
    return {
        "candidate_id": "candidate_001",
        "byte_count": 68,
        "sha256": "a" * 64,
        "width": 720,
        "height": 1280,
        "aspect_ratio": "9:16",
        "provider_url_persisted": False,
    }


def _assert_packet_safe(packet: dict) -> None:
    serialized = json.dumps(packet, ensure_ascii=False).lower()
    for fragment in FORBIDDEN_PACKET_FRAGMENTS:
        assert fragment not in serialized
