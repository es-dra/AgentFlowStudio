import { showModal, el } from "../overlay.js";
import { visualAssetDefaults } from "./visual-asset-defaults.js";
import { lockChipsForAssetType, renderVisualAssetPanel } from "./visual-asset-panel-render.js";
import { formatRuntimeError } from "../runtime-error-utils.js";
import { buildVisualAssetPromotionPayload } from "./visual-asset-promotion-request.js";

export function openVisualAssetPanel({ store, runtime, node, imageAsset, initialAssetType = "character", existingAsset = null }) {
  if (!runtime?.promoteVisualAsset) {
    markNodeError(store, node.id, "资产确认服务不可用，请确认本地创作服务已启动。");
    return;
  }
  if (!imageAsset?.asset_id) {
    markNodeError(store, node.id, "当前节点没有可固定的图片，请先上传或生成图片。");
    return;
  }

  let assetType = normalizeAssetType(existingAsset?.asset_type || initialAssetType);
  const modal = el("div", "modal-card visual-asset-panel");
  const close = showModal(modal);
  render();

  function render() {
    const previous = mergeFieldValues(seedFromExistingAsset(existingAsset), collectFieldValues(modal));
    const defaults = visualAssetDefaults(node, imageAsset, assetType);
    renderVisualAssetPanel(modal, { assetType, node, imageAsset, previous, defaults });
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
    if (action === "draft-card") {
      await draftCard();
      return;
    }
    if (action === "fix" || action === "reject") {
      await submit(action === "fix" ? "fixed" : "rejected");
    }
  });

  function applyLockChip(index) {
    const chips = lockChipsForAssetType(assetType);
    const [label, fieldKey] = chips[index] || [];
    if (!label) return;
    const fieldValue = fieldKey ? field(modal, fieldKey, "data-card") : "";
    const lockText = fieldValue ? `保持${fieldValue.slice(0, 24)}` : label;
    const textareaEl = modal.querySelector('[data-field="negative_locks"]');
    const current = lines(textareaEl.value);
    if (!current.includes(lockText)) textareaEl.value = [...current, lockText].join("\n");
  }

  async function draftCard() {
    if (!runtime?.draftAssetCard) return showError("自动识别服务暂不可用。");
    setDrafting(true);
    setBusy(true);
    try {
      const response = await runtime.draftAssetCard({
        asset_type: assetType,
        source_image_asset_refs: [imageAsset.asset_id],
        node_id: node.id,
        prompt_text: node.prompt || node.result || node.title || "",
        provider_service_id: "vision_image",
        generated_at: new Date().toISOString(),
      });
      const draft = response?.draft || {};
      const status = modal.querySelector('[data-role="draft-status"]');
      if (!draft?.draft_id) {
        if (status) {
          status.hidden = false;
          status.textContent = response?.safe_manifest?.failure_class || response?.job?.status || "暂时无法生成草稿";
        }
        return;
      }
      setInputValue(modal, "label", draft.label_suggestion || "");
      setInputValue(modal, "signature", draft.signature || "");
      for (const [key, value] of Object.entries(draft.feature_card || {})) {
        setInputValue(modal, key, value, "data-card");
      }
      const textareaEl = modal.querySelector('[data-field="negative_locks"]');
      if (textareaEl) {
        const merged = [...lines(textareaEl.value), ...(draft.candidate_locks || [])];
        textareaEl.value = [...new Set(merged.map((item) => String(item || "").trim()).filter(Boolean))].join("\n");
      }
      if (status) {
        status.hidden = false;
        status.dataset.candidate_locks = JSON.stringify(draft.candidate_locks || []);
        status.dataset.missing_fields = JSON.stringify(draft.missing_fields || []);
        status.textContent = `草稿，确认前不会生效。待补充：${(draft.missing_fields || []).join(", ") || "无"}`;
      }
    } catch (error) {
      showError(`自动识别失败：${safeError(error)}`);
    } finally {
      setDrafting(false);
      setBusy(false);
    }
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
        supersedesAssetId: decision === "fixed" ? assetIdFromRef(existingAsset) : "",
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

  function setDrafting(drafting) {
    modal.classList.toggle("is-drafting", drafting);
    const button = modal.querySelector('[data-action="draft-card"]');
    if (button) button.textContent = drafting ? "识别中..." : "自动识别草稿";
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

async function submitVisualAssetReview({
  store,
  runtime,
  node,
  imageAsset,
  decision,
  label,
  assetType,
  signature,
  featureCard,
  negativeLocks,
  supersedesAssetId = "",
}) {
  const payload = buildVisualAssetPromotionPayload({
    node,
    imageAsset,
    decision,
    label,
    assetType,
    signature,
    featureCard,
    negativeLocks,
    supersedesAssetId,
  });
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
    n.params.visualAssets = mergeVisualAssets(n.params.visualAssets || [], localAsset, supersedesAssetId);
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
      image_asset_refs: Array.isArray(localAsset.image_asset_refs) ? localAsset.image_asset_refs : [imageAsset.asset_id],
      preview_url: localAsset.preview_url || imageAsset.preview_url || "",
      signature: localAsset.signature,
      feature_card: localAsset.feature_card,
      negative_locks: localAsset.negative_locks,
      source_evidence: localAsset.source_evidence || null,
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

function setInputValue(root, name, value, attr = "data-field") {
  const input = root.querySelector(`[${attr}="${name}"]`);
  if (input) input.value = String(value || "");
}

function mergeVisualAssets(existing, asset, supersedesAssetId = "") {
  const assetId = String(asset?.asset_id || "").trim();
  if (!assetId) return existing;
  return [
    ...existing.filter((item) => {
      const current = String(item?.asset_id || "").trim();
      return current !== assetId && current !== supersedesAssetId;
    }),
    asset,
  ].slice(-8);
}

function seedFromExistingAsset(asset) {
  if (!asset) return {};
  return {
    label: String(asset.label || asset.title || ""),
    signature: String(asset.signature || asset.safe_summary || ""),
    card: asset.feature_card && typeof asset.feature_card === "object" ? asset.feature_card : {},
    locks: Array.isArray(asset.negative_locks) ? asset.negative_locks.join("\n") : "",
  };
}

function mergeFieldValues(seed, current) {
  return {
    label: current.label || seed.label || "",
    signature: current.signature || seed.signature || "",
    locks: current.locks || seed.locks || "",
    card: { ...(seed.card || {}), ...(current.card || {}) },
  };
}

const normalizeAssetType = (value) => (["character", "scene", "prop"].includes(String(value || "")) ? String(value) : "character");

function assetIdFromRef(ref) {
  return String(ref?.asset_id || ref?.visual_asset_id || ref?.assetId || "").trim();
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
  return formatRuntimeError(error, "??????");
}
