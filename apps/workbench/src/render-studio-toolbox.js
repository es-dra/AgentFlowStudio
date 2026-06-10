import { el } from "./dom.js";

export function renderToolboxPanel(state = {}) {
  const activeIntent = state.studioToolIntent || "";
  return el("div", { className: "libtv-floating libtv-toolbox-panel" }, [
    renderPanelHeader("TV工具箱", "主体功能骨架"),
    el("div", { className: "libtv-toolbox-body" }, [
      renderToolboxSection("创作工具", tvTools(), "libtv-tv-tool-row", activeIntent),
      renderToolboxSection("画布辅助", canvasTools(), "libtv-toolbox-row", activeIntent),
      renderToolboxStatus(activeIntent),
      renderToolIntentFlow(activeIntent),
      el("p", { className: "libtv-safe-tool-note", text: "仅登记工具意图，真实生成继续由能力门控制。" }),
    ]),
  ]);
}

function renderToolboxSection(title, items, rowClass, activeIntent) {
  return el("section", { className: "libtv-toolbox-section" }, [
    el("h3", { text: title }),
    ...items.map(([kind, itemTitle, summary]) => renderToolboxRow(kind, itemTitle, summary, rowClass, activeIntent)),
  ]);
}

function renderToolboxRow(kind, title, summary, rowClass, activeIntent) {
  const active = activeIntent === kind;
  return el("button", {
    className: `${rowClass}${active ? " active" : ""}`,
    attrs: { type: "button", "data-toolbox-intent": kind, "aria-pressed": active ? "true" : "false" },
  }, [
    el("span", { className: "node-icon", text: nodeIcon(kind) }),
    el("strong", { text: title }),
    el("small", { text: summary }),
  ]);
}

function renderToolboxStatus(activeIntent) {
  return el("section", { className: "libtv-toolbox-status" }, [
    el("h3", { text: "工具回执" }),
    el("strong", { text: activeIntent ? "本地工具意图已登记" : "等待工具选择" }),
    el("p", { text: intentReceipt(activeIntent) }),
    el("small", { text: "未创建真实任务 · 未启动 provider" }),
  ]);
}

function renderToolIntentFlow(activeIntent) {
  const engaged = Boolean(activeIntent);
  const steps = [
    ["工具意图", engaged ? "done" : "pending", engaged ? "已写入当前 Workbench 状态" : "等待工具选择"],
    ["能力门检查", engaged ? "active" : "pending", "等待能力门授权"],
    ["真实生成", "locked", "未创建真实任务"],
  ];
  return el("ol", { className: "libtv-tool-intent-flow" }, steps.map(([label, status, summary]) =>
    el("li", { className: `status-${status}` }, [
      el("span", { text: label }),
      el("small", { text: summary }),
    ]),
  ));
}

function intentReceipt(activeIntent) {
  const labels = {
    angles: "已登记多角度工具意图；等待能力门授权后才可进入真实生成。",
    motion: "已登记运镜标记意图；当前只保存镜头运动方向。",
    keyframes: "已登记首尾帧组织意图；不会读取或上传本地图片。",
    upscale: "已登记图片高清意图；当前不调用 image provider。",
    music: "已登记文字生音乐意图；当前不调用 audio provider。",
    character: "已登记角色库意图；只复用安全摘要和造型约束。",
    fit: "已登记整理画布意图；当前只作为本地画布辅助。",
    map: "已登记小地图意图；后续接大画布定位。",
    grid: "已登记网格吸附意图；当前只作为交互设置。",
    follow: "已登记跟随选中意图；当前只影响本地检查器入口。",
  };
  return labels[activeIntent] || "选择一个工具后，只会更新本地状态。";
}

function tvTools() {
  return [
    ["angles", "多角度", "为角色或首帧准备多视角生成入口"],
    ["motion", "运镜标记", "标注镜头运动、节奏和画面重点"],
    ["keyframes", "首尾帧", "组织首帧、尾帧和视频节点关系"],
    ["upscale", "图片高清", "对候选图片登记高清化意图"],
    ["music", "文字生音乐", "从文本方向进入音乐或音效草案"],
    ["character", "角色库", "复用角色安全摘要和造型约束"],
  ];
}

function canvasTools() {
  return [
    ["fit", "整理画布", "对齐当前生产节点，保持起步画布可扫读"],
    ["map", "切换小地图", "后续接入大画布定位；当前仅保留入口"],
    ["grid", "网格吸附", "保持节点移动时贴合点阵节奏"],
    ["follow", "跟随选中", "点选节点后打开检查器，不展开系统状态"],
  ];
}

function renderPanelHeader(title, meta) {
  return el("header", { className: "libtv-panel-header" }, [
    el("h2", { text: title }),
    meta ? el("span", { text: meta }) : null,
  ]);
}

function nodeIcon(kind) {
  const icons = {
    fit: "⌖",
    map: "▣",
    grid: "▦",
    follow: "◎",
    angles: "◫",
    motion: "↝",
    keyframes: "▥",
    upscale: "⬚",
    music: "♪",
    character: "◉",
  };
  return icons[kind] || "□";
}
