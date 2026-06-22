import { createNode, connect } from "./nodes.js";
import { structuredShotFromSegment } from "./structured-shot.js";

export function createKeyframeNodesForStoryboard(store, sourceScriptNode) {
  const state = store.get();
  const scriptNode = state.nodes[sourceScriptNode.id] || sourceScriptNode;
  if (!scriptNode) return [];
  const assetNodes = downstreamAssetCardNodes(state, scriptNode.id);
  const fixedAssets = fixedVisualAssetsFromAssetNodes(assetNodes);
  const missingIds = assetNodes
    .filter((asset) => !(asset.params?.visualAssets || []).some(isFixedVisualAsset))
    .map((asset) => asset.id);
  const missingAssets = assetNodes
    .filter((asset) => missingIds.includes(asset.id))
    .map((asset) => asset.params?.assetCardDraft || asset.params?.asset_prep?.asset_ref || null)
    .filter(Boolean);
  const structuredShot = scriptNode.params?.structuredShot
    || structuredShotFromSegment(scriptNode.content || scriptNode.prompt || "", Number(scriptNode.params?.scriptSegmentIndex || 1));
  let keyframeNode = existingKeyframeNode(state, scriptNode.id);
  if (!keyframeNode) keyframeNode = createNode(store, "image", scriptNode.x + scriptNode.w + 720, scriptNode.y);
  store.set((s) => {
    const node = s.nodes[keyframeNode.id];
    if (!node) return;
    node.title = `关键帧 · ${scriptNode.title || structuredShot.shot_id || "分镜"}`;
    node.prompt = keyframePrompt(structuredShot, fixedAssets, missingAssets);
    node.content = "";
    node.status = "empty";
    node.params.nodeRole = "keyframe_generation";
    node.params.structuredShot = structuredShot;
    node.params.visualAssets = fixedAssets;
    node.params.keyframeLayer = {
      status: fixedAssets.length ? "ready_with_fixed_assets" : "ready_without_fixed_assets",
      source_script_node_id: scriptNode.id,
      source_asset_card_node_ids: assetNodes.map((asset) => asset.id),
      candidate_asset_card_node_ids: assetNodes.map((asset) => asset.id),
      fixed_visual_asset_ids: fixedAssets.map((asset) => asset.asset_id).filter(Boolean),
      missing_asset_card_node_ids: missingIds,
      unfixed_candidate_asset_card_node_ids: missingIds,
      updated_at: new Date().toISOString(),
    };
  });
  connect(store, scriptNode.id, keyframeNode.id);
  for (const asset of assetNodes) connect(store, asset.id, keyframeNode.id);
  return [keyframeNode.id];
}

function downstreamAssetCardNodes(state, scriptNodeId) {
  const downstreamIds = new Set(
    Object.values(state.edges || {})
      .filter((edge) => edge.from === scriptNodeId)
      .map((edge) => edge.to),
  );
  return Object.values(state.nodes || {})
    .filter((node) => downstreamIds.has(node.id) && isAssetCardNode(node));
}

function fixedVisualAssetsFromAssetNodes(assetNodes) {
  const seen = new Set();
  const result = [];
  for (const asset of assetNodes) {
    for (const visual of asset.params?.visualAssets || []) {
      if (!isFixedVisualAsset(visual)) continue;
      const assetId = String(visual.asset_id || visual.visual_asset_id || "").trim();
      if (!assetId || seen.has(assetId)) continue;
      seen.add(assetId);
      result.push(visual);
    }
  }
  return result;
}

function existingKeyframeNode(state, scriptNodeId) {
  return Object.values(state.nodes || {})
    .find((node) => node?.params?.keyframeLayer?.source_script_node_id === scriptNodeId) || null;
}

function keyframePrompt(shot, fixedAssets, missingAssets) {
  const fixedLines = fixedAssets.map((asset) => {
    const label = asset.label || asset.asset_id;
    const signature = asset.signature ? `：${asset.signature}` : "";
    return `- @${label}${signature}`;
  });
  const missingLines = missingAssets.map((asset) => `- @${asset.label || asset.asset_id || "未命名资产"}（候选资产卡，未固定时仅供审查，不作为参考图注入）`);
  return [
    `根据分镜生成关键帧：${shot.description || shot.source_text || ""}`,
    `镜头：${shot.shot_size || "中景"}；光影：${shot.light_atmosphere || "自然光影"}；运镜参考：${shot.camera_motion || "固定机位"}`,
    fixedLines.length ? "已固定资产（必须保持）：" : "",
    ...fixedLines,
    fixedLines.length ? "" : "已固定资产：暂无；将仅根据分镜文本生成。",
    missingLines.length ? "候选资产卡（可稍后固定；未固定不阻断关键帧生成）：" : "",
    ...missingLines,
    "画面要求：单张关键帧，主体清晰，延续分镜剧情，不添加文字、水印、UI 或边框。",
  ].filter(Boolean).join("\n");
}

function isFixedVisualAsset(asset) {
  return ["fixed", "ready"].includes(String(asset?.status || ""));
}

function isAssetCardNode(node) {
  return Boolean(
    node?.params?.assetCardDraft
    || node?.params?.nodeRole === "asset_card_draft"
    || node?.params?.asset_prep?.source_script_node_id,
  );
}
