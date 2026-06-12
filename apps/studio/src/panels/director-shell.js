import { showModal, el } from "../overlay.js";
import { icon } from "../icons.js";
import {
  DIRECTOR_OBJECTS,
  allDirectorObjects,
  createDefaultDirectorSetup,
  directorPromptSummary,
  directorSummary,
  normalizeDirectorSetup,
  safeDirectorSetup,
  selectedDirectorObject,
  updateDirectorObjectPosition,
} from "../director-data.js";
import {
  cameraFields,
  labelForObject,
  lightFields,
  numberField,
  propFields,
  readonly,
  subjectFields,
  textField,
} from "./director-fields.js";

export function openDirectorShell(store, node) {
  let setup = normalizeDirectorSetup(node.params.directorSetup);
  let drag = null;
  let activeView = "layout";

  const modal = el("div", "modal director-modal director-2d-modal");
  const top = el("div", "d-top");
  top.appendChild(el("span", "d-title", "二维导演台"));
  const views = el("div", "d-views");
  const layoutTab = el("button", "modal-tab active", "顶视布置");
  const intentTab = el("button", "modal-tab", "镜头意图");
  views.append(layoutTab, intentTab);
  top.appendChild(views);
  const closeBtn = el("button", "modal-close");
  closeBtn.innerHTML = icon("x", 15);
  top.appendChild(closeBtn);
  modal.appendChild(top);

  const main = el("div", "d-main");
  const scene = el("div", "d-scene director-objects");
  const board = el("div", "d-viewport director-board");
  const props = el("div", "d-props director-props");
  main.append(scene, board, props);
  modal.appendChild(main);

  const bottom = el("div", "d-bottom director-actions");
  const saveBtn = el("button", "cam-use-btn", "保存布置");
  const applyBtn = el("button", "cam-use-btn", "应用到相连节点");
  const promptBtn = el("button", "cam-use-btn", "生成提示词片段");
  const resetBtn = el("button", "cam-use-btn muted", "重置布局");
  bottom.append(saveBtn, applyBtn, promptBtn, resetBtn);
  modal.appendChild(bottom);

  renderAll();

  const close = showModal(modal);
  closeBtn.addEventListener("click", close);
  layoutTab.addEventListener("click", () => switchView("layout"));
  intentTab.addEventListener("click", () => switchView("intent"));
  saveBtn.addEventListener("click", () => {
    saveSetup(store, node.id, setup, "二维导演台已保存");
    close();
  });
  applyBtn.addEventListener("click", () => {
    const count = applyToDownstream(store, node.id, setup);
    saveSetup(store, node.id, setup, `二维导演台已应用到 ${count} 个相连节点`);
    close();
  });
  promptBtn.addEventListener("click", () => {
    const prompt = directorPromptSummary(setup);
    if (!window.confirm("将导演台提示词片段追加到当前节点，不会覆盖原提示词。")) return;
    store.set((s) => {
      const current = s.nodes[node.id];
      if (!current) return;
      current.prompt = [current.prompt, prompt].map((item) => String(item || "").trim()).filter(Boolean).join("\n\n");
      current.result = `导演台提示词片段已追加：${directorSummary(setup)}`;
      current.status = "complete";
      current.params.directorSetup = withSelection(setup);
      current.params.directorSummary = directorSummary(setup);
      current.params.visual_asset_ids = directorVisualAssetIds(setup);
      upsertDirectorAsset(s, node.id, current, setup);
    });
    close();
  });
  resetBtn.addEventListener("click", () => {
    setup = createDefaultDirectorSetup();
    renderAll();
  });

  function renderAll() {
    layoutTab.classList.toggle("active", activeView === "layout");
    intentTab.classList.toggle("active", activeView === "intent");
    if (activeView === "intent") {
      renderIntentPreview();
      return;
    }
    renderObjectList();
    renderBoard();
    renderProps();
  }

  function switchView(view) {
    activeView = view;
    renderAll();
  }

  function renderIntentPreview() {
    scene.replaceChildren();
    scene.appendChild(el("div", "d-scene-label", "编译预览"));
    scene.appendChild(el("div", "p-readonly", directorSummary(setup)));
    board.replaceChildren();
    const preview = el("div", "director-intent-preview");
    preview.textContent = directorPromptSummary(setup);
    board.appendChild(preview);
    props.replaceChildren();
    props.appendChild(el("div", "d-scene-label", "检查"));
    for (const warning of localDirectorWarnings(setup)) {
      props.appendChild(el("div", "bundle-warning", warning));
    }
  }

  function renderObjectList() {
    scene.replaceChildren();
    scene.appendChild(el("div", "d-scene-label", "对象"));
    const search = el("div", "drawer-search");
    search.innerHTML = icon("search", 13);
    const input = document.createElement("input");
    input.placeholder = "搜索对象";
    search.appendChild(input);
    scene.appendChild(search);

    for (const def of DIRECTOR_OBJECTS) {
      const entry = objectByKind(setup, def.kind);
      const item = el("button", `tree-item${entry?.object.id === setup.selectedId ? " selected" : ""}`);
      item.innerHTML = `<span class="tree-icon">${icon(iconForKind(def.kind), 12)}</span><span class="tree-label">${entry ? def.label : `+ ${def.label}`}</span>`;
      item.addEventListener("click", () => {
        const current = entry || addDirectorObject(setup, def);
        setup.selectedId = current.object.id;
        renderAll();
      });
      scene.appendChild(item);
    }
  }

  function renderBoard() {
    board.replaceChildren();
    const guide = el("div", "director-board-hint", "拖动相机、人物、灯光和道具来布置镜头");
    board.appendChild(guide);
    for (const entry of allDirectorObjects(setup)) {
      board.appendChild(renderBoardObject(entry));
    }
  }

  function renderBoardObject(entry) {
    const obj = entry.object;
    const item = el("button", `director-object ${entry.group} kind-${obj.kind || entry.group}${obj.id === setup.selectedId ? " selected" : ""}`);
    item.dataset.objectId = obj.id;
    item.style.left = `${obj.x}%`;
    item.style.top = `${obj.y}%`;
    item.style.setProperty("--angle", `${obj.angle || 0}deg`);
    if (entry.group === "prop") {
      item.style.width = `${obj.width || 12}%`;
      item.style.height = `${obj.height || 8}%`;
    }
    if (entry.group === "camera") item.innerHTML = `<span class="camera-cone"></span>${icon("filmcam", 15)}<span>${obj.name}</span>`;
    else if (entry.group === "light") item.innerHTML = `<span class="light-cone"></span>${icon("sparkles", 14)}<span>${obj.name}</span>`;
    else if (entry.group === "subject") item.innerHTML = `${icon("user", 15)}<span>${obj.name}</span><span class="facing-arrow">↑</span>`;
    else if (entry.group === "modifier") item.innerHTML = `${icon(iconForKind(obj.kind), 14)}<span>${obj.name}</span>`;
    else item.innerHTML = `<span>${obj.name}</span>`;
    item.addEventListener("pointerdown", (event) => startDrag(event, item, obj));
    return item;
  }

  function startDrag(event, item, obj) {
    setup.selectedId = obj.id;
    renderObjectList();
    renderProps();
    drag = { id: obj.id, item };
    board.setPointerCapture(event.pointerId);
    event.preventDefault();
    event.stopPropagation();
  }

  board.addEventListener("pointermove", (event) => {
    if (!drag) return;
    const rect = board.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * 100;
    const y = ((event.clientY - rect.top) / rect.height) * 100;
    updateDirectorObjectPosition(setup, drag.id, x, y);
    const entry = selectedDirectorObject(setup);
    drag.item.style.left = `${entry.object.x}%`;
    drag.item.style.top = `${entry.object.y}%`;
  });
  board.addEventListener("pointerup", () => {
    if (!drag) return;
    drag = null;
    renderAll();
  });

  function renderProps() {
    props.replaceChildren();
    const selected = selectedDirectorObject(setup);
    if (!selected) return;
    const obj = selected.object;
    props.appendChild(el("div", "d-scene-label", "参数"));
    props.appendChild(readonly("类型", labelForObject(selected)));
    if (selected.group === "camera") {
      const active = obj.id === setup.activeCameraId;
      const btn = el("button", "cam-use-btn", active ? "当前生效机位" : "设为生效机位");
      btn.disabled = active;
      btn.addEventListener("click", () => { setup.activeCameraId = obj.id; renderAll(); });
      props.appendChild(btn);
    }
    if (selected.group === "subject") {
      const activeSubjects = new Set(setup.activeSubjectIds || []);
      const active = activeSubjects.has(obj.id);
      const btn = el("button", "cam-use-btn", active ? "移出本镜头主体" : "加入本镜头主体");
      btn.addEventListener("click", () => {
        if (active) activeSubjects.delete(obj.id);
        else activeSubjects.add(obj.id);
        setup.activeSubjectIds = [...activeSubjects];
        renderAll();
      });
      props.appendChild(btn);
    }
    props.appendChild(textField("名称", obj.name, (value) => { obj.name = value; renderObjectList(); renderBoard(); }));
    props.appendChild(numberField("X", obj.x, (value) => { obj.x = value; renderBoard(); }));
    props.appendChild(numberField("Y", obj.y, (value) => { obj.y = value; renderBoard(); }));
    if ("angle" in obj) props.appendChild(numberField("朝向/角度", obj.angle, (value) => { obj.angle = value; renderBoard(); }));
    if (selected.group === "camera") cameraFields(obj).forEach((node) => props.appendChild(node));
    if (selected.group === "subject") subjectFields(obj).forEach((node) => props.appendChild(node));
    if (selected.group === "light") lightFields(obj).forEach((node) => props.appendChild(node));
    if (selected.group === "modifier") props.appendChild(textField("作用", obj.influence, (value) => { obj.influence = value; }));
    if (selected.group === "prop") propFields(obj, renderBoard).forEach((node) => props.appendChild(node));
    props.appendChild(textField("导演备注", setup.notes || "", (value) => { setup.notes = value; }, true));
  }

}

function saveSetup(store, nodeId, setup, message) {
  store.set((s) => {
    const node = s.nodes[nodeId];
    if (!node) return;
    node.params.directorSetup = withSelection(setup);
    node.params.directorSummary = directorSummary(setup);
    node.params.visual_asset_ids = directorVisualAssetIds(setup);
    node.result = `${message}：${directorSummary(setup)}`;
    node.status = "complete";
    upsertDirectorAsset(s, nodeId, node, setup);
  });
}

function applyToDownstream(store, nodeId, setup) {
  let count = 0;
  store.set((s) => {
    const payload = withSelection(setup);
    for (const edge of Object.values(s.edges)) {
      if (edge.from !== nodeId) continue;
      const target = s.nodes[edge.to];
      if (!target) continue;
      target.params.directorSetup = payload;
      target.params.directorRef = nodeId;
      target.params.visual_asset_ids = directorVisualAssetIds(setup);
      edge.relation_type = "director";
      count += 1;
    }
    const source = s.nodes[nodeId];
    if (source) source.params.appliedDownstreamCount = count;
  });
  return count;
}

function upsertDirectorAsset(state, nodeId, node, setup) {
  const assetId = `asset_director_${nodeId}`;
  const payload = {
    id: assetId,
    kind: "director_setup",
    title: node.title || "二维导演台布置",
    safe_summary: directorSummary(setup),
    thumbnail_ref: "director-board",
    source_node_id: nodeId,
    status: "ready",
    created_at: new Date().toISOString(),
  };
  const index = state.assets.findIndex((asset) => asset.id === assetId);
  if (index >= 0) state.assets[index] = payload;
  else state.assets.unshift(payload);
}

function withSelection(setup) {
  return { ...safeDirectorSetup(setup), selectedId: setup.selectedId };
}

function directorVisualAssetIds(setup) {
  return (setup.subjects || [])
    .map((item) => String(item.visual_asset_id || "").trim())
    .filter(Boolean)
    .filter((value, index, arr) => arr.indexOf(value) === index);
}

function localDirectorWarnings(setup) {
  const warnings = [];
  if (!setup.activeCameraId && setup.cameras.length) warnings.push("未指定生效机位，后端会默认取第一个机位。");
  if (!setup.activeSubjectIds?.length && setup.subjects.length) warnings.push("未指定生效主体，后端会编译全部主体。");
  if (!setup.cameras.length) warnings.push("当前没有机位。");
  if (!setup.subjects.length) warnings.push("当前没有主体。");
  return warnings.length ? warnings : ["后端会在优化/生成时使用 Director Compiler v1 编译摄影语言。"];
}

function objectByKind(setup, kind) {
  return allDirectorObjects(setup).find((entry) => entry.object.kind === kind || entry.group === kind);
}

function addDirectorObject(setup, def) {
  const kind = def.kind;
  const id = `${kind}_${Date.now().toString(36)}`;
  let object;
  let group;
  if (kind === "camera") {
    group = "camera";
    object = { id, kind: "camera", name: "机位", x: 22, y: 78, angle: -35, fov: 50, focalLength: 35, height: "平视", shot: "中景", composition: "", lookAt: "" };
    setup.cameras.push(object);
    setup.activeCameraId = setup.activeCameraId || id;
  } else if (kind === "subject") {
    group = "subject";
    object = { id, kind: "subject", name: "主体", x: 53, y: 55, angle: 210, action: "", emotion: "", visual_asset_id: "" };
    setup.subjects.push(object);
    setup.activeSubjectIds = [...new Set([...(setup.activeSubjectIds || []), id])];
  } else if (kind.includes("light")) {
    group = "light";
    object = { id, kind, name: def.label, x: 36, y: 30, angle: 45, intensity: 60, colorTemp: 4300, softness: 60, distance: 3, motivated: false };
    setup.lights.push(object);
  } else if (["reflector", "diffusion", "flag", "window_light"].includes(kind)) {
    group = "modifier";
    object = { id, kind, name: def.label, x: 45, y: 45, angle: 90, width: 16, influence: "" };
    setup.modifiers.push(object);
  } else {
    group = "prop";
    object = { id, kind, name: def.label, x: 58, y: 58, width: 14, height: 10, visible: true, narrative: "" };
    setup.props.push(object);
  }
  return { group, object };
}

function iconForKind(kind) {
  if (kind === "camera") return "filmcam";
  if (kind === "subject") return "user";
  if (kind.includes("light")) return "sparkles";
  if (kind === "reflector" || kind === "diffusion" || kind === "flag") return "layers";
  if (kind === "poster") return "image";
  return "layers";
}
