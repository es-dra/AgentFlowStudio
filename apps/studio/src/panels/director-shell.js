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

  const modal = el("div", "modal director-modal director-2d-modal");
  const top = el("div", "d-top");
  top.appendChild(el("span", "d-title", "二维导演台"));
  const views = el("div", "d-views");
  views.appendChild(el("button", "modal-tab active", "顶视布置"));
  views.appendChild(el("button", "modal-tab", "镜头意图"));
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
    store.set((s) => {
      const current = s.nodes[node.id];
      if (!current) return;
      current.prompt = prompt;
      current.result = `导演台提示词片段已生成：${directorSummary(setup)}`;
      current.status = "complete";
      current.params.directorSetup = withSelection(setup);
    });
    close();
  });
  resetBtn.addEventListener("click", () => {
    setup = createDefaultDirectorSetup();
    renderAll();
  });

  function renderAll() {
    renderObjectList();
    renderBoard();
    renderProps();
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
      item.innerHTML = `<span class="tree-icon">${icon(iconForKind(def.kind), 12)}</span><span class="tree-label">${def.label}</span>`;
      item.disabled = !entry;
      item.addEventListener("click", () => {
        if (!entry) return;
        setup.selectedId = entry.object.id;
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
    node.result = `${message}：${directorSummary(setup)}`;
    node.status = "complete";
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
      count += 1;
    }
  });
  return count;
}

function withSelection(setup) {
  return { ...safeDirectorSetup(setup), selectedId: setup.selectedId };
}

function objectByKind(setup, kind) {
  return allDirectorObjects(setup).find((entry) => entry.object.kind === kind || entry.group === kind);
}

function iconForKind(kind) {
  if (kind === "camera") return "filmcam";
  if (kind === "subject") return "user";
  if (kind.includes("light")) return "sparkles";
  if (kind === "reflector" || kind === "diffusion" || kind === "flag") return "layers";
  if (kind === "poster") return "image";
  return "layers";
}
