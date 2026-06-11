import { badge, button, el } from "./dom.js";
import { directorSetupAsset } from "./director-setup-model.js";

const ASSETS = [
  ["char-turnaround-01", "character_turnaround", "人物三视图", "主角正面、侧面、背面与服装版本", "镜头 01", "已完成"],
  ["char-avatar-01", "character_avatar", "角色头像", "主角情绪头像和发型参考", "镜头 01", "已完成"],
  ["costume-01", "costume_version", "服装版本", "深色连帽衫与室内弱光材质", "镜头 01", "待生成"],
  ["scene-board-01", "scene_board", "场景图", "昏暗卧室、墙上海报、窗户冷光", "镜头 01", "已完成"],
  ["director-setup-01", "director_setup", "导演台布光图", "主光、辅光、背光和遮光旗布置", "镜头 01", "已完成"],
  ["keyframe-01", "keyframe", "关键帧", "男孩坐在床边的首帧构图", "镜头 01", "排队中"],
  ["video-clip-01", "video_clip", "视频片段", "默认 5s I2V 片段占位", "镜头 01", "生成中"],
  ["audio-clip-01", "audio_clip", "音频", "低频环境声与旁白占位", "项目", "已完成"],
];

const FILTERS = [
  ["all", "全部"],
  ["character_turnaround", "人物"],
  ["scene_board", "场景"],
  ["keyframe", "关键帧"],
  ["video_clip", "视频"],
  ["audio_clip", "音频"],
  ["director_setup", "导演台"],
];

export function visibleAssets(state = {}) {
  const baseAssets = ASSETS.map(([asset_id, asset_type, title, safe_summary, linked_shot_id, status]) => ({
    asset_id,
    asset_type,
    title,
    thumbnail_ref: `${asset_type}_thumbnail_ref`,
    linked_shot_id,
    status,
    created_at: "2026-06-11",
    safe_summary,
  }));
  if (!state.directorSavedSetupId) return baseAssets;
  return [directorSetupAsset(state), ...baseAssets.filter((asset) => asset.asset_id !== state.directorSavedSetupId)];
}

export function renderVisibleAssetsLibrary(state, workspace = {}) {
  const allAssets = visibleAssets(state);
  const assets = filteredAssets(state.selectedAssetType || "all", state);
  const selected = allAssets.find((asset) => asset.asset_id === state.selectedVisibleAssetId) || assets[0] || allAssets[0];
  return el("main", { className: "asset-library-page" }, [
    el("header", { className: "asset-library-head" }, [
      el("div", {}, [
        el("span", { text: "显性资产" }),
        el("h1", { text: "资产库" }),
        el("p", { text: "这里只展示能被用户看见、确认和复用的人物、场景、关键帧、视频与导演台资产。" }),
      ]),
      el("button", { className: "btn primary", text: "回到画布", dataset: { view: "Create" }, attrs: { type: "button" } }),
    ]),
    el("div", { className: "asset-library-layout" }, [
      renderAssetSidebar(state.selectedAssetType || "all"),
      el("section", { className: "asset-grid-panel" }, [
        el("div", { className: "asset-grid" }, assets.map((asset) => renderVisibleAssetCard(asset, selected?.asset_id))),
      ]),
      renderVisibleAssetPreview(selected, workspace),
    ]),
  ]);
}

export function renderVisibleAssetsPanel(state, workspace = {}) {
  const allAssets = visibleAssets(state);
  const selected = allAssets.find((asset) => asset.asset_id === state.selectedVisibleAssetId) || allAssets[0];
  return el("aside", { className: "canvas-assets-panel" }, [
    el("header", {}, [
      el("strong", { text: "可用资产" }),
      el("button", { text: "查看全部", dataset: { view: "Assets" }, attrs: { type: "button" } }),
    ]),
    el("div", { className: "compact-asset-list" }, allAssets.slice(0, 5).map((asset) => renderVisibleAssetCard(asset, selected.asset_id))),
    renderVisibleAssetPreview(selected, workspace),
  ]);
}

export function renderVisibleAssetShelf() {
  return el("div", { className: "compact-asset-list" }, visibleAssets().slice(0, 4).map((asset) => renderVisibleAssetCard(asset, "")));
}

function renderAssetSidebar(activeType) {
  return el("aside", { className: "asset-filter-sidebar" }, [
    el("input", { className: "asset-search", attrs: { type: "search", placeholder: "搜索资产", autocomplete: "off" } }),
    el("div", { className: "asset-filter-list" }, FILTERS.map(([type, label]) =>
      el("button", {
        className: type === activeType ? "active" : "",
        text: label,
        dataset: { visibleAssetType: type },
        attrs: { type: "button" },
      }),
    )),
    el("div", { className: "applied-context" }, [
      badge("已应用项目风格", "active"),
      badge("已参考上次反馈", "quiet"),
      badge("已保持角色一致性", "quiet"),
    ]),
  ]);
}

function renderVisibleAssetCard(asset, selectedId) {
  return el("article", {
    className: `visible-asset-card${asset.asset_id === selectedId ? " selected" : ""}`,
    dataset: { visibleAssetId: asset.asset_id },
  }, [
    el("div", { className: `visible-asset-thumb ${asset.asset_type}` }, [el("span", { text: asset.title.slice(0, 2) })]),
    el("strong", { text: asset.title }),
    el("small", { text: `${asset.linked_shot_id} / ${asset.status}` }),
    el("p", { text: asset.safe_summary }),
    el("div", { className: "visible-asset-actions" }, [
      button("设为参考", "set-visible-asset-reference", "ghost", { visibleAssetId: asset.asset_id }),
      button("用于当前镜头", "apply-visible-asset-to-shot", "ghost", { visibleAssetId: asset.asset_id }),
      button("重新生成", "regenerate-visible-asset", "ghost", { visibleAssetId: asset.asset_id }),
      button("查看来源", "inspect-visible-asset-source", "ghost", { visibleAssetId: asset.asset_id }),
    ]),
  ]);
}

function renderVisibleAssetPreview(asset) {
  return el("aside", { className: "asset-preview-panel" }, [
    el("div", { className: `asset-preview-hero ${asset.asset_type}` }, [el("span", { text: asset.title })]),
    el("h2", { text: asset.title }),
    badge(asset.status, statusTone(asset.status)),
    el("p", { text: asset.safe_summary }),
    el("div", { className: "asset-preview-actions" }, [
      button("加入导演台", "apply-visible-asset-to-shot", "primary", { visibleAssetId: asset.asset_id }),
      button("设为参考", "set-visible-asset-reference", "secondary", { visibleAssetId: asset.asset_id }),
    ]),
    el("p", { className: "subtle-note", text: "已应用项目风格，已参考上次反馈，并保持角色与场景一致性。" }),
  ]);
}

function filteredAssets(type, state = {}) {
  const assets = visibleAssets(state);
  if (type === "all") return assets;
  if (type === "character_turnaround") {
    return assets.filter((asset) => ["character_turnaround", "character_avatar", "costume_version"].includes(asset.asset_type));
  }
  return assets.filter((asset) => asset.asset_type === type);
}

function statusTone(status) {
  if (status === "已完成") return "active";
  if (status === "生成中") return "ready";
  if (status === "排队中") return "quiet";
  return "blocked";
}
