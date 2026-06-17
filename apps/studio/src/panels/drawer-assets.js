import { icon } from "../icons.js";
import { el } from "../overlay.js";
import { openAssetDetailPopover } from "./asset-detail-popover.js";
import {
  attachAssetToSelection,
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
  renderAssets(state, store, runtime, body);
}

function renderAssets(state, store, runtime, body) {
  const query = String(state.ui.drawerSearch || "").trim().toLowerCase();
  const assets = query
    ? state.assets.filter((asset) => `${asset.title || ""} ${asset.safe_summary || ""} ${asset.asset_id || ""}`.toLowerCase().includes(query))
    : state.assets;
  if (!assets.length) {
    body.appendChild(emptyAssetState(query));
    return;
  }
  for (const asset of assets) body.appendChild(assetCard(state, store, runtime, asset));
}

function emptyAssetState(query) {
  const empty = el("div", "drawer-empty");
  empty.classList.add("asset-empty-state");
  empty.innerHTML = [
    `<span class="folder-glyph">${icon("folder", 34)}</span>`,
    `<strong>${query ? "没有匹配的素材" : "还没有可复用素材"}</strong>`,
    `<small>${query ? "换一个关键词，或先清空搜索。" : "生成图片、上传参考图，或把结果保存为角色/场景后会出现在这里。"}</small>`,
  ].join("");
  return empty;
}

function assetCard(state, store, runtime, asset) {
  const retired = asset.status === "retired" || asset.asset_status === "retired" || asset.runtime_status === "excluded";
  const card = el("div", `asset-card${retired ? " retired" : ""}`);
  const thumb = assetThumb(store, runtime, asset);
  const meta = assetMeta(store, runtime, asset, retired);
  const actions = assetActions(state, store, runtime, asset, retired);
  card.append(thumb, meta, actions);
  return card;
}

function assetThumb(store, runtime, asset) {
  const thumb = el("button", `asset-thumb asset-thumb-${asset.thumbnail_ref || asset.kind || "reference"}`);
  if (asset.preview_url) {
    const img = document.createElement("img");
    img.src = asset.preview_url;
    img.alt = asset.title || asset.asset_id || "asset preview";
    img.loading = "lazy";
    thumb.appendChild(img);
  } else {
    thumb.innerHTML = `<span>${icon(iconForAsset(asset), 18)}</span>`;
  }
  thumb.title = "查看素材详情";
  thumb.addEventListener("click", () => openAssetDetailPopover(store, runtime, asset, thumb));
  return thumb;
}

function assetMeta(store, runtime, asset, retired) {
  const meta = el("div", "asset-meta");
  meta.appendChild(el("div", "asset-title", asset.title || "未命名素材"));
  meta.appendChild(el("div", "asset-kind", `${kindLabel(asset)}${retired ? " · 已停用" : ""}`));
  meta.appendChild(el("div", "asset-summary", asset.safe_summary || "安全摘要将在生成后出现。"));
  meta.addEventListener("click", () => openAssetDetailPopover(store, runtime, asset, meta));
  return meta;
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
    actions.appendChild(assetAction("保存角色", () => promoteImageAssetFromDrawer(state, store, runtime, asset, "character")));
    actions.appendChild(assetAction("保存场景", () => promoteImageAssetFromDrawer(state, store, runtime, asset, "scene")));
  }
  if (isFixedVisualAsset(asset) && !retired) {
    actions.appendChild(assetAction("停用素材", () => openRetireAssetModal(store, runtime, asset)));
  }
  return actions;
}

function assetAction(label, onClick) {
  const btn = el("button", "asset-action", label);
  btn.addEventListener("click", onClick);
  return btn;
}
