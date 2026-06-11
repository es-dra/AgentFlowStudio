import { promptPlaceholder } from "./nodes.js";
import { MODELS_BY_NODE_TYPE, findModel } from "./presets/models.js";
import {
  IMAGE_QUALITY, IMAGE_RESOLUTION, IMAGE_RATIOS, IMAGE_COUNTS,
  VIDEO_RATIOS, VIDEO_RESOLUTIONS, VIDEO_DURATIONS, VIDEO_COUNTS, VIDEO_MODES,
  imageSpecLabel, videoSpecLabel,
} from "./presets/specs.js";
import { showPopover, el } from "./overlay.js";
import { openOptimizer } from "./optimizer.js";
import { openCameraPopover } from "./panels/camera-popover.js";
import { openGalleryModal } from "./panels/gallery-modal.js";
import { startLocalPreview } from "./node-actions.js";
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
    if (bar && bar.dataset.nodeId === node.id && bar.contains(document.activeElement) && bar.dataset.structure === structureSignature(node)) {
      bar.dataset.signature = signature;
      positionBar(bar, state, node);
      return;
    }
    const next = buildBar(state, store, runtime, node);
    next.dataset.signature = signature;
    next.dataset.structure = structureSignature(node);
    if (bar) bar.replaceWith(next);
    else layer.appendChild(next);
    bar = next;
  }
  positionBar(bar, state, node);
}

function buildBar(state, store, runtime, node) {
  const bar = el("div", "prompt-bar");
  bar.dataset.nodeId = node.id;
  const p = node.params;

  if (node.type === "video") {
    const tabs = el("div", "mode-tabs");
    for (const mode of VIDEO_MODES) {
      const tab = el("button", `mode-tab${p.spec.mode === mode ? " active" : ""}`, mode);
      tab.addEventListener("click", () => updateNode(store, node.id, (n) => { n.params.spec.mode = mode; }));
      tabs.appendChild(tab);
    }
    bar.appendChild(tabs);
    bar.appendChild(buildToolChips(store, runtime, node, [
      ["标记", "pencil", () => {}],
      ["特效", "sparkles", () => openGalleryModal(store, "effects", node.id)],
      ["角色库", "user", () => {}],
    ]));
  }

  if (node.type === "image") {
    bar.appendChild(buildToolChips(store, runtime, node, [
      ["风格", "wand", () => openGalleryModal(store, "styles", node.id)],
      ["标记", "pencil", () => {}],
    ], p.spec.panorama));
  }

  if ((p.attachments || []).length) {
    const chips = el("div", "attach-chips");
    for (const att of p.attachments) {
      const chip = el("button", "attach-chip");
      chip.innerHTML = icon("text", 14);
      chip.title = att.label || att.id;
      const badge = el("span", "badge", "1");
      chip.appendChild(badge);
      chips.appendChild(chip);
    }
    bar.appendChild(chips);
  }

  const textarea = document.createElement("textarea");
  textarea.placeholder = node.params.spec?.panorama
    ? "描述你想要的全景画面，例如“生成一张科技展厅的 720° 全景图”，支持上传场景参考图。"
    : promptPlaceholder(node.type, p.spec?.mode);
  textarea.value = node.prompt || "";
  textarea.addEventListener("input", () => {
    updateNode(store, node.id, (n) => { n.prompt = textarea.value; });
  });
  textarea.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      startLocalPreview(store, node);
    }
  });
  bar.appendChild(textarea);

  if (node.type === "image" || node.type === "video" || node.type === "script") {
    const expand = el("button", "expand-btn");
    expand.innerHTML = icon("expand", 14);
    expand.title = "放大编辑";
    expand.addEventListener("click", () => openExpandEditor(store, runtime, node));
    bar.appendChild(expand);
  }

  bar.appendChild(buildBottomRow(state, store, runtime, node, textarea));
  return bar;
}

function buildToolChips(store, runtime, node, defs, disabled = false) {
  const wrap = el("div", "tool-chips");
  for (const [label, iconName, onClick] of defs) {
    const chip = el("button", "tool-chip");
    chip.innerHTML = `<span class="tc-icon">${icon(iconName, 14)}</span><span>${label}</span>`;
    if (disabled) chip.disabled = true;
    if (label === "风格" && node.params.styleRef) chip.classList.add("active");
    if (label === "特效" && node.params.effect) chip.classList.add("active");
    chip.addEventListener("click", onClick);
    wrap.appendChild(chip);
  }
  return wrap;
}

function buildBottomRow(state, store, runtime, node, textarea) {
  const row = el("div", "bar-row");
  const p = node.params;
  const model = findModel(node.type, p.model);

  const modelBtn = el("button", "bar-select");
  modelBtn.innerHTML = `<span class="sel-icon">${icon("sparkle1", 13)}</span><span>${model.name}</span><span class="caret">▾</span>`;
  modelBtn.addEventListener("click", () => openModelPopover(store, node, modelBtn));
  row.appendChild(modelBtn);

  if (node.type === "image") {
    const specBtn = el("button", "bar-select");
    specBtn.innerHTML = `<span class="sel-icon">${icon("frames", 13)}</span><span>${imageSpecLabel(p.spec)}</span><span class="caret">▾</span>`;
    specBtn.addEventListener("click", () => openImageSpecPopover(store, node, specBtn));
    row.appendChild(specBtn);

    const camBtn = el("button", `bar-tool${p.camera ? " active" : ""}`);
    camBtn.innerHTML = `${icon("camera", 14)}<span>摄像机</span>`;
    camBtn.addEventListener("click", () => openCameraPopover(store, node, camBtn));
    row.appendChild(camBtn);

    const panoBtn = el("button", `bar-tool${p.spec.panorama ? " active" : ""}`);
    panoBtn.innerHTML = `${icon("globe", 14)}<span>全景</span>`;
    panoBtn.addEventListener("click", () => updateNode(store, node.id, (n) => {
      n.params.spec.panorama = !n.params.spec.panorama;
    }));
    row.appendChild(panoBtn);
  }

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

  // —— 唯一增量：优化提示词 ——
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

  const translateBtn = el("button", "bar-tool");
  translateBtn.innerHTML = icon("translate", 14);
  translateBtn.title = "翻译提示词";
  translateBtn.addEventListener("click", () => flashTooltip(translateBtn, "翻译将在后续版本开放"));
  row.appendChild(translateBtn);

  const counts = node.type === "image" ? IMAGE_COUNTS : (node.type === "video" ? VIDEO_COUNTS : null);
  if (counts) {
    const unit = node.type === "image" ? "张" : "个";
    const countBtn = el("button", "bar-select");
    countBtn.innerHTML = `<span>${p.spec.count}${unit}</span><span class="caret">▾</span>`;
    countBtn.addEventListener("click", () => {
      const pop = el("div");
      for (const c of counts) {
        const item = el("button", `menu-item${p.spec.count === c ? " selected" : ""}`, `${c}${unit}`);
        item.addEventListener("click", () => {
          updateNode(store, node.id, (n) => { n.params.spec.count = c; });
          close();
        });
        pop.appendChild(item);
      }
      const close = showPopover(countBtn, pop, { place: "top" });
    });
    row.appendChild(countBtn);
  }

  const model2 = findModel(node.type, p.model);
  const baseCost = model2.cost * (p.spec?.count || 1);
  const cost = el("span", "bar-cost");
  cost.innerHTML = `<span class="bolt">${icon("bolt", 12)}</span><span>${baseCost}</span>`;
  row.appendChild(cost);

  const send = el("button", "send-btn");
  send.innerHTML = icon("arrowUp", 15);
  send.title = "生成";
  send.addEventListener("click", () => startLocalPreview(store, node));
  row.appendChild(send);

  return row;
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

function openImageSpecPopover(store, node, anchor) {
  const pop = el("div", "spec-pop");
  pop.appendChild(specSection("画质", IMAGE_QUALITY, node.params.spec.quality, (v) =>
    updateNode(store, node.id, (n) => { n.params.spec.quality = v; })));
  pop.appendChild(specSection("清晰度", IMAGE_RESOLUTION, node.params.spec.resolution, (v) =>
    updateNode(store, node.id, (n) => { n.params.spec.resolution = v; })));
  pop.appendChild(specSection("比例", IMAGE_RATIOS, node.params.spec.ratio, (v) =>
    updateNode(store, node.id, (n) => { n.params.spec.ratio = v; }), true));
  showPopover(anchor, pop, { place: "top" });
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
