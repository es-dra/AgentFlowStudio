import { showModal, el } from "../overlay.js";
import { icon } from "../icons.js";
import {
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
import {
  createDirectorShellFrame,
  renderDirectorBoard,
  renderDirectorIntentPreview,
  renderDirectorObjectList,
} from "./director-shell-render.js";
import { addDirectorObject } from "./director-object-factory.js";

export function openDirectorShell(store, node) {
  let setup = normalizeDirectorSetup(node.params.directorSetup);
  let drag = null;
  let activeView = "layout";

  const {
    modal,
    layoutTab,
    intentTab,
    closeBtn,
    scene,
    board,
    props,
    saveBtn,
    applyBtn,
    promptBtn,
    resetBtn,
  } = createDirectorShellFrame();

  renderAll();

  const close = showModal(modal);
  closeBtn.addEventListener("click", close);
  layoutTab.addEventListener("click", () => switchView("layout"));
  intentTab.addEventListener("click", () => switchView("intent"));
  saveBtn.addEventListener("click", () => {
    saveSetup(store, node.id, setup, "导演台已保存");
    close();
  });
  applyBtn.addEventListener("click", () => {
    const count = applyToDownstream(store, node.id, setup);
    saveSetup(store, node.id, setup, `导演台已应用到 ${count} 个相连节点`);
    close();
  });
  promptBtn.addEventListener("click", async () => {
    const prompt = directorPromptSummary(setup);
    if (!(await confirmDirectorPromptAppend(prompt))) return;
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
    renderDirectorIntentPreview({ scene, board, props, setup, warnings: localDirectorWarnings(setup) });
  }

  function renderObjectList() {
    renderDirectorObjectList({
      scene,
      setup,
      onObjectSelect: (def, entry) => {
        const current = entry || addDirectorObject(setup, def);
        setup.selectedId = current.object.id;
        renderAll();
      },
    });
  }

  function renderBoard() {
    renderDirectorBoard({ board, setup, onObjectPointerDown: startDrag });
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

function confirmDirectorPromptAppend(prompt) {
  return new Promise((resolve) => {
    const modal = el("div", "modal compact director-confirm-modal");
    const head = el("div", "modal-head");
    head.appendChild(el("strong", "", "追加导演台提示词"));
    const closeBtn = el("button", "modal-close");
    closeBtn.innerHTML = icon("x", 15);
    head.appendChild(el("span", "head-spacer"));
    head.appendChild(closeBtn);
    const body = el("div", "modal-body director-confirm-body");
    body.appendChild(el("p", "", "将以下片段追加到当前节点，不会覆盖原提示词。"));
    const preview = el("div", "director-confirm-preview", prompt);
    body.appendChild(preview);
    const actions = el("div", "modal-actions");
    const cancel = el("button", "ghost-btn", "取消");
    const confirm = el("button", "primary-btn", "追加");
    actions.append(cancel, confirm);
    modal.append(head, body, actions);
    let settled = false;
    const close = showModal(modal, { onClose: () => { if (!settled) resolve(false); } });
    const finish = (value) => {
      if (settled) return;
      settled = true;
      close();
      resolve(value);
    };
    closeBtn.addEventListener("click", () => finish(false));
    cancel.addEventListener("click", () => finish(false));
    confirm.addEventListener("click", () => finish(true));
  });
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
    title: node.title || "导演台布置",
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
