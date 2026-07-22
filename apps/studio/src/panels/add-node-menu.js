import { NODE_TYPES, NODE_MENU_ORDER, createNode, connect, downstreamTypesFor, effectiveHeight } from "../nodes.js";
import { clientToCanvasPoint, screenToWorld, rectsIntersect } from "../geometry.js";
import { visibleCanvasFrame } from "../canvas-safe-area.js";
import { showPopover, el } from "../overlay.js";
import { icon } from "../icons.js";
import { ACTION_GROUPS, createActionNode } from "../action-registry.js";

const QUICK_ACTION_IDS = ["node_text", "node_script", "node_sequence", "asset_character", "node_image", "node_video"];
const HANDLE_PRIMARY_TYPES = ["text", "script", "sequence", "scene", "shot", "character", "location", "prop", "ref", "image", "video"];

export function openAddNodeMenu(store, runtime, screenPoint, anchorEl = null) {
  let closeRef = () => {};
  const pop = buildMenu((action) => {
    const point = canvasPointFromMenuPoint(screenPoint);
    const world = screenToWorld(store.get().viewport, point.x, point.y);
    const position = openPositionNear(store, action, world.x - 140, world.y - 40);
    spawn(store, action, position.x, position.y);
  }, () => closeRef());
  bindDynamicMenuPosition(pop, () => closeRef);
  if (anchorEl) {
    closeRef = showPopover(anchorEl, pop, { place: "top" });
    return closeRef;
  }
  const anchorPoint = clientPointFromMenuPoint(screenPoint);
  const anchor = el("div");
  anchor.style.cssText = `position:fixed;left:${anchorPoint.x}px;top:${anchorPoint.y}px;width:1px;height:1px;pointer-events:none;`;
  document.body.appendChild(anchor);
  closeRef = showPopover(anchor, pop, { place: "bottom", onClose: () => anchor.remove() });
  return closeRef;
}

function canvasPointFromMenuPoint(point) {
  if (point?.coordinateSpace === "canvas") return { x: point.x, y: point.y };
  return clientToCanvasPoint(point?.x || 0, point?.y || 0);
}

function clientPointFromMenuPoint(point) {
  if (point?.coordinateSpace !== "canvas") return { x: point?.x || 0, y: point?.y || 0 };
  const rect = document.getElementById("canvas-root")?.getBoundingClientRect?.();
  return {
    x: (rect?.left || 0) + Number(point.x || 0),
    y: (rect?.top || 0) + Number(point.y || 0),
  };
}

export function openReferenceMenu(store, runtime, fromNode, anchorEl, options = {}) {
  const direction = options.direction || "downstream";
  const allowed = new Set(direction === "upstream" ? upstreamTypesFor(fromNode.type) : downstreamTypesFor(fromNode.type));
  const pop = el("div");
  pop.classList.add("compact-create-menu", "handle-create-menu");
  pop.appendChild(el("div", "menu-title", direction === "upstream" ? "添加上游" : "添加下游"));
  const primary = HANDLE_PRIMARY_TYPES.filter((type) => allowed.has(type));
  const advanced = NODE_MENU_ORDER.filter((type) => allowed.has(type) && !primary.includes(type) && type !== "library");
  const items = primary.length ? primary : [...allowed].filter((type) => type && NODE_TYPES[type]);
  for (const type of items) {
    const def = NODE_TYPES[type];
    const item = menuItem(def.icon, handleLabel(type, def), handleTag(type));
    item.addEventListener("click", () => {
      const x = direction === "upstream" ? fromNode.x - def.size.w - 160 : fromNode.x + fromNode.w + 160;
      const node = spawn(store, { id: `node_${type}`, type, label: handleLabel(type, def) }, x, fromNode.y);
      if (direction === "upstream") connect(store, node.id, fromNode.id);
      else connect(store, fromNode.id, node.id);
      close();
    });
    pop.appendChild(item);
  }
  if (advanced.length) {
    const details = el("details", "advanced-create-list handle-advanced-list");
    details.appendChild(el("summary", "advanced-create-summary", "更多/高级"));
    const content = el("div", "advanced-create-content");
    for (const type of advanced) {
      const def = NODE_TYPES[type];
      const item = menuItem(def.icon, handleLabel(type, def), handleTag(type));
      item.addEventListener("click", () => {
        const x = direction === "upstream" ? fromNode.x - def.size.w - 160 : fromNode.x + fromNode.w + 160;
        const node = spawn(store, { id: `node_${type}`, type, label: handleLabel(type, def) }, x, fromNode.y);
        if (direction === "upstream") connect(store, node.id, fromNode.id);
        else connect(store, fromNode.id, node.id);
        close();
      });
      content.appendChild(item);
    }
    details.appendChild(content);
    pop.appendChild(details);
  }
  const close = showPopover(anchorEl, pop, { place: "right" });
}

function buildMenu(onPick, onDone) {
  const pop = el("div");
  pop.classList.add("action-registry-menu", "compact-create-menu");
  pop.appendChild(quickCreatePanel(onPick, onDone));
  const advanced = el("details", "advanced-create-list");
  advanced.appendChild(el("summary", "advanced-create-summary", "更多/高级"));
  const content = el("div", "advanced-create-content");
  for (const group of ACTION_GROUPS) {
    if (group.id === "basic_nodes") continue;
    content.appendChild(el("div", "menu-title", group.label));
    for (const action of group.actions) {
      const item = menuItem(action.icon, action.label, action.tag, action.requires_gate);
      item.addEventListener("click", () => {
        onPick(action);
        onDone();
      });
      content.appendChild(item);
    }
  }
  advanced.appendChild(content);
  pop.appendChild(advanced);
  return pop;
}

function bindDynamicMenuPosition(pop, closeRef) {
  pop.addEventListener("toggle", (event) => {
    if (!event.target?.matches?.(".advanced-create-list")) return;
    requestAnimationFrame(() => closeRef()?.reposition?.());
  }, true);
}

function quickCreatePanel(onPick, onDone) {
  const panel = el("div", "quick-create-panel");
  panel.appendChild(el("div", "quick-create-title", "从这里开始"));
  panel.appendChild(el("div", "quick-create-hint", "选择常用入口；专家类型在更多/高级里。"));
  const grid = el("div", "quick-create-grid");
  for (const action of quickActions()) {
    const item = el("button", "quick-create-card");
    item.dataset.tone = quickTone(action);
    item.innerHTML = [
      `<span class="quick-create-icon">${icon(action.icon, 15)}</span>`,
      `<span><strong>${action.label}</strong><small>${quickHint(action)}</small></span>`,
    ].join("");
    item.addEventListener("click", () => {
      onPick(action);
      onDone();
    });
    grid.appendChild(item);
  }
  panel.appendChild(grid);
  return panel;
}

function quickActions() {
  const actions = ACTION_GROUPS.flatMap((group) => group.actions);
  return QUICK_ACTION_IDS.map((id) => actions.find((action) => action.id === id)).filter(Boolean);
}

function quickTone(action) {
  return {
    node_text: "story",
    node_image: "scene",
    node_video: "video",
    node_script: "story",
    node_sequence: "revision",
    asset_character: "character",
    node_ref: "scene",
    node_director: "revision",
  }[action.id] || "story";
}

function quickHint(action) {
  return {
    node_text: "写想法",
    node_image: "上传或描述",
    node_video: "导入或生成预览",
    node_script: "导入/改写",
    node_sequence: "拆场景镜头",
    asset_character: "角色/道具/空间",
    node_ref: "上传参考",
    node_director: "控镜头",
  }[action.id] || "新节点";
}

function handleLabel(type, def) {
  return {
    text: "想法/文本",
    script: "剧本/导入",
    sequence: "场景与镜头",
    scene: "场景故事单元",
    shot: "镜头设计",
    character: "角色设定",
    location: "空间设定",
    prop: "道具设定",
    ref: "参考资料",
    image: "参考图/图片",
    video: "视频",
    audio: "音频",
    video_merge: "剪辑合成草稿",
    director: "镜头调度板",
  }[type] || def.label;
}

function handleTag(type) {
  return {
    video_merge: "高级",
    director: "高级",
    audio: "高级",
  }[type] || "";
}

function spawn(store, action, wx, wy) {
  const position = clampNodePositionToVisibleFrame(store, action, wx, wy);
  if (action?.type === "library") {
    const node = createNode(store, "text", position.x, position.y);
    store.set((s) => {
      const n = s.nodes[node.id];
      n.params.actionId = action.id;
      n.params.actionLabel = action.label;
      n.title = action.label || "素材库";
      n.content = `${action.label || "素材库"}：从项目素材、生成历史或固定资产中选择引用。`;
      n.h = 160;
      n.status = "complete";
    });
    return node;
  }
  return createActionNode(store, action, position.x, position.y);
}

function upstreamTypesFor(targetType) {
  return NODE_MENU_ORDER.filter((type) => downstreamTypesFor(type).includes(targetType));
}

function openPositionNear(store, action, wx, wy) {
  const nodeType = nodeTypeForAction(action);
  const def = NODE_TYPES[nodeType] || NODE_TYPES.text;
  const base = { x: Math.round(wx), y: Math.round(wy), w: def.size.w, h: def.size.h };
  const visibleBounds = visibleNodeWorldBounds(store.get().viewport, def);
  const existing = Object.values(store.get().nodes || {}).map((node) => ({
    x: node.x - 28,
    y: node.y - 28,
    w: node.w + 56,
    h: effectiveHeight(node) + 56,
  }));
  const stepX = Math.max(base.w + 80, 360);
  const stepY = Math.max(base.h + 80, 330);
  const offsets = [
    [0, 0],
    [stepX, 0],
    [0, stepY],
    [stepX, stepY],
    [-stepX, 0],
    [0, -stepY],
    [stepX * 2, 0],
    [-stepX, stepY],
    [stepX, -stepY],
    [0, stepY * 2],
  ];
  for (const [dx, dy] of offsets) {
    const candidate = clampRectToBounds({ ...base, x: base.x + dx, y: base.y + dy }, visibleBounds);
    if (!existing.some((rect) => rectsIntersect(candidate, rect))) return candidate;
  }
  return clampRectToBounds({ ...base, x: base.x + stepX * (existing.length + 1), y: base.y }, visibleBounds);
}

function clampNodePositionToVisibleFrame(store, action, wx, wy) {
  const def = NODE_TYPES[nodeTypeForAction(action)] || NODE_TYPES.text;
  const rect = clampRectToBounds({ x: Math.round(wx), y: Math.round(wy), w: def.size.w, h: def.size.h }, visibleNodeWorldBounds(store.get().viewport, def));
  return { x: rect.x, y: rect.y };
}

function nodeTypeForAction(action) {
  return action?.type === "library" ? "text" : action?.type || "text";
}

function visibleNodeWorldBounds(viewport, def) {
  const frame = visibleCanvasFrame();
  if (!frame.visible || frame.width < 160 || frame.height < 160) return null;
  const margin = 24;
  const left = (frame.safeArea?.left || 0) + margin;
  const top = (frame.safeArea?.top || 0) + margin;
  const right = frame.width - (frame.safeArea?.right || 0) - def.size.w - margin;
  const bottom = frame.height - (frame.safeArea?.bottom || 0) - def.size.h - margin;
  if (right < left || bottom < top) return null;
  const topLeft = screenToWorld(viewport, left, top);
  const bottomRight = screenToWorld(viewport, right, bottom);
  return {
    minX: Math.min(topLeft.x, bottomRight.x),
    maxX: Math.max(topLeft.x, bottomRight.x),
    minY: Math.min(topLeft.y, bottomRight.y),
    maxY: Math.max(topLeft.y, bottomRight.y),
  };
}

function clampRectToBounds(rect, bounds) {
  if (!bounds) return rect;
  return {
    ...rect,
    x: Math.round(Math.min(Math.max(rect.x, bounds.minX), bounds.maxX)),
    y: Math.round(Math.min(Math.max(rect.y, bounds.minY), bounds.maxY)),
  };
}

function menuItem(iconName, label, tag, gate) {
  const item = el("button", "menu-item");
  item.innerHTML = [
    `<span class="mi-icon">${icon(iconName, 14)}</span>`,
    `<span><span>${label}</span>${gate ? `<span class="mi-sub">需要 ${gate}</span>` : ""}</span>`,
    tag ? `<span class="mi-tag${tag === "NEW" ? " new" : ""}">${tag}</span>` : "",
  ].join("");
  return item;
}
