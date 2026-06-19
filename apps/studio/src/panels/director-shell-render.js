import { el } from "../overlay.js";
import { icon } from "../icons.js";
import { DIRECTOR_OBJECTS, allDirectorObjects, directorPromptSummary, directorSummary } from "../director-data.js";

export function createDirectorShellFrame() {
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

  return { modal, layoutTab, intentTab, closeBtn, scene, board, props, saveBtn, applyBtn, promptBtn, resetBtn };
}

export function renderDirectorIntentPreview({ scene, board, props, setup, warnings }) {
  scene.replaceChildren();
  scene.appendChild(el("div", "d-scene-label", "编译预览"));
  scene.appendChild(el("div", "p-readonly", directorSummary(setup)));

  board.replaceChildren();
  const preview = el("div", "director-intent-preview");
  preview.textContent = directorPromptSummary(setup);
  board.appendChild(preview);

  props.replaceChildren();
  props.appendChild(el("div", "d-scene-label", "检查"));
  for (const warning of warnings) {
    props.appendChild(el("div", "bundle-warning", warning));
  }
}

export function renderDirectorObjectList({ scene, setup, onObjectSelect }) {
  scene.replaceChildren();
  scene.appendChild(el("div", "d-scene-label", "对象"));

  const search = el("div", "drawer-search");
  search.innerHTML = icon("search", 13);
  const input = document.createElement("input");
  input.placeholder = "搜索对象";
  search.appendChild(input);
  scene.appendChild(search);

  for (const def of DIRECTOR_OBJECTS) {
    const entry = objectEntryForKind(setup, def.kind);
    const item = el("button", `tree-item${entry?.object.id === setup.selectedId ? " selected" : ""}`);
    item.innerHTML = `<span class="tree-icon">${icon(iconForKind(def.kind), 12)}</span><span class="tree-label">${entry ? def.label : `+ ${def.label}`}</span>`;
    item.addEventListener("click", () => onObjectSelect(def, entry));
    scene.appendChild(item);
  }
}

export function renderDirectorBoard({ board, setup, onObjectPointerDown }) {
  board.replaceChildren();
  const guide = el("div", "director-board-hint", "拖动相机、人物、灯光和道具来布置镜头");
  board.appendChild(guide);
  for (const entry of allDirectorObjects(setup)) {
    board.appendChild(renderBoardObject(entry, setup, onObjectPointerDown));
  }
}

function renderBoardObject(entry, setup, onObjectPointerDown) {
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
  item.addEventListener("pointerdown", (event) => onObjectPointerDown(event, item, obj));
  return item;
}

function objectEntryForKind(setup, kind) {
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
