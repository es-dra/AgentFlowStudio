from __future__ import annotations

import json
import subprocess
import textwrap
from pathlib import Path


STUDIO_ROOT = Path("apps/studio")


def test_keyframe_video_surfaces_distinguish_regenerate_from_local_edit() -> None:
    node_menu = (STUDIO_ROOT / "src" / "panels" / "node-menu.js").read_text(encoding="utf-8")
    result_view = (STUDIO_ROOT / "src" / "node-result-view.js").read_text(encoding="utf-8")
    prompt_bar = (STUDIO_ROOT / "src" / "prompt-bar.js").read_text(encoding="utf-8")
    asset_panel = (STUDIO_ROOT / "src" / "panels" / "asset-card-panel.js").read_text(encoding="utf-8")
    algorithm_panel = (STUDIO_ROOT / "src" / "panels" / "algorithm-context-panel.js").read_text(encoding="utf-8")

    assert "重新生成整张图" in node_menu
    assert "重新生成整段视频" in node_menu
    assert "创建局部编辑需求草稿" in node_menu
    assert "关键帧局部编辑不可用" in node_menu
    assert "局部视频编辑不可用" in node_menu
    assert "需要 image-edit/mask 能力" in node_menu
    assert "需要 video-edit/mask/temporal 能力" in node_menu
    assert "创建视频重生成草稿" in node_menu
    assert "创建视频修改草稿" not in node_menu

    assert "重新生成整张" in result_view
    assert "重新生成整段" in result_view
    assert "这不是局部编辑" in result_view
    assert "提交视频重生成尝试；不是局部编辑" in prompt_bar

    assert "保存并重新生成资产图" in asset_panel
    assert "保存并局部修订生成" not in asset_panel
    assert "局部图像编辑未开放" in asset_panel
    assert "重新绘制整张资产图" in asset_panel
    assert "视频重生成尝试" in algorithm_panel
    assert "重生成片段" in algorithm_panel


def test_video_revision_draft_records_local_edit_unavailable_state() -> None:
    script = textwrap.dedent(
        """
        import { enableVideoRevisionDraft } from "./apps/studio/src/node-video-actions.js";

        const state = {
          nodes: {
            video_1: {
              id: "video_1",
              type: "video",
              prompt: "只让灯光更冷",
              params: { lastVideoJobId: "video_job_001" },
              result: "",
            },
          },
        };
        const store = {
          get: () => state,
          set: (mutator) => mutator(state),
        };

        enableVideoRevisionDraft(store, state.nodes.video_1);
        process.stdout.write(JSON.stringify(state.nodes.video_1));
        """
    )
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    node = json.loads(completed.stdout)
    revision = node["params"]["videoRevision"]
    availability = revision["local_edit_availability"]

    assert revision["enabled"] is True
    assert revision["provider_capability_mode"] == "i2v_revision_attempt"
    assert availability["status"] == "unavailable"
    assert availability["required_capability"] == "video_edit_or_masked_temporal_edit"
    assert availability["reason"] == "current_video_revision_is_global_regeneration_attempt"
    assert "这不是局部编辑" in node["result"]
    assert "整段重生成尝试" in node["result"]
    assert "video-edit/mask/temporal" in node["result"]


def test_local_edit_honesty_does_not_change_runtime_or_provider_contract_markers() -> None:
    video_actions = (STUDIO_ROOT / "src" / "node-video-actions.js").read_text(encoding="utf-8")
    keyframe_actions = (STUDIO_ROOT / "src" / "node-keyframe-actions.js").read_text(encoding="utf-8")
    runtime_client = (STUDIO_ROOT / "src" / "runtime-client.js").read_text(encoding="utf-8")

    assert "provider_capability_mode: \"i2v_revision_attempt\"" in video_actions
    assert "runtime.generateVideo(request)" in video_actions
    assert "runtime.generateVideoRevision(request)" in video_actions
    assert "runtime.generateKeyframe(request)" in keyframe_actions
    assert "/video-revisions" in runtime_client
    assert "/keyframe-generations" in runtime_client
    assert "preflightKeyframeLocalEdit" in runtime_client
    assert "/keyframe-local-edits/preflight" in runtime_client
    assert "preflight_keyframe_local_edit" in runtime_client


def test_keyframe_local_edit_draft_records_lineage_without_execution() -> None:
    script = textwrap.dedent(
        """
        import { createKeyframeLocalEditDraft } from "./apps/studio/src/keyframe-local-edit-contract.js";

        const state = {
          nodes: {
            keyframe_1: {
              id: "keyframe_1",
              type: "image",
              title: "关键帧 · 天台",
              prompt: "只把窗户灯光改冷，其他不变",
              previewUrl: "/projects/demo/keyframe.png",
              params: {
                nodeRole: "keyframe_generation",
                lastKeyframeJobId: "kg_job_001",
                lastKeyframeCompletedJobId: "kg_job_001",
                uploads: [{
                  asset_id: "img_asset_001",
                  preview_url: "/projects/demo/keyframe.png",
                  source_candidate_id: "candidate_001",
                }],
              },
              result: "ready",
            },
          },
          assets: [],
        };
        const store = {
          get: () => state,
          set: (mutator) => mutator(state),
        };

        createKeyframeLocalEditDraft(store, state.nodes.keyframe_1, {
          generatedAt: "2026-07-06T00:00:00.000Z",
          editIntent: "只修改左侧窗户灯光，不改变人物和构图",
          editScope: { kind: "semantic_region", target_description: "左侧窗户灯光区域" },
        });
        process.stdout.write(JSON.stringify(state.nodes.keyframe_1));
        """
    )
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    node = json.loads(completed.stdout)
    draft = node["params"]["keyframeLocalEditDraft"]
    request = draft["request"]
    preflight = draft["preflight"]
    availability = node["params"]["local_edit_availability"]

    assert request["schema_version"] == "afs_keyframe_local_edit_request.v0.1"
    assert request["parent_lineage"]["immutable_parent"] is True
    assert request["parent_lineage"]["parent_keyframe_job_id"] == "kg_job_001"
    assert request["parent_lineage"]["parent_image_asset_id"] == "img_asset_001"
    assert request["fallback_policy"]["allow_full_frame_fallback"] is False
    assert request["provider_capability_mode"] == "no_provider_execution"
    assert preflight["schema_version"] == "afs_keyframe_local_edit_preflight.v0.1"
    assert preflight["contract_status"] == "ready_no_provider_execution"
    assert preflight["execution_status"] == "blocked_no_local_transform"
    assert preflight["provider_calls_started"] is False
    assert preflight["local_transformation_started"] is False
    assert preflight["generated_media_created"] is False
    assert preflight["fallback_full_frame_edit"] is False
    assert preflight["local_edit_truth_label"] == "request_contract_only"
    assert "preflight_token" not in preflight
    assert preflight["preflight_receipt_status"] == "local_hash_pruned_before_persistence"
    assert preflight["preflight_receipt_persisted"] is False
    assert preflight["runtime_preflight_recorded"] is False
    assert "no_pixel_transformation" in preflight["non_claims"]
    assert availability["status"] == "contract_ready_execution_blocked"
    assert "No provider call, generated media, or local pixel/image transform was performed." in node["result"]
    assert "不会生成媒体、不会调用 provider" in node["result"]


def test_keyframe_local_edit_action_records_runtime_preflight_without_persisting_token() -> None:
    script = textwrap.dedent(
        """
        import { createKeyframeLocalEditDraft } from "./apps/studio/src/node-actions.js";

        const state = {
          nodes: {
            keyframe_1: {
              id: "keyframe_1",
              type: "image",
              title: "Keyframe 001",
              prompt: "Only cool the window light while preserving the character and composition.",
              previewUrl: "/projects/demo/keyframe.png",
              params: {
                nodeRole: "keyframe_generation",
                lastKeyframeJobId: "kg_job_001",
                lastKeyframeCompletedJobId: "kg_job_001",
                uploads: [{
                  asset_id: "img_asset_001",
                  preview_url: "/projects/demo/keyframe.png",
                  source_candidate_id: "candidate_001",
                }],
              },
              result: "ready",
            },
          },
          assets: [],
        };
        let flushCalls = 0;
        const store = {
          get: () => state,
          set: (mutator) => mutator(state),
          flushRuntimeSave: async () => { flushCalls += 1; },
        };
        let runtimeCalls = 0;
        let capturedRequest = null;
        const runtime = {
          preflightKeyframeLocalEdit: async (request) => {
            runtimeCalls += 1;
            capturedRequest = request;
            return {
              schema_version: "afs_keyframe_local_edit_preflight.v0.1",
              project_id: "local-edit-runtime-preflight",
              request_id: request.request_id,
              contract_status: "ready_no_provider_execution",
              execution_status: "blocked_no_local_transform",
              provider_calls_started: false,
              local_transformation_started: false,
              generated_media_created: false,
              fallback_full_frame_edit: false,
              local_edit_truth_label: "request_contract_only",
              blocking_capability: "image_edit_or_masked_local_transform",
              blockers: [{
                code: "execution_not_implemented",
                reason: "Local pixel transformation is not implemented in this no-provider preflight slice.",
                provider_calls_started: false,
                local_transformation_started: false,
                generated_media_created: false,
              }],
              allowed_next_actions: ["refine_edit_scope", "route_to_transform_or_provider_implementation_lane"],
              preflight_token: "runtime-token-should-not-persist",
              non_claims: ["no_provider_call", "no_generated_media", "no_pixel_transformation", "not_full_frame_fallback"],
            };
          },
        };

        await createKeyframeLocalEditDraft(store, runtime, state.nodes.keyframe_1, {
          generatedAt: "2026-07-06T00:00:00.000Z",
          editIntent: "Only cool the window light while preserving the character and composition.",
          editScope: { kind: "semantic_region", target_description: "left window light area" },
        });
        process.stdout.write(JSON.stringify({
          node: state.nodes.keyframe_1,
          runtimeCalls,
          capturedRequest,
          flushCalls,
        }));
        """
    )
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(completed.stdout)
    node = payload["node"]
    request = payload["capturedRequest"]
    preflight = node["params"]["keyframeLocalEditDraft"]["preflight"]
    serialized = json.dumps(node, ensure_ascii=False).lower()

    assert payload["runtimeCalls"] == 1
    assert payload["flushCalls"] == 1
    assert request["fallback_policy"]["allow_full_frame_fallback"] is False
    assert request["fallback_policy"]["fallback_truth_label"] == "not_allowed_in_first_slice"
    assert request["provider_capability_mode"] == "no_provider_execution"
    assert preflight["preflight_source"] == "runtime"
    assert preflight["runtime_preflight_recorded"] is True
    assert preflight["runtime_project_id"] == "local-edit-runtime-preflight"
    assert preflight["contract_status"] == "ready_no_provider_execution"
    assert preflight["execution_status"] == "blocked_no_local_transform"
    assert preflight["provider_calls_started"] is False
    assert preflight["local_transformation_started"] is False
    assert preflight["generated_media_created"] is False
    assert preflight["fallback_full_frame_edit"] is False
    assert preflight["preflight_receipt_status"] == "issued_pruned_before_persistence"
    assert preflight["preflight_receipt_persisted"] is False
    assert "preflight_token" not in serialized
    assert "runtime-token-should-not-persist" not in serialized
    assert "Runtime preflight recorded" in node["result"]
    assert "raw preflight receipt is pruned" in node["result"]
    assert "No provider call, generated media, or local pixel/image transform was performed." in node["result"]


def test_keyframe_local_edit_action_keeps_node_menu_draft_blocked_without_user_scope() -> None:
    script = textwrap.dedent(
        """
        import { createKeyframeLocalEditDraft } from "./apps/studio/src/node-actions.js";

        const state = {
          nodes: {
            keyframe_1: {
              id: "keyframe_1",
              type: "image",
              title: "Keyframe 001",
              prompt: "Only cool the window light while preserving the character and composition.",
              previewUrl: "/projects/demo/keyframe.png",
              params: {
                nodeRole: "keyframe_generation",
                lastKeyframeJobId: "kg_job_001",
                lastKeyframeCompletedJobId: "kg_job_001",
                uploads: [{
                  asset_id: "img_asset_001",
                  preview_url: "/projects/demo/keyframe.png",
                  source_candidate_id: "candidate_001",
                }],
              },
              result: "ready",
            },
          },
          assets: [],
        };
        const store = {
          get: () => state,
          set: (mutator) => mutator(state),
          flushRuntimeSave: async () => {},
        };
        let capturedRequest = null;
        const runtime = {
          preflightKeyframeLocalEdit: async (request) => {
            capturedRequest = request;
            return {
              schema_version: "afs_keyframe_local_edit_preflight.v0.1",
              project_id: "local-edit-runtime-preflight",
              request_id: request.request_id,
              contract_status: "draft_needs_input",
              execution_status: "blocked_missing_required_input",
              provider_calls_started: false,
              local_transformation_started: false,
              generated_media_created: false,
              fallback_full_frame_edit: false,
              local_edit_truth_label: "request_contract_only",
              blocking_capability: "image_edit_or_masked_local_transform",
              blockers: [{
                code: "missing_edit_scope",
                reason: "Missing local edit target description.",
                provider_calls_started: false,
                local_transformation_started: false,
                generated_media_created: false,
              }],
              allowed_next_actions: ["add_parent_image_asset", "add_edit_intent", "refine_edit_scope"],
              non_claims: ["no_provider_call", "no_generated_media", "no_pixel_transformation", "not_full_frame_fallback"],
            };
          },
        };

        await createKeyframeLocalEditDraft(store, runtime, state.nodes.keyframe_1, {
          generatedAt: "2026-07-06T00:00:00.000Z",
        });
        process.stdout.write(JSON.stringify({
          node: state.nodes.keyframe_1,
          capturedRequest,
        }));
        """
    )
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(completed.stdout)
    request = payload["capturedRequest"]
    node = payload["node"]
    preflight = node["params"]["keyframeLocalEditDraft"]["preflight"]
    blocker_codes = {blocker["code"] for blocker in preflight["blockers"]}

    assert request["edit_intent"] == "Only cool the window light while preserving the character and composition."
    assert request["edit_scope"]["target_description"] == ""
    assert preflight["contract_status"] == "draft_needs_input"
    assert preflight["execution_status"] == "blocked_missing_required_input"
    assert "missing_edit_scope" in blocker_codes
    assert node["params"]["local_edit_availability"]["status"] == "draft_needs_input"
    assert preflight["provider_calls_started"] is False
    assert preflight["generated_media_created"] is False
    assert preflight["fallback_full_frame_edit"] is False


def test_keyframe_local_edit_action_redacts_unsafe_runtime_preflight_error_copy() -> None:
    script = textwrap.dedent(
        """
        import { createKeyframeLocalEditDraft } from "./apps/studio/src/node-actions.js";

        const state = {
          nodes: {
            keyframe_unsafe: {
              id: "keyframe_unsafe",
              type: "image",
              prompt: "Safe parent keyframe prompt",
              params: {
                nodeRole: "keyframe_generation",
                lastKeyframeCompletedJobId: "kg_job_001",
                uploads: [{ asset_id: "img_asset_001", preview_url: "/projects/demo/keyframe.png" }],
              },
              result: "ready",
            },
          },
          assets: [],
        };
        const store = {
          get: () => state,
          set: (mutator) => mutator(state),
          flushRuntimeSave: async () => {},
        };
        const runtime = {
          preflightKeyframeLocalEdit: async () => {
            throw new Error("Runtime request failed (422): invalid_keyframe_local_edit data_base64 raw_provider_response D:\\\\private\\\\secret.png Bearer secret-token");
          },
        };

        await createKeyframeLocalEditDraft(store, runtime, state.nodes.keyframe_unsafe, {
          generatedAt: "2026-07-06T00:00:00.000Z",
          editIntent: "Use data_base64 raw_provider_response D:\\\\private\\\\secret.png Bearer secret-token",
          editScope: { kind: "semantic_region", target_description: "left window light area" },
        });
        process.stdout.write(JSON.stringify(state.nodes.keyframe_unsafe));
        """
    )
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    node = json.loads(completed.stdout)
    preflight = node["params"]["keyframeLocalEditDraft"]["preflight"]
    serialized = json.dumps(node, ensure_ascii=False).lower()

    assert preflight["contract_status"] == "runtime_preflight_rejected"
    assert preflight["execution_status"] == "blocked_invalid_runtime_preflight_request"
    assert preflight["provider_calls_started"] is False
    assert preflight["local_transformation_started"] is False
    assert preflight["generated_media_created"] is False
    assert preflight["preflight_receipt_status"] == "not_issued"
    assert "data_base64" not in serialized
    assert "raw_provider_response" not in serialized
    assert "secret-token" not in serialized
    assert "d:\\\\private" not in serialized
    assert "preflight_token" not in serialized


def test_keyframe_local_edit_draft_blocks_missing_parent_lineage() -> None:
    script = textwrap.dedent(
        """
        import { buildKeyframeLocalEditDraft } from "./apps/studio/src/keyframe-local-edit-contract.js";

        const draft = buildKeyframeLocalEditDraft({ nodes: {}, assets: [] }, {
          id: "keyframe_missing",
          type: "image",
          prompt: "只改灯光",
          params: { nodeRole: "keyframe_generation", uploads: [] },
        }, {
          generatedAt: "2026-07-06T00:00:00.000Z",
          editIntent: "只改灯光",
          editScope: { kind: "semantic_region", target_description: "窗户灯光区域" },
        });
        process.stdout.write(JSON.stringify(draft.preflight));
        """
    )
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    preflight = json.loads(completed.stdout)
    blocker_codes = {blocker["code"] for blocker in preflight["blockers"]}

    assert preflight["contract_status"] == "draft_needs_input"
    assert preflight["execution_status"] == "blocked_missing_required_input"
    assert "missing_parent_keyframe_job" in blocker_codes
    assert "missing_parent_image_asset" in blocker_codes
    assert preflight["provider_calls_started"] is False
    assert preflight["generated_media_created"] is False
