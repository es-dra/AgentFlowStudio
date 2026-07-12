import { createNode, connect } from "./nodes.js";
import { lastImageAsset, mergeImageAssets } from "./node-image-assets.js";
import { VIDEO_RATIOS } from "./presets/specs.js";
import { DEFAULT_KEYFRAME_VIDEO_MOTION, buildKeyframeVideoPrompt } from "./keyframe-video-prompt.js";

export function canContinueKeyframeToVideo(node) {
  return Boolean(isKeyframeLikeNode(node));
}

export function createVideoNodeFromKeyframe(store, keyframeNode) {
  const state = store.get();
  const source = state.nodes?.[keyframeNode?.id] || keyframeNode;
  if (!source || !isKeyframeLikeNode(source)) return null;
  const frameAsset = keyframeFirstFrameAsset(state, source);
  if (!frameAsset?.asset_id) {
    markMissingFirstFrame(store, source.id);
    return null;
  }
  const videoAssetPlan = videoAssetPlanForKeyframe(state, source);

  const video = createNode(
    store,
    "video",
    Number(source.x || 0) + Number(source.w || 280) + 180,
    Number(source.y || 0),
  );
  store.set((s) => {
    const node = s.nodes[video.id];
    if (!node) return;
    node.title = videoTitle(source);
    node.prompt = buildKeyframeVideoPrompt(source, videoAssetPlan, {
      motion: DEFAULT_KEYFRAME_VIDEO_MOTION,
      duration: source.params?.spec?.duration || "5s",
    });
    node.status = "empty";
    node.previewUrl = null;
    node.result = [
      "已从上游关键帧创建图生视频节点。",
      "关键帧图片已设为首帧；视频提示词和视频资产计划已自动生成。",
      "可以直接生成，也可以先微调提示词/视频资产计划后重新生成整段视频。",
      "提示词微调不是局部视频编辑；未点名内容仍可能变化。",
    ].join("\n");
    node.params = {
      ...node.params,
      nodeRole: "video_generation",
      sourceKeyframeNodeId: source.id,
      sourceKeyframeJobId: source.params?.lastKeyframeJobId || null,
      sourceKeyframeAssetId: frameAsset.asset_id,
      assetReferenceMode: source.params?.assetReferenceMode || source.params?.referenceTransformMode || null,
      firstFrameImageAssetId: frameAsset.asset_id,
      firstFramePreviewUrl: frameAsset.preview_url || source.previewUrl || "",
      videoInputSource: {
        source_mode: "upstream_generated_image",
        source_asset_id: frameAsset.asset_id,
        source_node_id: source.id,
        source_job_id: source.params?.lastKeyframeJobId || frameAsset.source_job_id || null,
        role: "first_frame",
      },
      motion: node.params?.motion || DEFAULT_KEYFRAME_VIDEO_MOTION,
      spec: {
        ...(node.params?.spec || {}),
        ratio: supportedVideoRatio(source.params?.spec?.ratio || node.params?.spec?.ratio),
        resolution: node.params?.spec?.resolution || "720P",
        duration: node.params?.spec?.duration || "5s",
        count: 1,
        mode: "图生视频",
      },
      uploads: mergeImageAssets(node.params?.uploads || [], {
        ...frameAsset,
        role: "first_frame",
        source_role: frameAsset.source_role || frameAsset.role || "generated_keyframe_reference",
      }).slice(-4),
      videoAssetPlan,
      videoAssetRecognition: {
        status: "pending_video_generation",
        source: "generated_video",
        source_keyframe_node_id: source.id,
        source_first_frame_image_asset_id: frameAsset.asset_id,
        assets: videoAssetPlan.assets,
      },
    };
  });
  connect(store, source.id, video.id);
  return store.get().nodes[video.id] || video;
}

export function keyframeFirstFrameAsset(state, node) {
  return normalizeImageAssetRef(lastImageAsset(node), node)
    || latestReadyImageAssetFromNode(state, node?.id)
    || null;
}

function isKeyframeLikeNode(node) {
  if (node?.type !== "image") return false;
  if (node.params?.nodeRole === "asset_card_draft" || node.params?.assetCardDraft) return false;
  const searchable = `${node.title || ""}\n${node.prompt || ""}\n${node.content || ""}`;
  return node.params?.nodeRole === "keyframe_generation"
    || Boolean(node.params?.keyframeLayer)
    || Boolean(node.params?.lastKeyframeJobId)
    || Boolean(node.params?.structuredShot)
    || /关键帧|keyframe/i.test(searchable);
}

function latestReadyImageAssetFromNode(state, sourceNodeId) {
  if (!sourceNodeId) return null;
  const assets = (Array.isArray(state.assets) ? state.assets : [])
    .filter((asset) =>
      asset?.source_node_id === sourceNodeId
      && asset?.asset_id
      && (!asset.status || asset.status === "ready")
      && ["keyframe", "image_reference"].includes(asset.kind),
    )
    .sort((a, b) => String(b.created_at || "").localeCompare(String(a.created_at || "")));
  return normalizeImageAssetRef(assets[0], state.nodes?.[sourceNodeId]);
}

function normalizeImageAssetRef(asset, node) {
  const assetId = String(asset?.asset_id || asset?.assetId || "").trim();
  if (!assetId) return null;
  return {
    ...asset,
    asset_id: assetId,
    filename: asset.filename || asset.title || `${assetId}.png`,
    preview_url: asset.preview_url || asset.previewUrl || node?.previewUrl || "",
    width: asset.width || null,
    height: asset.height || null,
    aspect_ratio: asset.aspect_ratio || asset.aspectRatio || node?.params?.previewAspectRatio || null,
  };
}

function supportedVideoRatio(ratio) {
  const value = String(ratio || "16:9").trim();
  return VIDEO_RATIOS.includes(value) ? value : "16:9";
}

function videoTitle(source) {
  const suffix = String(source.title || source.id || "关键帧")
    .replace(/^关键帧\s*[·.-]\s*/u, "")
    .slice(0, 36);
  return `视频 · ${suffix}`;
}

function videoAssetPlanForKeyframe(state, source) {
  const seen = new Set();
  const assets = [];

  const addAsset = (asset, sourceLabel, sourceNode = null) => {
    const normalized = normalizeVideoAsset(asset, sourceLabel, sourceNode);
    if (!normalized) return;
    const key = normalized.label.toLowerCase();
    if (seen.has(key)) return;
    seen.add(key);
    assets.push(normalized);
  };

  for (const asset of safeArray(source.params?.visualAssets)) {
    addAsset(asset, "keyframe_visual_asset", source);
  }
  for (const asset of safeArray(source.params?.lastContextBundle?.included_assets)) {
    addAsset(asset, "context_bundle", source);
  }
  for (const node of connectedAssetNodes(state, source.id)) {
    if (node.params?.assetCardDraft) {
      addAsset({
        ...node.params.assetCardDraft,
        image_asset_refs: referenceImageRefsFromNode(node),
      }, "connected_asset_card", node);
    }
    for (const asset of safeArray(node.params?.visualAssets)) {
      addAsset(asset, "connected_visual_asset", node);
    }
  }
  for (const label of mentionedAssetLabels(source)) {
    addAsset({ label, asset_type: "asset", signature: "来自关键帧提示词的资产引用" }, "keyframe_prompt", source);
  }

  return {
    status: "draft",
    source: "keyframe_to_video_auto_plan",
    source_keyframe_node_id: source.id,
    user_editable: true,
    generation_ready: true,
    assets: assets.slice(0, 12),
  };
}

function connectedAssetNodes(state, sourceNodeId) {
  return Object.values(state.edges || {})
    .filter((edge) => edge?.to === sourceNodeId)
    .map((edge) => state.nodes?.[edge.from])
    .filter((node) => node?.params?.assetCardDraft || node?.params?.nodeRole === "asset_card_draft");
}

function normalizeVideoAsset(asset, sourceLabel, sourceNode) {
  const label = cleanAssetLabel(asset?.label || asset?.name || asset?.title || asset?.asset_label);
  if (!label) return null;
  const imageRefs = imageRefsFromAsset(asset);
  return {
    label,
    asset_type: normalizeAssetType(asset?.asset_type || asset?.type || asset?.category),
    status: asset?.status || asset?.fix_status || asset?.review_decision || "candidate",
    signature: String(asset?.signature || asset?.one_line || asset?.description || "").trim(),
    source: sourceLabel,
    source_node_id: sourceNode?.id || null,
    source_asset_id: asset?.asset_id || asset?.id || null,
    image_asset_refs: imageRefs,
    video_role: "continuity_lock",
    reference_policy: imageRefs.length ? "reference_images_available" : "prompt_only",
  };
}

function mentionedAssetLabels(source) {
  const text = `${source.prompt || ""}\n${source.result || ""}`;
  const labels = [];
  const re = /@([^\s@，。；;、,：:\)\]】]+)/gu;
  let match = re.exec(text);
  while (match) {
    const label = cleanAssetLabel(match[1]);
    if (label) labels.push(label);
    match = re.exec(text);
  }
  return labels;
}

function imageRefsFromAsset(asset) {
  const refs = [
    ...safeArray(asset?.image_asset_refs),
    ...safeArray(asset?.source_image_asset_refs),
    ...safeArray(asset?.reference_image_assets),
  ];
  if (asset?.image_asset_id) refs.push({ asset_id: asset.image_asset_id });
  if (asset?.reference_image_asset_id) refs.push({ asset_id: asset.reference_image_asset_id });
  return refs
    .map((ref) => typeof ref === "string" ? { asset_id: ref } : ref)
    .filter((ref) => ref?.asset_id);
}

function referenceImageRefsFromNode(node) {
  return safeArray(node.params?.uploads)
    .filter((upload) => {
      const role = String(upload?.role || "").toLowerCase();
      return upload?.asset_id && [
        "asset_reference",
        "character_reference",
        "scene_reference",
        "prop_reference",
        "fixed_asset_reference",
      ].includes(role);
    })
    .map((upload) => normalizeImageAssetRef(upload, node))
    .filter(Boolean);
}

function normalizeAssetType(type) {
  const value = String(type || "").trim().toLowerCase();
  if (["character", "role", "person", "角色"].includes(value)) return "character";
  if (["scene", "location", "environment", "场景"].includes(value)) return "scene";
  if (["prop", "object", "item", "道具"].includes(value)) return "prop";
  return "asset";
}

function cleanAssetLabel(label) {
  return String(label || "")
    .replace(/^[@#]+/u, "")
    .replace(/[（(【\[].*$/u, "")
    .replace(/^[角色场景道具资产]\s*[·:：-]\s*/u, "")
    .trim();
}

function safeArray(value) {
  return Array.isArray(value) ? value : [];
}

function markMissingFirstFrame(store, nodeId) {
  store.set((s) => {
    const node = s.nodes?.[nodeId];
    if (!node) return;
    node.result = [
      node.result || "",
      "无法接续视频节点：当前关键帧缺少可作为首帧的图像资产。请先重新生成关键帧，或上传/替换一张可用参考图。",
    ].filter(Boolean).join("\n");
  });
}
