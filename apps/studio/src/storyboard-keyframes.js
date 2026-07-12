import { createNode, connect } from "./nodes.js";
import { graphBoundVisualAssetsForShot } from "./asset-auto-binding-refs.js";
import { sourceEvidenceRefs } from "./generation-preflight-source-evidence.js";
import { structuredShotFromSegment } from "./structured-shot.js";

export function createKeyframeNodesForStoryboard(store, sourceScriptNode) {
  const state = store.get();
  const scriptNode = state.nodes[sourceScriptNode.id] || sourceScriptNode;
  if (!scriptNode) return [];
  const assetNodes = downstreamAssetCardNodes(state, scriptNode.id);
  const fixedAssets = fixedVisualAssetsFromAssetNodes(assetNodes);
  const fixedAssetSourceEvidenceRefs = sourceEvidenceRefs({ included_assets: fixedAssets });
  const productionGraphReview = productionGraphReviewFromScriptNode(scriptNode);
  const candidateImageRefs = candidateAssetImageRefsFromAssetNodes(assetNodes);
  const candidateAssets = candidateAssetPlansFromAssetNodes(assetNodes);
  const missingIds = assetNodes
    .filter((asset) => !(asset.params?.visualAssets || []).some(isFixedVisualAsset))
    .map((asset) => asset.id);
  const structuredShot = scriptNode.params?.structuredShot
    || structuredShotFromSegment(scriptNode.content || scriptNode.prompt || "", Number(scriptNode.params?.scriptSegmentIndex || 1));
  let keyframeNode = existingKeyframeNode(state, scriptNode.id);
  if (!keyframeNode) keyframeNode = createNode(store, "image", scriptNode.x + scriptNode.w + 720, scriptNode.y);
  store.set((s) => {
    const node = s.nodes[keyframeNode.id];
    if (!node) return;
    node.title = `关键帧 · ${scriptNode.title || structuredShot.shot_id || "分镜"}`;
    node.prompt = keyframePrompt(structuredShot, fixedAssets, candidateAssets);
    node.content = "";
    node.status = "empty";
    node.params.nodeRole = "keyframe_generation";
    node.params.structuredShot = structuredShot;
    node.params.visualAssets = fixedAssets;
    node.params.keyframeAssetPlan = {
      status: "draft",
      user_editable: true,
      source: "storyboard_keyframe_asset_plan",
      instruction: "可在生成前手动修订这些资产约束；未固定资产只作为本次关键帧局部参考。",
      assets: candidateAssets,
      updated_at: new Date().toISOString(),
    };
    node.params.keyframeLayer = {
      status: fixedAssets.length ? "ready_with_fixed_assets" : candidateAssets.length ? "ready_with_candidate_assets" : "ready_without_fixed_assets",
      source_script_node_id: scriptNode.id,
      source_asset_card_node_ids: assetNodes.map((asset) => asset.id),
      candidate_asset_card_node_ids: assetNodes.map((asset) => asset.id),
      candidate_image_asset_refs: candidateImageRefs,
      fixed_visual_asset_ids: fixedAssets.map((asset) => asset.asset_id).filter(Boolean),
      fixed_asset_source_evidence_count: fixedAssetSourceEvidenceRefs.length,
      fixed_asset_source_evidence_refs: fixedAssetSourceEvidenceRefs,
      production_graph_review: productionGraphReview,
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
  const add = (visual) => {
    if (!isFixedVisualAsset(visual)) return;
    const assetId = String(visual.asset_id || visual.visual_asset_id || "").trim();
    if (!assetId || seen.has(assetId)) return;
    seen.add(assetId);
    result.push(visual);
  };
  for (const asset of assetNodes) {
    for (const visual of asset.params?.visualAssets || []) {
      add(visual);
    }
    const graph = asset.params?.assetAutoBindingGraph || asset.params?.asset_auto_binding_graph || null;
    const assetRef = asset.params?.asset_prep?.asset_ref || asset.params?.assetCardDraft?.source_asset_ref || {};
    for (const visual of graphBoundVisualAssetsForShot(graph, { asset_refs: [assetRef] })) add(visual);
  }
  return result;
}

function productionGraphReviewFromScriptNode(scriptNode) {
  const breakdown = scriptNode?.params?.storyboardBreakdown || {};
  const graph = breakdown.productionGraph
    || breakdown.production_graph
    || scriptNode?.params?.productionGraph
    || scriptNode?.params?.production_graph
    || null;
  const artifactId = safeToken(
    breakdown.productionGraphArtifactId
    || breakdown.production_graph_artifact_id
    || scriptNode?.params?.productionGraphArtifactId
    || scriptNode?.params?.production_graph_artifact_id
    || "",
  );
  const fixedIds = productionGraphFixedAssetIds(graph);
  const fixedCount = productionGraphFixedAssetCount(graph, fixedIds.length);
  if (!artifactId && !fixedCount) return null;
  return {
    artifact_id: artifactId,
    fixed_asset_reuse_count: fixedCount,
    fixed_visual_asset_ids: fixedIds,
  };
}

function productionGraphFixedAssetCount(graph, fallbackCount) {
  const summaryCount = Number(graph?.summary?.fixed_visual_asset_count);
  if (Number.isFinite(summaryCount) && summaryCount > 0) return Math.min(summaryCount, 99);
  return Math.min(Math.max(Number(fallbackCount) || 0, 0), 99);
}

function productionGraphFixedAssetIds(graph) {
  const seen = new Set();
  const result = [];
  for (const node of Array.isArray(graph?.nodes) ? graph.nodes : []) {
    if (node?.node_type !== "fixed_visual_asset") continue;
    const id = safeToken(node.asset_id || node.visual_asset_id || node.id || "");
    if (!id || seen.has(id)) continue;
    seen.add(id);
    result.push(id);
    if (result.length >= 24) break;
  }
  return result;
}

function candidateAssetImageRefsFromAssetNodes(assetNodes) {
  const seen = new Set();
  const result = [];
  for (const asset of assetNodes) {
    const uploads = Array.isArray(asset.params?.uploads) ? asset.params.uploads : [];
    for (const upload of uploads) {
      const role = String(upload?.role || upload?.source_kind || upload?.sourceKind || "").toLowerCase();
      if (!["character_reference", "scene_reference", "prop_reference", "asset_reference"].includes(role)) continue;
      const assetId = String(upload?.asset_id || upload?.assetId || "").trim();
      if (!assetId || seen.has(assetId)) continue;
      seen.add(assetId);
      result.push(assetId);
    }
  }
  return result.slice(0, 4);
}

function candidateAssetPlansFromAssetNodes(assetNodes) {
  return assetNodes.map((node) => {
    const draft = node.params?.assetCardDraft || node.params?.asset_prep?.asset_ref || {};
    const visuals = Array.isArray(node.params?.visualAssets) ? node.params.visualAssets : [];
    const imageRefs = candidateAssetImageRefsFromAssetNodes([node]);
    return {
      source_node_id: node.id,
      label: cleanText(draft.label || draft.name || draft.asset_id || node.title || "未命名资产", 40),
      asset_type: normalizeAssetType(draft.asset_type || draft.type),
      status: visuals.some(isFixedVisualAsset) ? "fixed" : "candidate",
      signature: cleanText(draft.signature || "", 180),
      feature_summary: featureCardSummary(draft.feature_card),
      evidence_text: cleanText(draft.evidence_text || "", 220),
      image_asset_refs: imageRefs,
    };
  }).filter((asset) => asset.label);
}

function existingKeyframeNode(state, scriptNodeId) {
  return Object.values(state.nodes || {})
    .find((node) => node?.params?.keyframeLayer?.source_script_node_id === scriptNodeId) || null;
}

function keyframePrompt(shot, fixedAssets, candidateAssets) {
  const fixedLines = fixedAssets.map((asset) => {
    const label = asset.label || asset.asset_id;
    const signature = asset.signature ? `：${asset.signature}` : "";
    return `- @${label}${signature}`;
  });
  const candidateLines = candidateAssets.map((asset) => {
    const type = assetTypeLabel(asset.asset_type);
    const refText = asset.image_asset_refs?.length ? `；参考图：已连接 ${asset.image_asset_refs.length} 张` : "";
    const signature = asset.signature ? `：${asset.signature}` : "";
    const features = asset.feature_summary ? `；关键特征：${asset.feature_summary}` : "";
    const evidence = !asset.signature && !asset.feature_summary && asset.evidence_text ? `；依据：${asset.evidence_text}` : "";
    return `- @${asset.label}（${type}，${asset.status === "fixed" ? "已固定" : "候选资产卡"}）${signature}${features}${evidence}${refText}`;
  });
  const assetModeLine = fixedLines.length
    ? "已固定资产（必须保持）："
    : candidateLines.length
      ? "已固定资产：暂无；以下候选资产作为本次关键帧局部参考，不晋升为全局固定资产。"
      : "已固定资产：暂无；将仅根据分镜文本生成。";
  return [
    `根据分镜生成关键帧：${shot.description || shot.source_text || ""}`,
    `镜头：${shot.shot_size || "中景"}；光影：${shot.light_atmosphere || "自然光影"}；运镜参考：${shot.camera_motion || "固定机位"}`,
    assetModeLine,
    ...fixedLines,
    candidateLines.length ? "局部候选资产卡（本次必须参考；生成前可手动修订，未固定不阻断生成）：" : "",
    ...candidateLines,
    "资产一致性：严格保持上述资产的身份、材质/外壳、服装或结构、道具几何、场景布局和参考图关系；只生成当前分镜需要的画面。",
    "禁止新增：除非分镜或资产卡明确要求，不要新增椅子、凳子、篮子、额外家具、突出的屋檐/飞檐、无关道具或新角色。",
    "画面要求：单张关键帧，主体清晰，延续分镜剧情，不添加文字、水印、UI 或边框。",
  ].filter(Boolean).join("\n");
}

function featureCardSummary(featureCard) {
  if (!featureCard || typeof featureCard !== "object") return "";
  const values = [];
  for (const value of Object.values(featureCard)) {
    if (typeof value === "string") values.push(value);
    else if (Array.isArray(value)) values.push(value.filter((item) => typeof item === "string").join("、"));
  }
  return cleanText(values.filter(Boolean).join("；"), 260);
}

function normalizeAssetType(type) {
  const value = String(type || "asset").toLowerCase();
  return ["character", "scene", "prop", "video", "asset"].includes(value) ? value : "asset";
}

function assetTypeLabel(type) {
  if (type === "character") return "角色";
  if (type === "scene") return "场景";
  if (type === "prop") return "道具";
  if (type === "video") return "视频";
  return "资产";
}

function cleanText(value, limit) {
  return String(value || "").replace(/\s+/g, " ").trim().slice(0, limit);
}

function safeToken(value) {
  return String(value || "").replace(/[^a-zA-Z0-9_.:-]+/g, "_").slice(0, 160);
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
