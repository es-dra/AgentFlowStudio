import { showPopover, el } from "../overlay.js";
import { imageAssetFromVisualAsset, lastImageAsset } from "../node-image-assets.js";
import { openVisualAssetPanel } from "./visual-asset-panel.js";

export function openAssetDetailPopover(store, runtime, assetRef, anchor) {
  const assetId = assetIdFromRef(assetRef);
  const localAsset = resolveAsset(store.get(), assetRef) || (typeof assetRef === "object" ? assetRef : null);
  const visualAssetId = visualAssetIdFromRef(assetRef) || visualAssetIdFromRef(localAsset);
  const pop = el("div", "asset-detail-popover");
  renderAssetDetail(pop, store, runtime, localAsset, assetId, visualAssetId);
  showPopover(anchor, pop, { place: "bottom" });
  if (!visualAssetId || !runtime?.getVisualAsset) return;
  runtime.getVisualAsset(visualAssetId)
    .then((payload) => {
      const detail = payload?.asset || null;
      if (!detail) return;
      renderAssetDetail(pop, store, runtime, { ...localAsset, ...detail }, assetId, visualAssetId);
    })
    .catch(() => {
      if (!localAsset) renderAssetDetail(pop, store, runtime, null, assetId, visualAssetId);
    });
}

function renderAssetDetail(pop, store, runtime, asset, assetId, visualAssetId = "") {
  pop.replaceChildren();
  if (!asset) {
    pop.appendChild(el("div", "asset-detail-empty", "未找到资产详情"));
    return;
  }
  pop.appendChild(el("div", "asset-detail-title", asset.label || asset.title || asset.asset_id || assetId || "未命名资产"));
  pop.appendChild(detailRow("状态", statusLabel(asset)));
  pop.appendChild(detailRow("类型", assetTypeLabel(asset)));
  pop.appendChild(detailRow("签名", asset.signature || asset.safe_summary || "未记录"));
  pop.appendChild(detailList("特征卡", featureCardRows(asset.feature_card)));
  pop.appendChild(detailList("锁定项", Array.isArray(asset.negative_locks) ? asset.negative_locks : []));
  pop.appendChild(detailRow("来源节点", asset.source_node_id || "未记录"));
  if (asset.disabled_reason) pop.appendChild(detailRow("本次携带", asset.disabled_reason));
  const actions = el("div", "asset-detail-actions");
  const selectedId = store.get().selection.nodeIds[0];
  if (selectedId && visualAssetId) {
    if (runtime?.promoteVisualAsset) {
      actions.appendChild(actionButton("调整资产", () => openExistingAssetPanel(store, runtime, asset, visualAssetId)));
    }
    if (isFixedAsset(asset) && runtime?.retireVisualAsset) {
      actions.appendChild(actionButton("取消固定", () => cancelFixedAsset(store, runtime, visualAssetId)));
    }
    actions.appendChild(actionButton("从当前节点移除", () => removeAssetFromSelectedNode(store, visualAssetId)));
    actions.appendChild(actionButton("本次不携带", () => excludeAssetForNextRun(store, visualAssetId)));
  }
  if (actions.childNodes.length) pop.appendChild(actions);
}

function resolveAsset(state, ref) {
  const assetId = assetIdFromRef(ref);
  if (!assetId) return null;
  for (const node of Object.values(state.nodes || {})) {
    for (const asset of node.params?.visualAssets || []) {
      if (assetIdFromRef(asset) === assetId) return asset;
    }
  }
  return (state.assets || []).find((asset) => assetIdFromRef(asset) === assetId) || null;
}

function assetIdFromRef(ref) {
  return String(ref?.asset_id || ref?.visual_asset_id || ref?.assetId || ref || "").trim();
}

function visualAssetIdFromRef(ref) {
  if (!ref || typeof ref !== "object") return "";
  if (ref.visual_asset_id) return String(ref.visual_asset_id).trim();
  const kind = String(ref.kind || "").trim();
  if (["character_asset", "scene_asset", "visual_asset"].includes(kind) && ref.asset_id) return String(ref.asset_id).trim();
  if (ref.asset_type && ref.asset_id) return String(ref.asset_id).trim();
  return "";
}

function actionButton(label, onClick) {
  const button = el("button", "asset-detail-action", label);
  button.addEventListener("click", onClick);
  return button;
}

function openExistingAssetPanel(store, runtime, asset, visualAssetId) {
  const state = store.get();
  const node = nodeForAsset(state, asset) || state.nodes[state.selection.nodeIds[0]];
  if (!node) return;
  openVisualAssetPanel({
    store,
    runtime,
    node,
    imageAsset: imageAssetFromVisualAsset(asset) || lastImageAsset(node),
    initialAssetType: ["character", "scene", "prop"].includes(String(asset?.asset_type || "")) ? asset.asset_type : "character",
    existingAsset: { ...asset, asset_id: visualAssetId || asset?.asset_id },
  });
}

function cancelFixedAsset(store, runtime, visualAssetId) {
  if (!visualAssetId || !runtime?.retireVisualAsset) return;
  runtime.retireVisualAsset(visualAssetId, {
    reason: "user_cancelled_fixed_asset",
    retired_at: new Date().toISOString(),
  })
    .then((payload) => {
      applyRetiredVisualAssetToStore(store, payload?.asset || { asset_id: visualAssetId, status: "retired" });
    })
    .catch((error) => {
      console.warn("cancel fixed asset failed", error);
    });
}

function applyRetiredVisualAssetToStore(store, retiredAsset) {
  const retiredId = assetIdFromRef(retiredAsset);
  if (!retiredId) return;
  store.set((s) => {
    s.assets = (s.assets || []).map((asset) => (
      assetIdFromRef(asset) === retiredId
        ? { ...asset, ...retiredAsset, status: "retired", asset_status: "retired" }
        : asset
    ));
    for (const node of Object.values(s.nodes || {})) {
      if (!Array.isArray(node.params?.visualAssets)) continue;
      node.params.visualAssets = node.params.visualAssets.map((asset) => (
        assetIdFromRef(asset) === retiredId
          ? {
            ...asset,
            ...retiredAsset,
            status: "retired",
            asset_status: "retired",
            runtime_status: "excluded",
            disabled_reason: "已取消固定，本次不携带",
          }
          : asset
      ));
    }
  });
}

function nodeForAsset(state, asset) {
  const sourceId = String(asset?.source_node_id || "").trim();
  if (sourceId && state.nodes[sourceId]) return state.nodes[sourceId];
  const assetId = assetIdFromRef(asset);
  if (!assetId) return null;
  return Object.values(state.nodes || {}).find((node) => (
    Array.isArray(node.params?.visualAssets)
    && node.params.visualAssets.some((item) => assetIdFromRef(item) === assetId)
  )) || null;
}

function removeAssetFromSelectedNode(store, assetId) {
  store.set((s) => {
    const node = s.nodes[s.selection.nodeIds[0]];
    if (!node || !Array.isArray(node.params?.visualAssets)) return;
    node.params.visualAssets = node.params.visualAssets.filter((item) => assetIdFromRef(item) !== assetId);
  });
}

function excludeAssetForNextRun(store, assetId) {
  store.set((s) => {
    const node = s.nodes[s.selection.nodeIds[0]];
    if (!node) return;
    const current = Array.isArray(node.params.temporaryAssetExclusions) ? node.params.temporaryAssetExclusions : [];
    if (current.some((item) => assetIdFromRef(item) === assetId)) return;
    node.params.temporaryAssetExclusions = [
      ...current,
      { asset_id: assetId, reason: "user_excluded_from_asset_detail_popover" },
    ];
  }, { history: false });
}

function detailRow(label, value) {
  const row = el("div", "asset-detail-row");
  row.appendChild(el("span", "asset-detail-label", label));
  row.appendChild(el("span", "asset-detail-value", String(value || "未记录")));
  return row;
}

function detailList(label, items) {
  const wrap = el("div", "asset-detail-block");
  wrap.appendChild(el("div", "asset-detail-label", label));
  if (!items.length) {
    wrap.appendChild(el("div", "asset-detail-value muted", "未记录"));
    return wrap;
  }
  const list = el("ul", "asset-detail-list");
  for (const item of items) list.appendChild(el("li", "", item));
  wrap.appendChild(list);
  return wrap;
}

function featureCardRows(card) {
  if (!card || typeof card !== "object") return [];
  return Object.entries(card)
    .filter(([, value]) => String(value || "").trim())
    .map(([key, value]) => `${fieldLabel(key)}：${value}`);
}

function fieldLabel(key) {
  return {
    identity: "身份",
    hair: "发型/毛发/颜色",
    face: "面部/头部特征",
    build: "体态身形",
    wardrobe: "服装/饰品/外观",
    palette: "配色",
    demeanor: "气质神态",
    location: "地点定位",
    layout: "空间结构",
    props: "关键道具",
    lighting_mood: "光线基调",
    time_weather: "时间天气",
  }[key] || key;
}

function statusLabel(asset) {
  const status = asset.runtime_status === "excluded" ? "excluded" : asset.status || asset.asset_status || "fixed";
  return {
    fixed: "已固定",
    ready: "可用",
    rejected: "未采用",
    retired: "已退役",
    excluded: "已失效，本次未携带",
  }[status] || status;
}

function assetTypeLabel(asset) {
  if (asset.asset_type === "scene") return "场景资产";
  if (asset.asset_type === "character") return "角色资产";
  if (asset.asset_type === "prop") return "道具资产";
  if (asset.kind === "image_reference" || asset.role === "reference_image") return "参考图片";
  return "显性资产";
}

function isFixedAsset(asset) {
  return ["fixed", "ready", ""].includes(String(asset?.status || asset?.asset_status || ""));
}
