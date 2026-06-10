import { badge, button, el, textareaField } from "./dom.js";
import { zoomPercent } from "./canvas-interactions.js";
import { displayStatus, displayText } from "./display-labels.js";
import { renderHistoryPanel } from "./render-studio-history.js";
import { renderResourceEntryPanel } from "./render-studio-resource-entry.js";
import { renderToolboxPanel } from "./render-studio-toolbox.js";

export function renderBottomToolbar(panel, workspace, state) {
  const counts = workspace.counts || {};
  return el("footer", { className: "libtv-bottom-bar" }, [
    toolButton("assets", "资产管理", "▥", panel === "assets"),
    toolButton("add", "添加节点", "+", panel === "add"),
    toolButton("toolbox", "工具箱", "⌘", panel === "toolbox"),
    toolButton("history", "历史资产", "◴", panel === "history"),
    toolButton("shortcuts", "快捷键", "⌨", panel === "shortcuts"),
    toolButton("help", "帮助中心", "?", panel === "help"),
    canvasButton("zoom-out", "缩小画布", "−"),
    el("button", { className: "libtv-zoom", text: zoomPercent(state), dataset: { canvasAction: "zoom-reset" }, attrs: { type: "button", title: "重置画布" } }),
    canvasButton("zoom-in", "放大画布", "+"),
    counts.provider_blockers ? badge(`${counts.provider_blockers} 个门禁`, "blocked") : null,
  ]);
}

export function renderFloatingPanel(panel, workspace, selected, state) {
  if (panel === "add") return renderAddNodeMenu();
  if (panel === "assets") return renderAssetsPanel(workspace.side_rail || {}, workspace.counts || {});
  if (panel === "resource") return renderResourceEntryPanel(state.studioResourceMode, workspace);
  if (panel === "toolbox") return renderToolboxPanel(state);
  if (panel === "history") return renderHistoryPanel(workspace);
  if (panel === "shortcuts") return renderShortcutsPanel();
  if (panel === "help") return renderHelpPanel();
  if (panel === "inspector") return renderInspectorPanel(selected, state);
  if (panel === "gate") return renderGatePanel(workspace);
  return null;
}

function toolButton(panel, label, icon, active) {
  return el("button", {
    className: `libtv-tool${active ? " active" : ""}`,
    dataset: { studioTool: panel },
    attrs: { type: "button", title: label, "aria-label": label },
  }, [
    el("span", { text: icon }),
    el("small", { text: label }),
  ]);
}

function canvasButton(action, label, icon) {
  return el("button", {
    className: "libtv-tool libtv-canvas-tool",
    dataset: { canvasAction: action },
    attrs: { type: "button", title: label, "aria-label": label },
  }, [el("span", { text: icon })]);
}

function renderAddNodeMenu() {
  const nodeItems = [
    ["text", "文本", "剧本、广告词、品牌文案", ""],
    ["image", "图片", "海报、分镜、角色设计", ""],
    ["video", "视频", "创意广告、动画、电影", ""],
    ["video_merge", "视频合成", "多个视频片段合为一个", "Beta"],
    ["director", "导演台", "搭建3D场景，截图作为构图参考", "NEW"],
    ["audio", "音频", "音效、配音、音乐", ""],
    ["script", "脚本", "创意脚本、生成故事板", "Beta"],
  ];
  const resourceItems = [
    ["upload", "上传", "可上传图片、视频、音频文件", ""],
    ["history", "从生成历史选择", "从历史生成中选择素材", ""],
  ];
  return el("div", { className: "libtv-floating libtv-add-menu" }, [
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

function renderAssetsPanel(sideRail, counts) {
  const assets = Array.isArray(sideRail.assets) ? sideRail.assets : [];
  const groups = groupedAssets(assets);
  const meta = assets.length ? `${counts.assets || assets.length} 个素材` : "3 个入口";
  return el("aside", { className: "libtv-side-panel libtv-assets-panel" }, [
    renderPanelHeader("资产管理", meta),
    el("input", { className: "libtv-search", attrs: { placeholder: "请输入搜索内容", autocomplete: "off" } }),
    el("div", { className: "libtv-asset-tabs" }, [
      el("button", { className: "active", text: "全部", attrs: { type: "button" } }),
      el("button", { text: "图片", attrs: { type: "button" } }),
      el("button", { text: "视频", attrs: { type: "button" } }),
      el("button", { text: "文本", attrs: { type: "button" } }),
    ]),
    groups.length ? el("div", { className: "libtv-asset-groups" }, groups.map(renderAssetGroup)) : renderEmpty("暂无资产"),
  ]);
}

function groupedAssets(assets) {
  const seed = [
    ["项目输入", assets.filter((asset) => ["brief", "reference", "source"].includes(asset.asset_type))],
    ["生成候选", assets.filter((asset) => ["image", "video", "scene", "candidate"].includes(asset.asset_type))],
    ["记忆证据", assets.filter((asset) => ["memory", "review", "report"].includes(asset.asset_type))],
  ];
  return seed
    .map(([title, items]) => [title, items.length ? items : fallbackAssets(title)])
    .filter(([, items]) => items.length);
}

function fallbackAssets(title) {
  const samples = {
    项目输入: [{ asset_type: "brief", label: "主需求摘要", summary: "用于运行规划的短内容项目目标" }],
    生成候选: [{ asset_type: "scene", label: "候选分镜", summary: "等待首轮检查后进入审片" }],
    记忆证据: [{ asset_type: "memory", label: "风格偏好", summary: "审片后才可写入候选记忆" }],
  };
  return samples[title] || [];
}

function renderShortcutsPanel() {
  const groups = [
    ["创作", ["连线 Ctrl + L", "生成 Ctrl + Enter", "新建节点 Tab", "复制节点 Alt + 拖动"]],
    ["缩放", ["放大 Ctrl + +", "缩小 Ctrl + -", "适应画布 Ctrl + 0"]],
    ["移动画布", ["按住 Space 拖动画布", "整理画布 Alt + Shift + F"]],
    ["其他", ["撤销 Ctrl + Z", "重做 Ctrl + Shift + Z", "删除 Delete"]],
  ];
  return el("div", { className: "libtv-floating libtv-shortcuts-panel" }, groups.map(([title, items]) =>
    el("section", {}, [
      el("h3", { text: title }),
      ...items.map((item) => el("p", { text: item })),
    ]),
  ));
}

function renderHelpPanel() {
  const items = [
    ["画布操作", "双击或添加节点开始，底部工具负责缩放、历史和辅助。"],
    ["素材安全", "这里只登记安全摘要，不读取本地私有素材字节。"],
    ["生成能力门", "真实模型调用必须经过能力门和用户授权。"],
    ["审片记忆", "审片反馈只进入候选证据，不自动晋升长期记忆。"],
  ];
  return el("div", { className: "libtv-floating libtv-help-panel" }, [
    renderPanelHeader("帮助中心", "本地工作台边界"),
    ...items.map(([title, summary]) =>
      el("section", {}, [
        el("strong", { text: title }),
        el("p", { text: summary }),
      ]),
    ),
  ]);
}

function renderInspectorPanel(card, state) {
  const fields = card.inspector || {};
  return el("aside", { className: "libtv-side-panel libtv-inspector-panel" }, [
    renderPanelHeader("节点检查器", displayStatus(card.status || "not_started")),
    el("strong", { text: displayText(card.title || "未选择节点") }),
    card.summary ? el("p", { text: displayText(card.summary) }) : null,
    textareaField("提示词", "inspector-prompt", displayText(fields.prompt || state.inspectorPrompt), { rows: "4" }),
    textareaField("参考摘要", "inspector-reference-summary", displayText(fields.reference_summary || state.inspectorReferenceSummary), { rows: "3" }),
    textareaField("风格方向", "inspector-style-direction", displayText(fields.style_direction || state.inspectorStyleDirection), { rows: "3" }),
    button("保存检查器", "update-scene-inspector", "primary"),
  ]);
}

function renderGatePanel(workspace) {
  const blockers = Array.isArray(workspace.operations_summary?.provider_blockers) ? workspace.operations_summary.provider_blockers : [];
  return el("div", { className: "libtv-floating libtv-gate-panel" }, [
    renderPanelHeader("生成能力门", displayStatus(workspace.provider_status || "ready_not_run")),
    blockers.length
      ? el("div", { className: "libtv-panel-list" }, blockers.map((item) => el("p", { text: displayText(item.message || item.blocker_id) })))
      : el("p", { text: "当前只显示安全预检状态，不会启动真实模型调用。" }),
    workspace.operations_summary?.primary_artifact_id ? button("查看预检证据", "open-artifact-ref", "ghost", { artifactId: workspace.operations_summary.primary_artifact_id }) : null,
  ]);
}

function renderPanelHeader(title, meta) {
  return el("header", { className: "libtv-panel-header" }, [
    el("h2", { text: title }),
    meta ? el("span", { text: meta }) : null,
  ]);
}

function renderAssetRow(asset) {
  return el("article", { className: "libtv-list-row" }, [
    el("span", { className: "node-icon", text: nodeIcon(asset.asset_type || "source") }),
    el("strong", { text: displayText(asset.label || "素材") }),
    el("small", { text: displayText(asset.summary || asset.asset_type || "安全摘要") }),
  ]);
}

function renderAssetGroup([title, items]) {
  return el("section", { className: "libtv-asset-group" }, [
    el("header", {}, [
      el("strong", { text: title }),
      el("span", { text: `${items.length} 个` }),
    ]),
    ...items.map(renderAssetRow),
  ]);
}

function renderEmpty(text) {
  return el("div", { className: "libtv-empty-state" }, [
    el("span", { text: "□" }),
    el("strong", { text }),
  ]);
}

function nodeIcon(kind) {
  const icons = {
    brief: "☰",
    source: "▧",
    script: "▤",
    scene: "▦",
    review: "▶",
    memory: "◇",
    gate: "⚡",
    image: "▧",
    audio: "♫",
  };
  return icons[kind] || "□";
}
