import { showModal, el } from "../overlay.js";
import { visualAssetDefaults } from "./visual-asset-defaults.js";

const CHARACTER_FIELDS = [
  ["identity", "身份", "28 岁左右的女性私家侦探，神情冷静"],
  ["hair", "发型发色", "黑色短发，微卷，右侧别银色发夹"],
  ["face", "面部特征", "瓜子脸，左眉尾一道细疤，黑色眼睛"],
  ["build", "体态身形", "身形瘦削，约 170cm"],
  ["wardrobe", "标志性服装", "红色及膝风衣，内搭黑色高领毛衣"],
  ["palette", "人物配色", "红黑为主，银色点缀"],
  ["demeanor", "气质神态", "寡言，惯于侧目观察"],
];

const SCENE_FIELDS = [
  ["location", "地点定位", "城市边缘的废弃天文观测站内部"],
  ["layout", "空间结构", "入口在东侧，中央是望远镜基座，西墙整面破玻璃窗"],
  ["props", "关键道具", "翻倒的金属椅，墙上褪色的星图，地面积水"],
  ["lighting_mood", "光线基调", "冷月光从西窗斜入，整体青蓝色调"],
  ["palette", "场景配色", "青蓝 + 锈橙"],
  ["time_weather", "时间天气", "深夜，雨后"],
];

const CHARACTER_LOCK_CHIPS = [
  ["保持发型发色", "hair"],
  ["保持标志性服装", "wardrobe"],
  ["保持面部特征", "face"],
  ["不改变体型比例", null],
];

const SCENE_LOCK_CHIPS = [
  ["保持空间布局", "layout"],
  ["保持关键道具", "props"],
  ["保持光线基调", "lighting_mood"],
];

export function openVisualAssetPanel({ store, runtime, node, imageAsset, initialAssetType = "character" }) {
  if (!runtime?.promoteVisualAsset) {
    markNodeError(store, node.id, "运行服务的资产接口不可用，请确认 Runtime Service 已启动。");
    return;
  }
  if (!imageAsset?.asset_id) {
    markNodeError(store, node.id, "当前节点没有可固定的图片，请先上传或生成图片。");
    return;
  }

  let assetType = initialAssetType === "scene" ? "scene" : "character";
  const modal = el("div", "modal-card visual-asset-panel");
  const close = showModal(modal);
  render();

  function render() {
    const fields = assetType === "character" ? CHARACTER_FIELDS : SCENE_FIELDS;
    const lockChips = assetType === "character" ? CHARACTER_LOCK_CHIPS : SCENE_LOCK_CHIPS;
    const previous = collectFieldValues(modal);
    const defaults = visualAssetDefaults(node, imageAsset, assetType);
    modal.innerHTML = `
      <div class="modal-head">
        <div>
          <div class="eyebrow">人工确认</div>
          <h3>固定为${assetType === "character" ? "人物" : "场景"}资产</h3>
        </div>
        <button class="icon-btn" data-action="close" title="关闭">×</button>
      </div>
      <div class="visual-asset-preview">
        ${imageAsset.preview_url ? `<img src="${escapeAttr(imageAsset.preview_url)}" alt="候选资产图">` : ""}
        <div>
          <strong>${escapeHtml(node.title || node.id)}</strong>
          <p>${escapeHtml((node.prompt || node.result || "").slice(0, 160))}</p>
          <small>${escapeHtml(imageAsset.asset_id)}</small>
        </div>
      </div>
      <div class="va-type-row">
        <button class="va-type${assetType === "character" ? " active" : ""}" data-type="character">人物资产</button>
        <button class="va-type${assetType === "scene" ? " active" : ""}" data-type="scene">场景资产</button>
      </div>
      <label class="va-row">名称<input data-field="label" value="${escapeAttr(previous.label || defaults.label || node.title || "")}" placeholder="如：林晚 / 观测站"></label>
      <label class="va-row">一句话签名<input data-field="signature" value="${escapeAttr(previous.signature || defaults.signature || "")}" placeholder="只写最具辨识度的 2-4 个特征，将进入优化提示词"></label>
      <div class="va-section-label">特征卡 <small>逐项填写，生成时全文注入模型；至少填一项</small></div>
      ${fields.map(([key, label, hint]) => `
        <label class="va-row va-feature">${label}<input data-card="${key}" value="${escapeAttr(previous.card?.[key] || defaults.card?.[key] || "")}" placeholder="${escapeAttr(hint)}"></label>
      `).join("")}
      <div class="va-section-label">不可变锁定项 <small>每行一条；生成时强制遵守，可临时解除</small></div>
      <div class="va-lock-chips">
        ${lockChips.map(([label], index) => `<button class="va-chip" data-chip="${index}">+ ${label}</button>`).join("")}
      </div>
      <textarea data-field="negative_locks" rows="3" placeholder="保持黑色短发&#10;保持左眉尾疤痕">${escapeHtml(previous.locks || defaults.locks || "")}</textarea>
      <div class="va-error" data-role="error" hidden></div>
      <div class="modal-actions">
        <button class="ghost-btn" data-action="reject">不采用</button>
        <button class="primary-btn" data-action="fix">确认固定</button>
      </div>
    `;
  }

  modal.addEventListener("click", async (event) => {
    const target = event.target;
    const action = target?.dataset?.action;
    if (action === "close") { close(); return; }
    if (target?.dataset?.type && target.dataset.type !== assetType) {
      assetType = target.dataset.type;
      render();
      return;
    }
    if (target?.dataset?.chip !== undefined && target.dataset.chip !== "") {
      applyLockChip(Number(target.dataset.chip));
      return;
    }
    if (action === "fix" || action === "reject") {
      await submit(action === "fix" ? "fixed" : "rejected");
    }
  });

  function applyLockChip(index) {
    const chips = assetType === "character" ? CHARACTER_LOCK_CHIPS : SCENE_LOCK_CHIPS;
    const [label, fieldKey] = chips[index] || [];
    if (!label) return;
    const fieldValue = fieldKey ? field(modal, fieldKey, "data-card") : "";
    const lockText = fieldValue ? `保持${fieldValue.slice(0, 24)}` : label;
    const textareaEl = modal.querySelector('[data-field="negative_locks"]');
    const current = lines(textareaEl.value);
    if (!current.includes(lockText)) textareaEl.value = [...current, lockText].join("\n");
  }

  async function submit(decision) {
    const values = collectFieldValues(modal);
    const card = compactCard(values.card);
    const signature = decision === "rejected" && !values.signature ? "未通过的候选图" : values.signature;
    const cardOrFallback = decision === "rejected" && !Object.keys(card).length ? { review: "rejected candidate" } : card;
    if (decision === "fixed") {
      if (!values.label) return showError("请填写资产名称。");
      if (!signature) return showError("请填写一句话签名，它会出现在优化提示词里。");
      if (!Object.keys(card).length) return showError("特征卡至少填写一项，生成时模型只认特征卡内容。");
    }
    setBusy(true);
    try {
      await submitVisualAssetReview({
        store, runtime, node, imageAsset, decision,
        label: values.label || node.title || "未命名资产",
        assetType,
        signature,
        featureCard: cardOrFallback,
        negativeLocks: lines(values.locks),
      });
      close();
    } catch (error) {
      showError(`提交失败：${safeError(error)}`);
      setBusy(false);
    }
  }

  function showError(message) {
    const box = modal.querySelector('[data-role="error"]');
    if (!box) return;
    box.hidden = false;
    box.textContent = message;
  }

  function setBusy(busy) {
    for (const btn of modal.querySelectorAll(".modal-actions button")) btn.disabled = busy;
  }
}

function collectFieldValues(root) {
  const card = {};
  for (const input of root.querySelectorAll("[data-card]")) {
    const value = String(input.value || "").trim();
    if (value) card[input.dataset.card] = value;
  }
  return {
    label: field(root, "label"),
    signature: field(root, "signature"),
    locks: String(root.querySelector('[data-field="negative_locks"]')?.value || ""),
    card,
  };
}

function compactCard(card) {
  const result = {};
  for (const [key, value] of Object.entries(card || {})) {
    if (String(value || "").trim()) result[key] = String(value).trim();
  }
  return result;
}

async function submitVisualAssetReview({ store, runtime, node, imageAsset, decision, label, assetType, signature, featureCard, negativeLocks }) {
  const payload = {
    source_image_asset_refs: [imageAsset.asset_id],
    asset_type: assetType,
    label,
    signature,
    feature_card: featureCard,
    negative_locks: negativeLocks,
    source_node_id: node.id,
    review_decision: decision,
    reviewed_at: new Date().toISOString(),
  };
  const response = await runtime.promoteVisualAsset(payload);
  const asset = response?.asset;
  const localAsset = asset?.asset_id ? {
    ...asset,
    asset_type: assetType,
    label,
    signature,
    feature_card: featureCard,
    negative_locks: negativeLocks,
  } : null;
  store.set((s) => {
    const n = s.nodes[node.id];
    if (!n || !localAsset?.asset_id) return;
    n.params.visualAssets = mergeVisualAssets(n.params.visualAssets || [], localAsset);
    n.params.lastVisualAssetWarnings = response?.warnings || [];
    n.result = `${n.result || ""}\n${decision === "fixed" ? "资产已固定；画布撤销(Ctrl+Z)不影响已固定资产" : "候选未采用"}：${localAsset.label}：${localAsset.asset_id}`.trim();
    s.assets.unshift({
      id: store.nextId("asset"),
      kind: "visual_asset",
      title: localAsset.label,
      safe_summary: localAsset.signature,
      thumbnail_ref: localAsset.asset_type,
      source_node_id: n.id,
      asset_status: localAsset.status,
      status: localAsset.status,
      asset_type: localAsset.asset_type,
      asset_id: localAsset.asset_id,
      visual_asset_id: localAsset.asset_id,
      signature: localAsset.signature,
      feature_card: localAsset.feature_card,
      negative_locks: localAsset.negative_locks,
      created_at: new Date().toISOString(),
    });
  });
}

function lines(value) {
  return String(value || "").split(/\r?\n/).map((item) => item.trim()).filter(Boolean);
}

function field(root, name, attr = "data-field") {
  return String(root.querySelector(`[${attr}="${name}"]`)?.value || "").trim();
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

function safeError(error) {
  const message = error instanceof Error ? error.message : String(error || "未知错误");
  return message.replace(/Bearer\s+\S+/gi, "Bearer <redacted>").slice(0, 160);
}

function escapeHtml(value) {
  return String(value || "").replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
}

function escapeAttr(value) {
  return escapeHtml(value).replace(/`/g, "&#96;");
}
