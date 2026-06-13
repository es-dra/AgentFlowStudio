import { promptPlaceholder } from "./nodes.js";
import { MODELS_BY_NODE_TYPE, findModel, isRemoteVideoModel } from "./presets/models.js";
import {
  VIDEO_RATIOS, VIDEO_RESOLUTIONS, VIDEO_DURATIONS,
  videoSpecLabel,
} from "./presets/specs.js";
import { showPopover, el } from "./overlay.js";
import { openOptimizer } from "./optimizer.js";
import { openGalleryModal } from "./panels/gallery-modal.js";
import { pollNodeVideoGeneration, startNodeGeneration } from "./node-actions.js";
import { icon } from "./icons.js";
import { barSignature, positionBar, structureSignature } from "./prompt-bar-position.js";
import { flashTooltip, updateNode } from "./prompt-bar-actions.js";
import { openExpandEditor } from "./prompt-bar-expand.js";

const PROMPT_NODE_TYPES = new Set(["text", "image", "video", "video_merge", "audio", "script"]);

export function renderPromptBar(state, store, runtime) {
  const layer = document.getElementById("prompt-bar-layer");
  const selectedId = state.selection.nodeIds.length === 1 ? state.selection.nodeIds[0] : null;
  const node = selectedId ? state.nodes[selectedId] : null;
  const show = node && PROMPT_NODE_TYPES.has(node.type) && !node.content;

  let bar = layer.querySelector(".prompt-bar");
  if (!show) {
    if (bar) bar.remove();
    return;
  }

  const signature = barSignature(state, node);
  if (!bar || bar.dataset.signature !== signature) {
    if (bar && bar.dataset.nodeId === node.id && isPromptTextEditing(bar) && bar.dataset.structure === structureSignature(node)) {
      bar.dataset.signature = signature;
      positionBar(bar, state, node);
      return;
    }
    const next = buildBar(store, runtime, node);
    next.dataset.signature = signature;
    next.dataset.structure = structureSignature(node);
    if (bar) bar.replaceWith(next);
    else layer.appendChild(next);
    bar = next;
  }
  positionBar(bar, state, node);
}

function isPromptTextEditing(bar) {
  const active = document.activeElement;
  return Boolean(bar.contains(active) && ["TEXTAREA", "INPUT"].includes(active?.tagName));
}

function buildBar(store, runtime, node) {
  const bar = el("div", "prompt-bar");
  bar.dataset.nodeId = node.id;
  const p = node.params;

  if ((p.attachments || []).length) {
    const chips = el("div", "attach-chips");
    for (const att of p.attachments) {
      const chip = el("button", "attach-chip");
      chip.innerHTML = icon("text", 14);
      chip.title = att.label || att.id;
      chip.appendChild(el("span", "badge", "1"));
      chips.appendChild(chip);
    }
    bar.appendChild(chips);
  }

  const textarea = document.createElement("textarea");
  textarea.placeholder = promptPlaceholder(node.type, p.spec?.mode);
  textarea.value = node.prompt || "";
  textarea.addEventListener("input", () => {
    updateNode(store, node.id, (n) => {
      n.prompt = textarea.value;
      delete n.params.lastOptimizedPromptPlain;
    }, { history: false });
  });
  textarea.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      if (node.type !== "image" && !(node.type === "video" && isRemoteVideoModel(node.params?.model))) {
        flashTooltip(textarea, "当前版本仅图片节点支持真实生成");
        return;
      }
      runPromptBarGeneration(store, runtime, node);
    }
  });
  bar.appendChild(textarea);

  if (node.type === "video" || node.type === "script") {
    const expand = el("button", "expand-btn");
    expand.innerHTML = icon("expand", 14);
    expand.title = "放大编辑";
    expand.addEventListener("click", () => openExpandEditor(store, runtime, node));
    bar.appendChild(expand);
  }

  bar.appendChild(buildBottomRow(store, runtime, node, textarea));
  return bar;
}

function buildToolChips(store, node, defs) {
  const wrap = el("div", "tool-chips");
  for (const [label, iconName, onClick] of defs) {
    const chip = el("button", "tool-chip");
    chip.innerHTML = `<span class="tc-icon">${icon(iconName, 14)}</span><span>${label}</span>`;
    if (label === "特效" && node.params.effect) chip.classList.add("active");
    chip.addEventListener("click", onClick);
    wrap.appendChild(chip);
  }
  return wrap;
}

function buildBottomRow(store, runtime, node, textarea) {
  const row = el("div", "bar-row");
  const p = node.params;
  const model = findModel(node.type, p.model);

  const modelBtn = el("button", "bar-select");
  modelBtn.innerHTML = `<span class="sel-icon">${icon("sparkle1", 13)}</span><span>${model.name}</span><span class="caret">▾</span>`;
  modelBtn.addEventListener("click", () => openModelPopover(store, node, modelBtn));
  row.appendChild(modelBtn);

  if (node.type === "video" || node.type === "video_merge") {
    const specBtn = el("button", "bar-select");
    specBtn.innerHTML = `<span class="sel-icon">${icon("frames", 13)}</span><span>${videoSpecLabel(p.spec)}</span><span class="caret">▾</span>`;
    specBtn.addEventListener("click", () => openVideoSpecPopover(store, node, specBtn));
    row.appendChild(specBtn);

    const motionBtn = el("button", `bar-tool${p.motion ? " active" : ""}`);
    motionBtn.innerHTML = `${icon("filmcam", 14)}<span>${p.motion || "运镜"}</span>`;
    motionBtn.addEventListener("click", () => openGalleryModal(store, "motions", node.id));
    row.appendChild(motionBtn);
  }

  row.appendChild(el("span", "row-spacer"));

  const optimizeBtn = el("button", "bar-tool optimize-btn");
  optimizeBtn.dataset.action = "optimize-prompt";
  optimizeBtn.innerHTML = `${icon("sparkles", 14)}<span>优化</span>`;
  optimizeBtn.title = "优化提示词";
  optimizeBtn.addEventListener("click", () => {
    if (!String(store.get().nodes[node.id]?.prompt || "").trim()) {
      flashTooltip(optimizeBtn, "先输入提示词");
      return;
    }
    openOptimizer(store, runtime, node.id, optimizeBtn, textarea);
  });
  row.appendChild(optimizeBtn);

  const send = el("button", "send-btn");
  const canVideo = node.type === "video" && isRemoteVideoModel(node.params?.model);
  const shouldPollVideo = canVideo && node.status === "generating" && Boolean(node.params?.lastVideoJobId);
  send.innerHTML = shouldPollVideo ? icon("retry", 15) : icon("arrowUp", 15);
  const canSend = node.type === "image" || canVideo;
  send.title = node.type === "image" ? "生成" : "视频/音频通道开发中，当前版本仅图片节点支持真实生成";
  if (canSend) send.title = "生成";
  if (shouldPollVideo) send.title = "继续轮询";
  send.disabled = !canSend;
  send.addEventListener("click", () => runPromptBarGeneration(store, runtime, node));
  row.appendChild(send);

  return row;
}

function runPromptBarGeneration(store, runtime, node) {
  const fresh = store.get().nodes[node.id] || node;
  if (fresh.type === "video" && fresh.status === "generating" && fresh.params?.lastVideoJobId) {
    pollNodeVideoGeneration(store, runtime, fresh);
    return;
  }
  startNodeGeneration(store, runtime, fresh);
}

function openModelPopover(store, node, anchor) {
  const models = MODELS_BY_NODE_TYPE[node.type] || [];
  const pop = el("div");
  pop.style.minWidth = "270px";
  for (const m of models) {
    const item = el("button", `menu-item${node.params.model === m.id ? " selected" : ""}`);
    item.innerHTML = `<span class="mi-icon">${icon("sparkle1", 13)}</span><span>${m.name}${m.desc ? `<span class="mi-sub">${m.desc}</span>` : ""}</span><span class="mi-meta">${m.eta}</span>`;
    item.addEventListener("click", () => {
      updateNode(store, node.id, (n) => { n.params.model = m.id; });
      close();
    });
    pop.appendChild(item);
  }
  const close = showPopover(anchor, pop, { place: "top" });
}

function openVideoSpecPopover(store, node, anchor) {
  const pop = el("div", "spec-pop");
  pop.appendChild(specSection("比例", VIDEO_RATIOS, node.params.spec.ratio, (v) =>
    updateNode(store, node.id, (n) => { n.params.spec.ratio = v; })));
  pop.appendChild(specSection("分辨率", VIDEO_RESOLUTIONS, node.params.spec.resolution, (v) =>
    updateNode(store, node.id, (n) => { n.params.spec.resolution = v; })));
  pop.appendChild(specSection("时长", VIDEO_DURATIONS, node.params.spec.duration, (v) =>
    updateNode(store, node.id, (n) => { n.params.spec.duration = v; })));
  pop.appendChild(specSection("声音", ["开", "关"], node.params.spec.sound ? "开" : "关", (v) =>
    updateNode(store, node.id, (n) => { n.params.spec.sound = v === "开"; })));
  showPopover(anchor, pop, { place: "top" });
}

function specSection(label, options, current, onPick, ratio = false) {
  const section = el("div", "spec-section");
  section.appendChild(el("div", "spec-label", label));
  const wrap = el("div", "spec-options");
  for (const opt of options) {
    const btn = el("button", `spec-opt${ratio ? " ratio" : ""}${current === opt ? " active" : ""}`, opt);
    btn.addEventListener("click", () => {
      onPick(opt);
      for (const sib of wrap.children) sib.classList.toggle("active", sib === btn);
    });
    wrap.appendChild(btn);
  }
  section.appendChild(wrap);
  return section;
}
