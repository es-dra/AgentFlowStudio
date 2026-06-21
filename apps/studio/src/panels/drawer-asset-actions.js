import { fitVisibleCanvasViewport } from "../canvas-safe-area.js";
import { icon } from "../icons.js";
import { el, showModal } from "../overlay.js";
import { openVisualAssetPanel } from "./visual-asset-panel.js";

export function markAssetReference(store, asset) {
  store.set((s) => {
    const sourceId = asset.source_node_id;
    const selectedId = s.selection.nodeIds[0];
    const target = sourceId && s.nodes[sourceId] ? s.nodes[sourceId] : s.nodes[selectedId];
    if (!target) return;
    target.params.isReference = true;
    target.status = "complete";
  });
}

export function attachAssetToSelection(state, store, asset) {
  const selectedId = state.selection.nodeIds[0];
  if (!selectedId) return;
  store.set((s) => {
    const node = s.nodes[selectedId];
    if (!node) return;
    if (isFixedVisualAsset(asset)) {
      const visual = visualAssetRef(asset);
      const current = Array.isArray(node.params.visualAssets) ? node.params.visualAssets : [];
      if (!current.some((item) => String(item?.asset_id || "") === visual.asset_id)) {
        node.params.visualAssets = [visual, ...current].slice(0, 8);
      }
      return;
    }
    const list = Array.isArray(node.params.attachments) ? node.params.attachments : [];
    if (!list.some((item) => item.id === asset.id)) {
      node.params.attachments = [{ id: asset.id, label: asset.title, kind: asset.kind }, ...list].slice(0, 8);
    }
  });
}

export function setVideoFrameFromAsset(state, store, asset, slot) {
  const selectedId = state.selection.nodeIds[0];
  if (!selectedId || !asset?.asset_id) return;
  store.set((s) => {
    const node = s.nodes[selectedId];
    if (!node || node.type !== "video") return;
    if (slot === "last") node.params.lastFrameImageAssetId = asset.asset_id;
    else node.params.firstFrameImageAssetId = asset.asset_id;
    const uploads = Array.isArray(node.params.uploads) ? node.params.uploads : [];
    const ref = imageAssetUploadRef(asset, slot === "last" ? "last_frame" : "first_frame");
    node.params.uploads = [ref, ...uploads.filter((item) => item?.asset_id !== asset.asset_id)].slice(0, 4);
    node.status = "complete";
    node.result = slot === "last" ? `已设为尾帧：${asset.asset_id}` : `已设为首帧：${asset.asset_id}`;
  });
}

export function promoteImageAssetFromDrawer(state, store, runtime, asset, assetType) {
  const node = state.nodes[asset.source_node_id] || state.nodes[state.selection.nodeIds[0]] || {
    id: asset.source_node_id || "drawer_asset",
    title: asset.title || asset.asset_id || "image asset",
    prompt: asset.safe_summary || "",
    result: asset.safe_summary || "",
  };
  openVisualAssetPanel({
    store,
    runtime,
    node,
    imageAsset: imageAssetUploadRef(asset, assetType === "scene" ? "scene_reference" : assetType === "prop" ? "prop_reference" : "character_reference"),
    initialAssetType: assetType,
  });
}

export function deleteImageAssetFromDrawer(state, store, runtime, asset) {
  const assetId = String(asset?.asset_id || "").trim();
  if (!assetId || isFixedVisualAsset(asset)) return;
  const applyDelete = () => {
    removeImageAssetFromStore(store, assetId);
    store.flushRuntimeSave?.();
  };
  if (!runtime?.deleteImageAsset) {
    applyDelete();
    return;
  }
  runtime.deleteImageAsset(assetId)
    .then(applyDelete)
    .catch((error) => {
      store.set((s) => {
        s.ui.saveState = "本地暂存";
        s.ui.saveMessage = `图片素材删除失败：${safeError(error)}`;
      }, { history: false, persist: false });
    });
}

export function removeImageAssetFromStore(store, assetId) {
  const normalized = String(assetId || "").trim();
  if (!normalized) return;
  store.set((s) => {
    s.assets = (s.assets || []).filter((item) => String(item.asset_id || "") !== normalized);
    for (const node of Object.values(s.nodes || {})) {
      if (!node?.params) continue;
      if (Array.isArray(node.params.uploads)) {
        node.params.uploads = node.params.uploads.filter((item) => String(item?.asset_id || item?.assetId || "") !== normalized);
      }
      if (Array.isArray(node.params.attachments)) {
        node.params.attachments = node.params.attachments.filter((item) => String(item?.asset_id || item?.assetId || item?.id || "") !== normalized);
      }
      if (String(node.params.firstFrameImageAssetId || "") === normalized) delete node.params.firstFrameImageAssetId;
      if (String(node.params.lastFrameImageAssetId || "") === normalized) delete node.params.lastFrameImageAssetId;
      if (String(node.previewUrl || "").includes(`/image-assets/${normalized}/preview`)) {
        delete node.previewUrl;
      }
    }
  });
}

export function openRetireAssetModal(store, runtime, asset) {
  const assetId = String(asset.visual_asset_id || asset.asset_id || "").trim();
  if (!assetId || !runtime?.retireVisualAsset) return;
  const modal = el("div", "modal compact asset-retire-modal");
  const head = el("div", "modal-head");
  head.appendChild(el("strong", "", "停用素材"));
  const closeBtn = el("button", "modal-close");
  closeBtn.innerHTML = icon("x", 15);
  head.appendChild(el("span", "head-spacer"));
  head.appendChild(closeBtn);

  const body = el("div", "modal-body");
  body.appendChild(el("p", "", "停用后，该素材不会再作为固定素材进入后续生成。已绑定到节点的标记会显示为失效。"));
  const field = el("label", "modal-field");
  field.appendChild(el("span", "", "原因"));
  const reason = document.createElement("textarea");
  reason.rows = 3;
  reason.value = "不再用于当前项目";
  field.appendChild(reason);
  const error = el("div", "modal-error");
  error.hidden = true;
  body.append(field, error);

  const actions = el("div", "modal-actions");
  const cancel = el("button", "ghost-btn", "取消");
  const confirm = el("button", "primary-btn danger", "确认停用");
  actions.append(cancel, confirm);
  modal.append(head, body, actions);

  const close = showModal(modal);
  closeBtn.addEventListener("click", close);
  cancel.addEventListener("click", close);
  confirm.addEventListener("click", () => retireAsset(store, runtime, assetId, reason, error, confirm, close));
}

export function isImageAsset(asset) {
  return Boolean(asset?.asset_id)
    && ["image_reference", "keyframe", "character_turnaround", "scene_board"].includes(String(asset?.kind || ""));
}

export function isFixedVisualAsset(asset) {
  return ["visual_asset", "character_asset", "scene_asset", "prop_asset"].includes(String(asset?.kind || "")) || Boolean(asset?.visual_asset_id);
}

export function iconForAsset(asset) {
  if (asset.kind === "visual_asset" && asset.asset_type === "character") return "user";
  if (asset.kind === "visual_asset" && asset.asset_type === "scene") return "image";
  if (asset.kind === "visual_asset" && asset.asset_type === "prop") return "bookmark";
  if (asset.kind === "character_asset") return "user";
  if (asset.kind === "scene_asset") return "image";
  if (asset.kind === "prop_asset") return "bookmark";
  if (asset.kind === "director_setup") return "layers";
  if (asset.kind === "character_turnaround") return "user";
  if (asset.kind === "video_clip" || asset.kind === "video_comp") return "video";
  if (asset.kind === "audio_clip") return "audio";
  if (asset.kind === "storyboard") return "script";
  return "image";
}

export function kindLabel(assetOrKind) {
  const asset = typeof assetOrKind === "object" && assetOrKind ? assetOrKind : { kind: assetOrKind };
  if (asset.kind === "visual_asset" && asset.asset_type === "character") return "角色资产";
  if (asset.kind === "visual_asset" && asset.asset_type === "scene") return "场景资产";
  if (asset.kind === "visual_asset" && asset.asset_type === "prop") return "道具资产";
  return {
    character_asset: "角色资产",
    scene_asset: "场景资产",
    prop_asset: "道具资产",
    character_turnaround: "角色三视图",
    scene_board: "场景",
    keyframe: "关键帧",
    video_clip: "视频片段",
    audio_clip: "音频",
    director_setup: "导演台",
    storyboard: "分镜",
    text_brief: "文本",
    video_comp: "合成",
  }[asset.kind] || "参考";
}

function retireAsset(store, runtime, assetId, reason, error, confirm, close) {
  const text = reason.value.trim();
  if (!text) {
    error.textContent = "请填写停用原因。";
    error.hidden = false;
    reason.focus();
    return;
  }
  confirm.disabled = true;
  runtime.retireVisualAsset(assetId, { reason: text, retired_at: new Date().toISOString() })
    .then((payload) => {
      applyRetiredAsset(store, payload?.asset || { asset_id: assetId, status: "retired" });
      close();
    })
    .catch((err) => {
      error.textContent = safeError(err);
      error.hidden = false;
      confirm.disabled = false;
    });
}

function applyRetiredAsset(store, retiredAsset) {
  const assetId = String(retiredAsset.asset_id || retiredAsset.visual_asset_id || "").trim();
  if (!assetId) return;
  store.set((s) => {
    for (const asset of s.assets || []) {
      if (String(asset.asset_id || asset.visual_asset_id || "") === assetId) {
        asset.status = "retired";
        asset.asset_status = "retired";
        asset.retired_at = retiredAsset.retired_at || asset.retired_at || new Date().toISOString();
      }
    }
    for (const node of Object.values(s.nodes || {})) {
      if (!Array.isArray(node.params?.visualAssets)) continue;
      node.params.visualAssets = node.params.visualAssets.map((item) => {
        if (String(item?.asset_id || item?.visual_asset_id || "") !== assetId) return item;
        return { ...item, status: "retired", runtime_status: "excluded", disabled_reason: "已停用，本次未携带" };
      });
    }
  });
}

function imageAssetUploadRef(asset, role) {
  return {
    asset_id: asset.asset_id,
    role,
    filename: asset.title || `${asset.asset_id}.png`,
    preview_url: asset.preview_url || "",
    width: asset.width || null,
    height: asset.height || null,
    aspect_ratio: asset.aspect_ratio || null,
  };
}

function visualAssetRef(asset) {
  const assetId = String(asset.visual_asset_id || asset.asset_id || asset.id || "").trim();
  return {
    asset_id: assetId,
    label: asset.label || asset.title || assetId,
    asset_type: asset.asset_type || (asset.kind === "scene_asset" ? "scene" : asset.kind === "prop_asset" ? "prop" : "character"),
    status: asset.status || "fixed",
    signature: asset.signature || asset.safe_summary || "",
    feature_card: asset.feature_card || {},
    negative_locks: Array.isArray(asset.negative_locks) ? asset.negative_locks : [],
    source_node_id: asset.source_node_id || null,
  };
}

function focusAssetSource(store, asset) {
  if (!asset.source_node_id) return;
  store.set((s) => {
    const node = s.nodes[asset.source_node_id];
    if (!node) return;
    s.selection = { nodeIds: [node.id], edgeId: null };
    s.viewport = fitVisibleCanvasViewport({ [node.id]: node }, 220);
  }, { history: false, persist: false });
}

function safeError(error) {
  return String(error instanceof Error ? error.message : error || "停用失败")
    .replace(/Bearer\s+\S+/gi, "Bearer <redacted>")
    .slice(0, 180);
}

export { focusAssetSource };
