from __future__ import annotations

import json
import subprocess
from pathlib import Path


STUDIO_ROOT = Path("apps/studio")


def _run_node(script: str) -> dict:
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
    )
    return json.loads(completed.stdout)


def test_video_admission_workspace_builds_exact_reserved_request() -> None:
    payload = _run_node(
        r'''
import {
  videoAdmissionGenerationRequest,
  videoAdmissionProjection,
} from "./apps/studio/src/video-admission-workspace.js";

const manifest = {
  status: "locked",
  manifest_id: "video-manifest-a",
  manifest_hash: "a".repeat(64),
  provider_contract: {
    model: "doubao-seedance-2-0",
    model_variant: "non_fast",
    create_endpoint: "/volc/v1/contents/generations/tasks",
    resolution: "720p",
    duration_sec: 6,
    max_dispatches: 1,
    auto_retry: 0,
  },
  budget_contract: {
    hard_ceiling_usd: "2.00",
    classification: "program_stop_ceiling_not_provider_enforced_estimate_or_actual",
    actual_charge_usd: null,
  },
  provider_input_contract: {
    mode: "first_frame",
    first_frame: {
      image_asset_id: "keyframe-approved",
      label: "已批准关键帧",
      role: "first_frame",
    },
    last_frame: null,
    reference_images: [],
    frame_role_cardinality: {
      first_frame: 1,
      last_frame: 0,
      reference_image: 0,
    },
  },
  source: {
    shot: { shot_id: "shot-01", label: "镜头 01" },
    keyframe: {
      image_asset_id: "keyframe-approved",
      label: "已批准关键帧",
      aspect_ratio: "16:9",
    },
    references: [
      { image_asset_id: "character-approved" },
      { image_asset_id: "scene-approved" },
      { image_asset_id: "prop-approved" },
    ],
    prompt_contract: {
      provider_prompt: "Canonical shot action and continuity.",
      camera_movement: "slow push in",
    },
  },
  item: {
    item_id: "video-shot-01",
    state: "reserved",
    reservation_token: "reservation-a",
  },
  provider_dispatch_count: 0,
};
const projection = videoAdmissionProjection({
  manifest,
  readiness: { status: "ready" },
  capability: { configured: true },
});
const request = videoAdmissionGenerationRequest(manifest, "2026-07-26T03:00:00Z");
process.stdout.write(JSON.stringify({ projection, request }));
'''
    )

    projection = payload["projection"]
    request = payload["request"]
    assert projection["generation_contract"]["model"] == "doubao-seedance-2-0"
    assert projection["budget_contract"]["hard_ceiling_usd"] == "2.00"
    assert projection["provider_dispatch_count"] == 0
    assert request == {
        "node_id": "shot-01",
        "prompt_text": "Canonical shot action and continuity.",
        "provider_service_id": "seedance_i2v",
        "first_frame_image_asset_id": "keyframe-approved",
        "reference_image_asset_ids": [],
        "duration_sec": 6,
        "resolution": "720p",
        "aspect_ratio": "16:9",
        "motion": "slow push in",
        "candidate_count": 1,
        "video_admission_manifest_id": "video-manifest-a",
        "video_admission_manifest_hash": "a" * 64,
        "video_admission_item_id": "video-shot-01",
        "video_admission_reservation_token": "reservation-a",
        "generated_at": "2026-07-26T03:00:00Z",
    }


def test_video_admission_workspace_rejects_unreserved_or_incomplete_manifest() -> None:
    payload = _run_node(
        r'''
import { videoAdmissionGenerationRequest } from "./apps/studio/src/video-admission-workspace.js";

const outcomes = [];
for (const manifest of [
  { item: { state: "planned" }, source: {} },
  {
    item: { state: "reserved" },
    source: { keyframe: { image_asset_id: "frame" }, prompt_contract: {} },
  },
]) {
  try {
    videoAdmissionGenerationRequest(manifest, "2026-07-26T03:00:00Z");
    outcomes.push("accepted");
  } catch (error) {
    outcomes.push(String(error.message));
  }
}
process.stdout.write(JSON.stringify({ outcomes }));
'''
    )

    assert payload["outcomes"] == [
        "视频生成确认缺少已批准关键帧或单次额度",
        "视频生成确认缺少已批准关键帧或单次额度",
    ]


def test_product_shell_discloses_video_contract_and_keeps_generation_gated() -> None:
    source = (STUDIO_ROOT / "src" / "product-shell.js").read_text(encoding="utf-8")

    for creator_text in (
        "准备单镜头视频",
        "已批准关键帧驱动",
        "doubao-seedance-2-0",
        "非 fast",
        "720p",
        "6 秒",
        "已批准关键帧",
        "参考图",
        "项目参考组",
        "$2.00 项目停止线（当前新轮次",
        "1 次发送",
        "自动重试 0",
        "建立新的单次视频清单",
        "批准并写入项目",
        "不会自动重试",
    ):
        assert creator_text in source
    assert 'generate.disabled = !snapshot.mediaGates?.video' in source
    assert 'if (!snapshot.mediaGates?.video)' in source
    assert 'videoAdmissionMediaState !== "loaded"' in source
    assert 'video.addEventListener("loadeddata"' in source
    assert 'if (view.readiness?.status !== "ready")' in source
    assert "视频准备需要更新" in source
    assert 'panel?.scrollIntoView({ block: "start", behavior: "auto" })' in source
    assert "video_admission_manifest_id" not in source
    assert "video_admission_reservation_token" not in source
    assert "doubao-seedance-2-0-fast" not in source
    assert "写入当前 ProductionGraph" not in source
    assert "镜头 01" not in source
    assert "videoAdmissionView().item?.job_id === result.job_id" in source
    assert "manifest.source?.references" in source


def test_video_admission_runtime_client_uses_project_scoped_authenticated_routes() -> None:
    source = (STUDIO_ROOT / "src" / "runtime-client.js").read_text(encoding="utf-8")

    assert "/m6/video-admission`" in source
    assert "/m6/video-admission/commands/preview`" in source
    assert "/m6/video-admission/commands/confirm`" in source
    assert "if (token) headers.Authorization = `Bearer ${token}`" in source
