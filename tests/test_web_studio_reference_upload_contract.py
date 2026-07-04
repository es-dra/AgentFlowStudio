from __future__ import annotations

import json
import subprocess
import textwrap


def _run_node(script: str) -> dict:
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
    )
    return json.loads(completed.stdout)


def test_reference_upload_actual_path_preserves_node_target_and_user_intent() -> None:
    payload = _run_node(
        textwrap.dedent(
            r'''
            import { buildOptimizationRequest } from "./apps/studio/src/optimizer-contract.js";
            import { uploadSelectedImage } from "./apps/studio/src/node-upload-actions.js";

            globalThis.FileReader = class {
              readAsDataURL(file) {
                this.result = `data:${file.type || "image/png"};base64,QUJD`;
                this.onload?.();
              }
            };

            const state = {
              nodes: {
                image_1: {
                  id: "image_1",
                  type: "image",
                  title: "Loose reference",
                  prompt: "Use this as a visual mood reference",
                  params: {},
                },
                video_1: {
                  id: "video_1",
                  type: "video",
                  title: "Opening shot",
                  prompt: "Animate the opening shot",
                  params: { referenceIntent: "Use as opening first frame" },
                },
                keyframe_1: {
                  id: "keyframe_1",
                  type: "image",
                  title: "Shot 03 keyframe",
                  prompt: "Match pose and camera angle",
                  params: { nodeRole: "keyframe_generation" },
                },
                asset_card_1: {
                  id: "asset_card_1",
                  type: "image",
                  title: "Hero asset draft",
                  prompt: "Preserve helmet silhouette",
                  params: { nodeRole: "asset_card_draft", assetCardDraft: { label: "Hero", asset_type: "character" } },
                },
              },
              edges: {},
              assets: [],
            };

            let assetSeq = 0;
            const uploadRequests = [];
            const store = {
              get: () => state,
              nextId: (prefix) => `${prefix}_${++assetSeq}`,
              set: (mutator) => mutator(state),
              flushRuntimeSave: async () => {},
            };
            const runtime = {
              uploadImageAsset: async (request) => {
                uploadRequests.push(request);
                return {
                  asset: {
                    asset_id: `img_${request.node_id}`,
                    preview_url: `/projects/p/image-assets/img_${request.node_id}/preview`,
                    width: 1280,
                    height: 720,
                    mime_type: request.mime_type,
                  },
                };
              },
            };
            const png = { name: "reference.png", type: "image/png" };

            await uploadSelectedImage(store, runtime, "image_1", png);
            await uploadSelectedImage(store, runtime, "video_1", png);
            await uploadSelectedImage(store, runtime, "keyframe_1", png);
            await uploadSelectedImage(store, runtime, "asset_card_1", png);

            const videoOptimization = buildOptimizationRequest(state, state.nodes.video_1);
            process.stdout.write(JSON.stringify({
              uploadRequests,
              nodes: state.nodes,
              assets: state.assets,
              videoOptimization,
            }));
            '''
        )
    )

    requests = {item["node_id"]: item for item in payload["uploadRequests"]}
    nodes = payload["nodes"]

    assert requests["image_1"]["role"] == "reference_image"
    assert requests["image_1"]["reference_target"] == "image_reference"
    assert requests["image_1"]["user_intent"] == "Use this as a visual mood reference"
    assert nodes["image_1"]["params"]["uploads"][0]["reference_target"] == "image_reference"
    assert nodes["image_1"]["params"]["uploads"][0]["user_intent"] == "Use this as a visual mood reference"

    assert requests["video_1"]["role"] == "first_frame"
    assert requests["video_1"]["reference_target"] == "video_first_frame"
    assert requests["video_1"]["user_intent"] == "Use as opening first frame"
    assert nodes["video_1"]["params"]["firstFrameImageAssetId"] == "img_video_1"
    assert nodes["video_1"]["params"]["videoInputSource"]["source_mode"] == "uploaded_image"
    assert nodes["video_1"]["params"]["videoInputSource"]["user_intent"] == "Use as opening first frame"

    assert requests["keyframe_1"]["role"] == "reference_image"
    assert requests["keyframe_1"]["reference_target"] == "keyframe_generation"
    assert nodes["keyframe_1"]["params"]["uploads"][0]["reference_target"] == "keyframe_generation"

    assert requests["asset_card_1"]["role"] == "asset_reference"
    assert requests["asset_card_1"]["reference_target"] == "asset_card_draft"
    assert nodes["asset_card_1"]["params"]["uploads"][0]["role"] == "asset_reference"
    assert nodes["asset_card_1"]["params"]["uploads"][0]["reference_target"] == "asset_card_draft"

    uploaded_images = payload["videoOptimization"]["node_parameters"]["uploaded_images"]
    assert uploaded_images[0]["reference_target"] == "video_first_frame"
    assert uploaded_images[0]["user_intent"] == "Use as opening first frame"
    assert uploaded_images[0]["media_kind"] == "image"
