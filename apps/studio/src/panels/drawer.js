import { NODE_TYPES, deleteNodes } from "../nodes.js";
import { el, showModal } from "../overlay.js";
import { fitViewport } from "../geometry.js";
import { icon } from "../icons.js";
import { openAssetDetailPopover } from "./asset-detail-popover.js";

export function renderDrawer(state, store, runtime) {
  const drawer = document.getElementById("drawer");
  drawer.classList.toggle("collapsed", !state.ui.drawerOpen);
  const signature = drawerSignature(state);
  if (drawer.dataset.signature === signature) return;
  drawer.dataset.signature = signature;
  drawer.replaceChildren();

  const head = el("div", "drawer-head");
  const logo = el("div", "topbar-logo", "▣");
  head.appendChild(logo);
  drawer.appendChild(head);

  const proj = el("div", "drawer-project");
  proj.appendChild(el("span", "proj-name", state.meta.projectName));
  proj.appendChild(el("span", "", "|"));
  proj.appendChild(el("span", "", `${state.meta.canvasName} ▾`));
  drawer.appendChild(proj);

  const tabs = el("div", "drawer-tabs");
  for (const [id, label] of [["canvas", "画布元素"], ["assets", "显性资产"]]) {
    const tab = el("button", `drawer-tab${state.ui.drawerTab === id ? " active" : ""}`, label);
    tab.addEventListener("click", () => store.set((s) => { s.ui.drawerTab = id; }));
    tabs.appendChild(tab);
  }
  drawer.appendChild(tabs);

  const body = el("div", "drawer-body");
  if (state.ui.drawerTab === "canvas") {
    drawer.appendChild(canvasToolbar());
    renderCanvasTree(state, store, body);
  } else {
    const search = el("div", "drawer-search");
    search.innerHTML = icon("search", 13);
    const input = document.createElement("input");
    input.placeholder = "请输入搜索内容";
    input.value = state.ui.drawerSearch || "";
    input.addEventListener("input", () => {
      store.set((s) => { s.ui.drawerSearch = input.value; }, { history: false });
    });
    search.appendChild(input);
    drawer.appendChild(search);
    renderAssets(state, store, runtime, body);
  }
  drawer.appendChild(body);

  const foot = el("div", "drawer-foot");
  const collapse = el("button", "icon-btn", "⇤");
  collapse.title = "收起节点侧栏";
  collapse.addEventListener("click", () => store.set((s) => { s.ui.drawerOpen = false; }));
  foot.appendChild(collapse);
  foot.appendChild(el("span", "", `共 ${state.order.length} 节点`));
  drawer.appendChild(foot);
}

function canvasToolbar() {
  const bar = el("div", "drawer-toolbar");
  bar.appendChild(el("span", "", "画布元素"));
  bar.appendChild(el("span", "", "全部 ▾"));
  return bar;
}

function renderCanvasTree(state, store, body) {
  if (!state.order.length) {
    body.appendChild(el("div", "drawer-empty", "当前画布没有内容"));
    return;
  }
  const grouped = new Set();
  for (const group of Object.values(state.groups)) {
    const wrap = el("div", "tree-group");
    const head = el("div", "tree-group-head");
    head.innerHTML = `<span>▾</span>${icon("folder", 13)}<span>${group.title}</span>`;
    wrap.appendChild(head);
    for (const id of group.nodeIds) {
      const node = state.nodes[id];
      if (!node) continue;
      grouped.add(id);
      wrap.appendChild(treeItem(state, store, node));
    }
    body.appendChild(wrap);
  }
  for (const id of [...state.order].reverse()) {
    if (grouped.has(id)) continue;
    const node = state.nodes[id];
    if (node) body.appendChild(treeItem(state, store, node));
  }
}

function treeItem(state, store, node) {
  const def = NODE_TYPES[node.type] || NODE_TYPES.text;
  const item = el("button", `tree-item${state.selection.nodeIds.includes(node.id) ? " selected" : ""}`);
  item.innerHTML = `<span class="tree-icon">${icon(def.icon, 12)}</span><span class="tree-label">${node.title}</span>`;
  item.addEventListener("click", () => {
    store.set((s) => {
      s.selection = { nodeIds: [node.id], edgeId: null };
      const root = document.getElementById("canvas-root").getBoundingClientRect();
      const single = { [node.id]: node };
      const fitted = fitViewport(single, root.width, root.height, 200);
      s.viewport = fitted;
    });
  });
  const remove = el("button", "icon-btn");
  remove.innerHTML = icon("x", 11);
  remove.title = "删除节点";
  remove.addEventListener("click", (e) => {
    e.stopPropagation();
    deleteNodes(store, [node.id]);
  });
  item.appendChild(remove);
  return item;
}

function renderAssets(state, store, runtime, body) {
  const query = String(state.ui.drawerSearch || "").trim().toLowerCase();
  const assets = query
    ? state.assets.filter((asset) => `${asset.title || ""} ${asset.safe_summary || ""} ${asset.asset_id || ""}`.toLowerCase().includes(query))
    : state.assets;
  if (!assets.length) {
    const empty = el("div", "drawer-empty");
    empty.innerHTML = `<span class="folder-glyph">${icon("folder", 34)}</span>暂无资产`;
    body.appendChild(empty);
    return;
  }
  for (const asset of assets) {
    body.appendChild(assetCard(state, store, runtime, asset));
  }
}

function assetCard(state, store, runtime, asset) {
  const retired = asset.status === "retired" || asset.asset_status === "retired";
  const card = el("div", `asset-card${retired ? " retired" : ""}`);
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
  thumb.title = "查看资产详情";
  thumb.addEventListener("click", () => openAssetDetailPopover(store, asset, thumb));
  const meta = el("div", "asset-meta");
  meta.appendChild(el("div", "asset-title", asset.title || "未命名资产"));
  meta.appendChild(el("div", "asset-kind", `${kindLabel(asset)}${retired ? " · 已退役" : ""}`));
  meta.appendChild(el("div", "asset-summary", asset.safe_summary || "安全摘要将在生成后出现。"));
  meta.addEventListener("click", () => openAssetDetailPopover(store, asset, meta));
  const actions = el("div", "asset-actions");
  actions.appendChild(assetAction("设为参考", () => markAssetReference(store, asset)));
  const selectedNode = state.nodes[state.selection.nodeIds[0]];
  if (selectedNode?.type === "video" && isImageAsset(asset)) {
    actions.appendChild(assetAction("设为首帧", () => setVideoFrameFromAsset(state, store, asset, "first")));
    actions.appendChild(assetAction("设为尾帧", () => setVideoFrameFromAsset(state, store, asset, "last")));
  } else {
    actions.appendChild(assetAction("用于当前节点", () => attachAssetToSelection(state, store, asset)));
  }
  actions.appendChild(assetAction("从画布定位", () => focusAssetSource(store, asset)));
  if (isFixedVisualAsset(asset) && !retired) {
    actions.appendChild(assetAction("退役", () => openRetireAssetModal(store, runtime, asset)));
  }
  card.append(thumb, meta, actions);
  return card;
}

function assetAction(label, onClick) {
  const btn = el("button", "asset-action", label);
  btn.addEventListener("click", onClick);
  return btn;
}

function openRetireAssetModal(store, runtime, asset) {
  const assetId = String(asset.visual_asset_id || asset.asset_id || "").trim();
  if (!assetId || !runtime?.retireVisualAsset) return;
  const modal = el("div", "modal compact asset-retire-modal");
  const head = el("div", "modal-head");
  head.appendChild(el("strong", "", "退役资产"));
  const closeBtn = el("button", "modal-close");
  closeBtn.innerHTML = icon("x", 15);
  head.appendChild(el("span", "head-spacer"));
  head.appendChild(closeBtn);

  const body = el("div", "modal-body");
  body.appendChild(el("p", "", `退役后，该资产不会再作为固定资产进入后续生成。已绑定到节点的标记会显示为失效。`));
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
  const confirm = el("button", "primary-btn danger", "确认退役");
  actions.append(cancel, confirm);
  modal.append(head, body, actions);

  const close = showModal(modal);
  closeBtn.addEventListener("click", close);
  cancel.addEventListener("click", close);
  confirm.addEventListener("click", async () => {
    const text = reason.value.trim();
    if (!text) {
      error.textContent = "请填写退役原因。";
      error.hidden = false;
      reason.focus();
      return;
    }
    confirm.disabled = true;
    try {
      const payload = await runtime.retireVisualAsset(assetId, {
        reason: text,
        retired_at: new Date().toISOString(),
      });
      applyRetiredAsset(store, payload?.asset || { asset_id: assetId, status: "retired" });
      close();
    } catch (err) {
      error.textContent = safeError(err);
      error.hidden = false;
      confirm.disabled = false;
    }
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
        return {
          ...item,
          status: "retired",
          runtime_status: "excluded",
          disabled_reason: "已退役，本次未携带",
        };
      });
    }
  });
}

function safeError(error) {
  return String(error instanceof Error ? error.message : error || "退役失败").replace(/Bearer\s+\S+/gi, "Bearer <redacted>").slice(0, 180);
}

function markAssetReference(store, asset) {
  store.set((s) => {
    const sourceId = asset.source_node_id;
    const selectedId = s.selection.nodeIds[0];
    const target = sourceId && s.nodes[sourceId] ? s.nodes[sourceId] : s.nodes[selectedId];
    if (!target) return;
    target.params.isReference = true;
    target.status = "complete";
  });
}

function attachAssetToSelection(state, store, asset) {
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

function setVideoFrameFromAsset(state, store, asset, slot) {
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
    node.result = slot === "last" ? `已设为尾帧 ${asset.asset_id}` : `已设为首帧 ${asset.asset_id}`;
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

function isImageAsset(asset) {
  return Boolean(asset?.asset_id)
    && ["image_reference", "keyframe", "character_turnaround", "scene_board"].includes(String(asset?.kind || ""));
}

function isFixedVisualAsset(asset) {
  return ["visual_asset", "character_asset", "scene_asset"].includes(String(asset?.kind || "")) || Boolean(asset?.visual_asset_id);
}

function visualAssetRef(asset) {
  const assetId = String(asset.visual_asset_id || asset.asset_id || asset.id || "").trim();
  return {
    asset_id: assetId,
    label: asset.label || asset.title || assetId,
    asset_type: asset.asset_type || (asset.kind === "scene_asset" ? "scene" : "character"),
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
    const root = document.getElementById("canvas-root").getBoundingClientRect();
    s.viewport = fitViewport({ [node.id]: node }, root.width, root.height, 220);
  }, { history: false, persist: false });
}

function iconForAsset(asset) {
  if (asset.kind === "visual_asset" && asset.asset_type === "character") return "user";
  if (asset.kind === "visual_asset" && asset.asset_type === "scene") return "image";
  if (asset.kind === "character_asset") return "user";
  if (asset.kind === "scene_asset") return "image";
  if (asset.kind === "director_setup") return "layers";
  if (asset.kind === "character_turnaround") return "user";
  if (asset.kind === "video_clip" || asset.kind === "video_comp") return "video";
  if (asset.kind === "audio_clip") return "audio";
  if (asset.kind === "storyboard") return "script";
  return "image";
}

function kindLabel(assetOrKind) {
  const asset = typeof assetOrKind === "object" && assetOrKind ? assetOrKind : { kind: assetOrKind };
  if (asset.kind === "visual_asset" && asset.asset_type === "character") return "人物资产";
  if (asset.kind === "visual_asset" && asset.asset_type === "scene") return "场景资产";
  const kind = asset.kind;
  return {
    character_asset: "人物资产",
    scene_asset: "场景资产",
    character_turnaround: "人物三视图",
    scene_board: "场景",
    keyframe: "关键帧",
    video_clip: "视频片段",
    audio_clip: "音频",
    director_setup: "导演台",
    storyboard: "分镜",
    text_brief: "文本",
    video_comp: "合成",
  }[kind] || "参考";
}

function drawerSignature(state) {
  return [
    state.meta.projectId, state.meta.projectName, state.meta.canvasName,
    state.ui.drawerOpen, state.ui.drawerTab,
    state.order.join(","),
    state.selection.nodeIds.join(","),
    Object.keys(state.groups).join(","),
    state.assets.length,
    ...Object.values(state.nodes).map((n) => n.title),
    ...state.assets.map((asset) => `${asset.title}:${asset.safe_summary}:${asset.source_node_id}:${asset.asset_id || asset.visual_asset_id || asset.id}:${asset.status || asset.asset_status || ""}:${asset.runtime_status || ""}`),
    ...Object.values(state.nodes).flatMap((node) => (node.params?.visualAssets || []).map((asset) => `${node.id}:${asset.asset_id}:${asset.status || ""}:${asset.runtime_status || ""}:${asset.disabled_reason || ""}`)),
  ].join("|");
}
