import { showModal, el } from "../overlay.js";

export function openVisualAssetPanel({ store, runtime, node, imageAsset }) {
  if (!runtime?.promoteVisualAsset) {
    markNodeError(store, node.id, "Runtime visual asset API is not available.");
    return;
  }
  if (!imageAsset?.asset_id) {
    markNodeError(store, node.id, "No image asset is available to fix.");
    return;
  }
  const modal = el("div", "modal-card visual-asset-panel");
  modal.innerHTML = `
    <div class="modal-head">
      <div>
        <div class="eyebrow">asset_fix</div>
        <h3>固定为资产</h3>
      </div>
      <button class="icon-btn" data-action="close" title="Close">×</button>
    </div>
    <div class="visual-asset-preview">
      ${imageAsset.preview_url ? `<img src="${escapeAttr(imageAsset.preview_url)}" alt="candidate asset">` : ""}
      <div>
        <strong>${escapeHtml(node.title || node.id)}</strong>
        <p>${escapeHtml((node.prompt || node.result || "").slice(0, 160))}</p>
        <small>${escapeHtml(imageAsset.asset_id)}</small>
      </div>
    </div>
    <label>类型<select data-field="asset_type"><option value="character">character</option><option value="scene">scene</option></select></label>
    <label>Label<input data-field="label" value="${escapeAttr(node.title || "Asset")}"></label>
    <label>Signature<input data-field="signature" placeholder="典型特征，一句话"></label>
    <label>Feature card<textarea data-field="feature_card" rows="4" placeholder="appearance: black short hair&#10;wardrobe: red trench coat"></textarea></label>
    <label>Negative locks<textarea data-field="negative_locks" rows="3" placeholder="keep black short hair&#10;do not remove brow scar"></textarea></label>
    <div class="modal-actions">
      <button class="ghost-btn" data-action="reject">拒绝</button>
      <button class="primary-btn" data-action="fix">固定</button>
    </div>
  `;
  const close = showModal(modal);
  modal.addEventListener("click", async (event) => {
    const action = event.target?.dataset?.action;
    if (action === "close") close();
    if (action === "fix" || action === "reject") {
      await submitVisualAssetReview({ store, runtime, node, imageAsset, modal, decision: action === "fix" ? "fixed" : "rejected" });
      close();
    }
  });
}

async function submitVisualAssetReview({ store, runtime, node, imageAsset, modal, decision }) {
  const payload = {
    source_image_asset_refs: [imageAsset.asset_id],
    asset_type: field(modal, "asset_type") || "character",
    label: field(modal, "label"),
    signature: field(modal, "signature"),
    feature_card: featureCard(field(modal, "feature_card")),
    negative_locks: lines(field(modal, "negative_locks")),
    source_node_id: node.id,
    review_decision: decision,
    reviewed_at: new Date().toISOString(),
  };
  const response = await runtime.promoteVisualAsset(payload);
  const asset = response?.asset;
  store.set((s) => {
    const n = s.nodes[node.id];
    if (!n || !asset?.asset_id) return;
    n.params.visualAssets = mergeVisualAssets(n.params.visualAssets || [], asset);
    n.params.lastVisualAssetWarnings = response?.warnings || [];
    n.result = `${n.result || ""}\nVisual asset ${decision}: ${asset.label} (${asset.asset_id})`.trim();
    s.assets.unshift({
      id: store.nextId("asset"),
      kind: "visual_asset",
      title: asset.label,
      safe_summary: asset.signature,
      thumbnail_ref: asset.asset_type,
      source_node_id: n.id,
      status: asset.status,
      asset_id: asset.asset_id,
      visual_asset_id: asset.asset_id,
      created_at: new Date().toISOString(),
    });
  });
}

function featureCard(value) {
  const entries = lines(value);
  const card = {};
  for (const item of entries) {
    const [key, ...rest] = item.split(":");
    const cleanKey = String(key || "").trim();
    const cleanValue = rest.join(":").trim() || item;
    if (cleanKey) card[cleanKey] = cleanValue;
  }
  return card;
}

function lines(value) {
  return String(value || "").split(/\r?\n/).map((item) => item.trim()).filter(Boolean);
}

function field(root, name) {
  return String(root.querySelector(`[data-field="${name}"]`)?.value || "").trim();
}

function mergeVisualAssets(existing, asset) {
  const assetId = String(asset?.asset_id || "").trim();
  if (!assetId) return existing;
  return [...existing.filter((item) => String(item?.asset_id || "") !== assetId), asset].slice(-8);
}

function markNodeError(store, nodeId, message) {
  store.set((s) => {
    const node = s.nodes[nodeId];
    if (!node) return;
    node.status = "error";
    node.result = message;
  });
}

function escapeHtml(value) {
  return String(value || "").replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
}

function escapeAttr(value) {
  return escapeHtml(value).replace(/`/g, "&#96;");
}
