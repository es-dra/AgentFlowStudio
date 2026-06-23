import { icon } from "../icons.js";
import { downloadResolvedMedia } from "../media-preview-modal.js";
import { el, showPopover } from "../overlay.js";
import { setRuntimeMediaSource } from "../runtime-media-source.js";
import {
  ASSET_LIFECYCLE_FILTERS,
  assetLifecycleLabel,
  assetLifecycleState,
  assetLifecycleSummary,
  matchesAssetLifecycleFilter,
} from "../asset-lifecycle.js";
import { openAssetDetailPopover } from "./asset-detail-popover.js";
import {
  attachAssetToSelection,
  deleteImageAssetFromDrawer,
  focusAssetSource,
  iconForAsset,
  isFixedVisualAsset,
  isImageAsset,
  kindLabel,
  markAssetReference,
  openRetireAssetModal,
  promoteImageAssetFromDrawer,
  setVideoFrameFromAsset,
} from "./drawer-asset-actions.js";

export function renderAssetDrawer(state, store, runtime, drawer, body) {
  const search = el("div", "drawer-search");
  search.innerHTML = icon("search", 13);
  const input = document.createElement("input");
  input.placeholder = "搜索角色、场景或参考图";
  input.value = state.ui.drawerSearch || "";
  input.addEventListener("input", () => {
    store.set((s) => { s.ui.drawerSearch = input.value; }, { history: false });
  });
  search.appendChild(input);
  drawer.appendChild(search);
  drawer.appendChild(assetLifecycleFilter(state, store));
  renderAssets(state, store, runtime, body);
}

function renderAssets(state, store, runtime, body) {
  const query = String(state.ui.drawerSearch || "").trim().toLowerCase();
  const filter = state.ui.assetLifecycleFilter || "all";
  const assets = (state.assets || []).filter((asset) => {
    const matchesQuery = !query
      || `${asset.title || ""} ${asset.safe_summary || ""} ${asset.asset_id || ""}`.toLowerCase().includes(query);
    return matchesQuery && matchesAssetLifecycleFilter(asset, filter);
  });
  if (!assets.length) {
    body.appendChild(emptyAssetState(query, filter));
    return;
  }
  for (const asset of assets) body.appendChild(assetCard(state, store, runtime, asset));
}

function assetLifecycleFilter(state, store) {
  const counts = assetLifecycleSummary(state.assets || []);
  const wrap = el("div", "asset-lifecycle-filter");
  for (const item of ASSET_LIFECYCLE_FILTERS) {
    const active = (state.ui.assetLifecycleFilter || "all") === item.id;
    const button = el("button", active ? "active" : "");
    button.type = "button";
    const count = item.id === "all" ? counts.total : item.id === "draft" ? counts.draft + counts.rejected : counts[item.id];
    button.innerHTML = `<span>${item.label}</span><strong>${count || 0}</strong>`;
    button.addEventListener("click", () => {
      store.set((s) => { s.ui.assetLifecycleFilter = item.id; }, { history: false });
    });
    wrap.appendChild(button);
  }
  return wrap;
}

function emptyAssetState(query, filter) {
  const empty = el("div", "drawer-empty");
  empty.classList.add("asset-empty-state");
  empty.innerHTML = [
    `<span class="folder-glyph">${icon("folder", 34)}</span>`,
    `<strong>${query ? "没有匹配的素材" : "还没有可复用素材"}</strong>`,
    `<small>${emptyAssetHint(query, filter)}</small>`,
  ].join("");
  return empty;
}

function assetCard(state, store, runtime, asset) {
  const retired = asset.status === "retired" || asset.asset_status === "retired" || asset.runtime_status === "excluded";
  const lifecycle = assetLifecycleState(asset);
  const card = el("div", `asset-card lifecycle-${lifecycle}${retired ? " retired" : ""}`);
  const thumb = assetThumb(state, store, runtime, asset, retired);
  const meta = assetMeta(store, runtime, asset, retired);
  const actions = assetActions(state, store, runtime, asset, retired);
  card.append(thumb, meta, actions);
  card.addEventListener("contextmenu", (event) => openAssetContextMenu(event, state, store, runtime, asset, retired));
  return card;
}

function assetThumb(state, store, runtime, asset, retired) {
  const thumb = el("button", `asset-thumb asset-thumb-${asset.thumbnail_ref || asset.kind || "reference"}`);
  if (asset.preview_url) {
    const img = document.createElement("img");
    setRuntimeMediaSource(img, asset.preview_url);
    img.alt = asset.title || asset.asset_id || "asset preview";
    img.loading = "lazy";
    thumb.appendChild(img);
  } else {
    thumb.innerHTML = `<span>${icon(iconForAsset(asset), 18)}</span>`;
  }
  thumb.title = "查看素材详情";
  thumb.addEventListener("click", () => openAssetDetailPopover(store, runtime, asset, thumb));
  thumb.addEventListener("contextmenu", (event) => openAssetContextMenu(event, state, store, runtime, asset, retired));
  return thumb;
}

function assetMeta(store, runtime, asset, retired) {
  const meta = el("div", "asset-meta");
  const title = el("div", "asset-title");
  title.appendChild(el("span", "", asset.title || "未命名素材"));
  title.appendChild(el("small", `asset-lifecycle-badge ${assetLifecycleState(asset)}`, assetLifecycleLabel(asset)));
  meta.appendChild(title);
  meta.appendChild(el("div", "asset-kind", `${kindLabel(asset)}${retired ? " · 已停用" : ""}`));
  meta.appendChild(el("div", "asset-summary", asset.safe_summary || "安全摘要将在生成后出现。"));
  meta.addEventListener("click", () => openAssetDetailPopover(store, runtime, asset, meta));
  return meta;
}

function emptyAssetHint(query, filter) {
  if (query) return "换一个关键词，或先清空搜索。";
  if (filter === "fixed") return "确认角色或场景资产后，会默认进入后续上下文调度。";
  if (filter === "draft") return "视觉识别和生成结果会先作为候选，等待你确认。";
  if (filter === "retired") return "停用素材会保留记录，但不会默认进入下一次调用。";
  return "生成图片、上传参考图，或把结果保存为角色/场景后会出现在这里。";
}

function assetActions(state, store, runtime, asset, retired) {
  const actions = el("div", "asset-actions");
  actions.appendChild(assetAction("用作参考", () => markAssetReference(store, asset)));
  const selectedNode = state.nodes[state.selection.nodeIds[0]];
  if (selectedNode?.type === "video" && isImageAsset(asset)) {
    actions.appendChild(assetAction("设为首帧", () => setVideoFrameFromAsset(state, store, asset, "first")));
    actions.appendChild(assetAction("设为尾帧", () => setVideoFrameFromAsset(state, store, asset, "last")));
  } else {
    actions.appendChild(assetAction("加入当前节点", () => attachAssetToSelection(state, store, asset)));
  }
  actions.appendChild(assetAction("定位来源", () => focusAssetSource(store, asset)));
  if (isImageAsset(asset)) {
    if (asset.preview_url) actions.appendChild(assetAction("导出原图", () => downloadImageAsset(asset)));
    actions.appendChild(assetAction("保存角色", () => promoteImageAssetFromDrawer(state, store, runtime, asset, "character")));
    actions.appendChild(assetAction("保存场景", () => promoteImageAssetFromDrawer(state, store, runtime, asset, "scene")));
  }
  if (isFixedVisualAsset(asset) && !retired) {
    actions.appendChild(assetAction("停用素材", () => openRetireAssetModal(store, runtime, asset)));
  }
  return actions;
}

function openAssetContextMenu(event, state, store, runtime, asset, retired) {
  event.preventDefault();
  event.stopPropagation();
  const menu = el("div", "canvas-context-menu asset-context-menu");
  menu.appendChild(el("div", "canvas-menu-title", asset.title || asset.asset_id || "素材"));
  const anchor = {
    getBoundingClientRect() {
      const size = 1;
      return {
        left: event.clientX,
        right: event.clientX + size,
        top: event.clientY,
        bottom: event.clientY + size,
        width: size,
        height: size,
      };
    },
  };
  const close = showPopover(anchor, menu, { place: "bottom" });
  const appendItem = (label, iconName, description, onClick, disabled = false) => {
    const button = contextMenuItem(label, iconName, description, () => {
      close();
      onClick();
    });
    button.disabled = disabled;
    menu.appendChild(button);
  };
  appendItem("查看详情", "image", "打开素材记录和来源", () => openAssetDetailPopover(store, runtime, asset, menu));
  appendItem("用作参考", "bookmark", "标记为当前生成参考", () => markAssetReference(store, asset));
  appendContextAttachAction(appendItem, state, store, asset);
  if (isImageAsset(asset) && asset.preview_url) {
    appendItem("导出原图", "archive", "下载原始分辨率图片", () => downloadImageAsset(asset));
  }
  appendItem("定位来源", "layers", "回到产生该素材的节点", () => focusAssetSource(store, asset), !asset.source_node_id);
  if (isFixedVisualAsset(asset)) {
    appendItem("停用素材", "x", "不再默认带入后续生成", () => openRetireAssetModal(store, runtime, asset), retired);
  } else if (isImageAsset(asset)) {
    appendItem("删除图片素材", "x", "从当前项目素材库移除", () => deleteImageAssetFromDrawer(state, store, runtime, asset));
  }
}

function appendContextAttachAction(appendItem, state, store, asset) {
  const selectedNode = state.nodes[state.selection.nodeIds[0]];
  if (selectedNode?.type === "video" && isImageAsset(asset)) {
    appendItem("设为首帧", "image", "给当前视频节点使用", () => setVideoFrameFromAsset(state, store, asset, "first"));
    appendItem("设为尾帧", "image", "给当前视频节点使用", () => setVideoFrameFromAsset(state, store, asset, "last"));
    return;
  }
  appendItem("加入当前节点", "plus", "把素材挂到选中节点", () => attachAssetToSelection(state, store, asset), !state.selection.nodeIds[0]);
}

function contextMenuItem(label, iconName, description, onClick) {
  const item = el("button", "canvas-menu-item");
  item.type = "button";
  item.innerHTML = [
    `<span class="canvas-menu-icon">${icon(iconName, 14)}</span>`,
    `<span><strong>${escapeHtml(label)}</strong><small>${escapeHtml(description)}</small></span>`,
  ].join("");
  item.addEventListener("click", onClick);
  return item;
}

function assetAction(label, onClick) {
  const btn = el("button", "asset-action", label);
  btn.addEventListener("click", onClick);
  return btn;
}

async function downloadImageAsset(asset) {
  await downloadResolvedMedia(asset.preview_url, assetDownloadName(asset));
}

function assetDownloadName(asset) {
  const base = String(asset.title || asset.label || asset.asset_id || "afs-image")
    .replace(/[\\/:*?"<>|]+/g, "-")
    .trim()
    .slice(0, 80) || "afs-image";
  return `${base}.png`;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[ch]));
}
