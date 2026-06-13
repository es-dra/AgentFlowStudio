import { showPopover, el } from "../overlay.js";

export function openAssetDetailPopover(store, runtime, assetRef, anchor) {
  const assetId = assetIdFromRef(assetRef);
  const localAsset = resolveAsset(store.get(), assetRef);
  const pop = el("div", "asset-detail-popover");
  renderAssetDetail(pop, store, localAsset, assetId);
  showPopover(anchor, pop, { place: "bottom" });
  if (!assetId || !runtime?.getVisualAsset) return;
  runtime.getVisualAsset(assetId)
    .then((payload) => {
      const detail = payload?.asset || null;
      if (!detail) return;
      renderAssetDetail(pop, store, { ...localAsset, ...detail }, assetId);
    })
    .catch(() => {
      if (!localAsset) renderAssetDetail(pop, store, null, assetId);
    });
}

function renderAssetDetail(pop, store, asset, assetId) {
  pop.replaceChildren();
  if (!asset) {
    pop.appendChild(el("div", "asset-detail-empty", "未找到资产详情"));
    return;
  }
  pop.appendChild(el("div", "asset-detail-title", asset.label || asset.title || asset.asset_id || assetId || "未命名资产"));
  pop.appendChild(detailRow("状态", statusLabel(asset)));
  pop.appendChild(detailRow("类型", asset.asset_type === "scene" ? "场景资产" : asset.asset_type === "character" ? "人物资产" : "显性资产"));
  pop.appendChild(detailRow("签名", asset.signature || asset.safe_summary || "未记录"));
  pop.appendChild(detailList("特征卡", featureCardRows(asset.feature_card)));
  pop.appendChild(detailList("锁定项", Array.isArray(asset.negative_locks) ? asset.negative_locks : []));
  pop.appendChild(detailRow("来源节点", asset.source_node_id || "未记录"));
  if (asset.disabled_reason) pop.appendChild(detailRow("本次携带", asset.disabled_reason));
  const actions = el("div", "asset-detail-actions");
  const selectedId = store.get().selection.nodeIds[0];
  if (selectedId && assetId) {
    actions.appendChild(actionButton("从当前节点移除", () => removeAssetFromSelectedNode(store, assetId)));
    actions.appendChild(actionButton("本次不携带", () => excludeAssetForNextRun(store, assetId)));
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

function actionButton(label, onClick) {
  const button = el("button", "asset-detail-action", label);
  button.addEventListener("click", onClick);
  return button;
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
    hair: "发型发色",
    face: "面部特征",
    build: "体态身形",
    wardrobe: "标志性服装",
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
    rejected: "未采用",
    retired: "已退役",
    excluded: "已失效，本次未携带",
  }[status] || status;
}
