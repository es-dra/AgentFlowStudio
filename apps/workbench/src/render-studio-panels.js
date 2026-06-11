import { el } from "./dom.js";
import { zoomPercent } from "./canvas-interactions.js";
import { displayText } from "./display-labels.js";
import { renderHistoryPanel } from "./render-studio-history.js";
import { renderResourceEntryPanel } from "./render-studio-resource-entry.js";
import { renderToolboxPanel } from "./render-studio-toolbox.js";
import { visibleAssets } from "./render-visible-assets.js";
import { canvasNavigatorMetrics } from "./canvas-viewport-actions.js";

export function renderBottomToolbar(panel, workspace, state) {
  return el("footer", { className: "libtv-bottom-bar" }, [
    toolButton("assets", "资产管理", "AST", panel === "assets"),
    toolButton("add", "添加节点", "+", panel === "add"),
    toolButton("toolbox", "工具箱", "KIT", panel === "toolbox"),
    toolButton("material", "素材库", "MAT", panel === "material"),
    toolButton("history", "历史记录", "HIS", panel === "history"),
    toolButton("shortcuts", "快捷键", "KEY", panel === "shortcuts"),
    toolButton("help", "帮助中心", "?", panel === "help"),
    quickTool("map", "小地图", "MAP"),
    quickTool("grid", "网格吸附", "GRID"),
    canvasButton("zoom-out", "缩小画布", "-"),
    el("button", { className: "libtv-zoom", text: zoomPercent(state), dataset: { canvasAction: "zoom-reset" }, attrs: { type: "button", title: "重置画布" } }),
    canvasButton("zoom-in", "放大画布", "+"),
  ]);
}

export function renderFloatingPanel(panel, workspace, selected, state) {
  if (panel === "add") return renderAddNodeMenu(state);
  if (panel === "assets") return renderAssetsPanel(state);
  if (panel === "resource") return renderResourceEntryPanel(state.studioResourceMode, workspace);
  if (panel === "material") return renderMaterialPanel();
  if (panel === "toolbox") return renderToolboxPanel(state);
  if (panel === "history") return renderHistoryPanel(workspace);
  if (panel === "map") return renderCanvasNavigator(state);
  if (panel === "shortcuts") return renderShortcutsPanel();
  if (panel === "help") return renderHelpPanel();
  return null;
}

function toolButton(panel, label, icon, active) {
  return el("button", {
    className: `libtv-tool${active ? " active" : ""}`,
    dataset: { studioTool: panel },
    attrs: { type: "button", title: label, "aria-label": label },
  }, [el("span", { text: icon }), el("small", { text: label })]);
}

function quickTool(kind, label, icon) {
  const dataset = { toolboxIntent: kind };
  if (kind === "map") dataset.studioTool = "map";
  return el("button", {
    className: "libtv-tool",
    dataset,
    attrs: { type: "button", title: label, "aria-label": label },
  }, [el("span", { text: icon }), el("small", { text: label })]);
}

function canvasButton(action, label, icon) {
  return el("button", {
    className: "libtv-tool libtv-canvas-tool",
    dataset: { canvasAction: action },
    attrs: { type: "button", title: label, "aria-label": label },
  }, [el("span", { text: icon })]);
}

function renderAddNodeMenu(state = {}) {
  const nodeItems = [
    ["text", "文本", "剧本、广告词、品牌文案", ""],
    ["image", "图片", "海报、分镜、角色设计", ""],
    ["video", "视频", "创意广告、动画、电影感镜头", ""],
    ["video_merge", "视频合成", "多个视频片段合成为一个", "Beta"],
    ["director", "导演台", "搭建场景，截图作为构图参考", "NEW"],
    ["audio", "音频", "音效、配音、音乐", ""],
    ["script", "脚本", "创意脚本、生成故事板", "Beta"],
  ];
  const resourceItems = [
    ["upload", "上传", "上传图片、视频、音频文件", ""],
    ["history", "从生成历史选择", "从历史生成中选择素材", ""],
  ];
  const anchored = Number(state.canvasAddMenuScreenX || 0) > 0 || Number(state.canvasAddMenuScreenY || 0) > 0;
  const attrs = anchored
    ? { style: `left:${Math.max(12, Number(state.canvasAddMenuScreenX || 0))}px;top:${Math.max(12, Number(state.canvasAddMenuScreenY || 0))}px;bottom:auto;` }
    : {};
  return el("div", { className: `libtv-floating libtv-add-menu${anchored ? " canvas-anchored-add-menu" : ""}`, attrs }, [
    renderPanelHeader("添加节点", ""),
    el("section", { className: "libtv-node-palette" }, nodeItems.map((item) => renderAddMenuItem(item))),
    el("section", { className: "libtv-add-resource-section" }, [
      el("h3", { text: "添加资源" }),
      ...resourceItems.map((item) => renderAddMenuItem(item, "addResourceKind", "选择")),
    ]),
  ]);
}

function renderAddMenuItem([kind, title, summary, status], datasetKey = "addNodeKind", action = "添加") {
  return el("button", { dataset: { [datasetKey]: kind }, attrs: { type: "button" } }, [
    el("span", { className: "node-icon", text: nodeIcon(kind) }),
    el("strong", { text: title }),
    el("small", { text: summary }),
    status ? el("em", { className: "libtv-node-badge", text: status }) : el("em", { className: "libtv-node-action", text: action }),
  ]);
}

function renderAssetsPanel(state) {
  const activeTab = state.studioSidebarTab || "canvas";
  return el("aside", { className: "libtv-side-panel libtv-assets-panel canvas-asset-drawer" }, [
    el("header", { className: "canvas-drawer-head" }, [
      el("strong", { text: state.studioProjectTitle || "未命名项目" }),
      el("span", { text: "画布 1" }),
    ]),
    el("div", { className: "canvas-drawer-tabs" }, [
      drawerTab("canvas", "画布", activeTab),
      drawerTab("asset", "资产", activeTab),
    ]),
    activeTab === "asset" ? renderVisibleAssetDrawer() : renderCanvasNodeDrawer(),
  ]);
}

function drawerTab(tab, label, activeTab) {
  return el("button", {
    className: tab === activeTab ? "active" : "",
    text: label,
    attrs: { type: "button", "data-studio-sidebar-tab": tab },
  });
}

function renderCanvasNodeDrawer() {
  const nodes = [
    ["script-input", "TXT", "剧本输入"], ["storyboard", "SHOT", "分镜脚本"],
    ["character", "CHR", "角色三视图"], ["scene", "SCN", "场景资产"],
    ["keyframe", "KEY", "关键帧"], ["director", "DIR", "导演台"],
    ["clip", "VID", "视频片段"], ["compose", "CUT", "成片合成"],
  ];
  return el("section", { className: "canvas-drawer-body" }, [
    el("input", { className: "libtv-search", attrs: { placeholder: "搜索节点", autocomplete: "off" } }),
    el("div", { className: "canvas-node-list" }, nodes.map(([id, icon, title]) =>
      el("button", { dataset: { cardId: id, canvasAction: "center-node", canvasNodeId: id }, attrs: { type: "button" } }, [
        el("span", { className: "node-icon", text: icon }),
        el("strong", { text: title }),
        el("small", { text: "定位到节点" }),
      ]),
    )),
    el("footer", { text: `共 ${nodes.length} 节点` }),
  ]);
}

function renderVisibleAssetDrawer() {
  const assets = visibleAssets();
  return el("section", { className: "canvas-drawer-body" }, [
    el("input", { className: "libtv-search", attrs: { placeholder: "搜索资产", autocomplete: "off" } }),
    el("button", { className: "asset-type-filter", text: "筛选素材类型", attrs: { type: "button" } }),
    assets.length ? el("div", { className: "canvas-asset-list" }, assets.map(renderAssetRow)) : renderEmpty("暂无资产"),
  ]);
}

function renderCanvasNavigator(state) {
  const metrics = canvasNavigatorMetrics(state);
  const miniWidth = 238;
  const miniHeight = 150;
  const scale = Math.min(miniWidth / metrics.bounds.width, miniHeight / metrics.bounds.height);
  return el("div", { className: "libtv-floating canvas-navigator-panel" }, [
    renderPanelHeader("小地图", ""),
    el("div", { className: "canvas-mini-map" }, [
      ...metrics.nodes.map((node) => el("span", {
        className: `canvas-mini-node${node.selected ? " selected" : ""}`,
        attrs: { style: miniStyle(node.x, node.y, 18, 12, scale), title: node.id },
      })),
      el("span", {
        className: "canvas-mini-viewport",
        attrs: { style: miniStyle(metrics.viewportRect.left - metrics.bounds.left, metrics.viewportRect.top - metrics.bounds.top, metrics.viewportRect.width, metrics.viewportRect.height, scale) },
      }),
    ]),
    el("div", { className: "canvas-navigator-actions" }, [
      el("button", { text: "适配流程", attrs: { type: "button", "data-canvas-action": "fit-view" } }),
      el("button", { text: "定位选中", attrs: { type: "button", "data-canvas-action": "center-selection" } }),
      el("button", { text: "100%", attrs: { type: "button", "data-canvas-action": "zoom-reset" } }),
    ]),
  ]);
}

function miniStyle(x, y, width, height, scale) {
  return `left:${Math.round(x * scale)}px;top:${Math.round(y * scale)}px;width:${Math.max(5, Math.round(width * scale))}px;height:${Math.max(5, Math.round(height * scale))}px;`;
}

function renderMaterialPanel() {
  return el("div", { className: "libtv-floating libtv-material-panel" }, [
    renderPanelHeader("素材库", ""),
    ...[["风格库", "新增风格节点", "NEW"], ["特效库", "新增特效节点", "NEW"]].map(([title, summary, tag]) =>
      el("button", { attrs: { type: "button" } }, [
        el("span", { className: "node-icon", text: "MAT" }),
        el("strong", { text: title }),
        el("small", { text: summary }),
        el("em", { text: tag }),
      ]),
    ),
  ]);
}

function renderShortcutsPanel() {
  const groups = [
    ["创作", ["成组 Ctrl+Alt+G", "连线 Ctrl+L", "生成 Ctrl+Enter", "新建节点 Tab"]],
    ["缩放", ["放大 Ctrl++", "缩小 Ctrl+-", "适应画布 Ctrl+0"]],
    ["移动画布", ["按住 Space 拖动画布", "整理画布 Alt+Shift+F"]],
    ["其他", ["撤销 Ctrl+Z", "重做 Ctrl+Shift+Z", "删除 Delete"]],
  ];
  return el("div", { className: "libtv-floating libtv-shortcuts-panel" }, groups.map(([title, items]) =>
    el("section", {}, [el("h3", { text: title }), ...items.map((item) => el("p", { text: item }))]),
  ));
}

function renderHelpPanel() {
  const items = [
    ["画布操作", "双击或添加节点开始，底部工具负责缩放、历史和辅助。"],
    ["素材安全", "这里只登记安全摘要，不读取本地私有素材字节。"],
    ["提示词优化", "在输入框旁点击优化，把普通描述整理为影视提示词。"],
    ["导演台", "导演台负责机位、布光、人物站位和构图参考。"],
  ];
  return el("div", { className: "libtv-floating libtv-help-panel" }, [
    renderPanelHeader("帮助中心", ""),
    ...items.map(([title, summary]) => el("section", {}, [el("strong", { text: title }), el("p", { text: summary })])),
  ]);
}

function renderPanelHeader(title, meta) {
  return el("header", { className: "libtv-panel-header" }, [
    el("h2", { text: title }),
    meta ? el("span", { text: meta }) : null,
  ]);
}

function renderAssetRow(asset) {
  return el("article", { className: "libtv-list-row", dataset: { visibleAssetId: asset.asset_id || "" } }, [
    el("span", { className: "node-icon", text: nodeIcon(asset.asset_type || "source") }),
    el("strong", { text: displayText(asset.title || asset.label || "素材") }),
    el("small", { text: displayText(asset.safe_summary || asset.summary || asset.asset_type || "安全摘要") }),
  ]);
}

function renderEmpty(text) {
  return el("div", { className: "libtv-empty-state" }, [el("span", { text: "AFS" }), el("strong", { text })]);
}

function nodeIcon(kind) {
  const icons = {
    text: "TXT", image: "IMG", video: "VID", video_merge: "CUT", director: "DIR", audio: "AUD", script: "SCR",
    upload: "UP", history: "HIS", character_turnaround: "CHR", character_avatar: "CHR", costume_version: "CST",
    scene_board: "SCN", director_setup: "DIR", keyframe: "KEY", video_clip: "VID", audio_clip: "AUD",
  };
  return icons[kind] || "AST";
}
