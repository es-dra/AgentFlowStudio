import { clientToWorld } from "./geometry.js";
import { createNode } from "./nodes.js";
import { setNodeError } from "./node-action-utils.js";
import { uploadSelectedImage } from "./node-upload-actions.js";

const DIRECT_REFERENCE_TYPES = new Set(["image", "video", "ref", "character", "location", "prop", "shot"]);

export function bindCanvasReferenceEntry({ store, runtime }) {
  const root = document.getElementById("canvas-root");
  if (!root) return;
  root.addEventListener("dragover", (event) => {
    if (!hasImageTransfer(event.dataTransfer) || event.target.closest(".modal-backdrop,.popover,#drawer,#dock,#topbar")) return;
    event.preventDefault();
    root.classList.add("canvas-reference-dragover");
  });
  root.addEventListener("dragleave", (event) => {
    if (!root.contains(event.relatedTarget)) root.classList.remove("canvas-reference-dragover");
  });
  root.addEventListener("drop", (event) => {
    if (!hasImageTransfer(event.dataTransfer)) return;
    event.preventDefault();
    root.classList.remove("canvas-reference-dragover");
    const file = firstImageFile(event.dataTransfer);
    if (file) void attachReferenceImage({ store, runtime, file, clientX: event.clientX, clientY: event.clientY });
  });
  window.addEventListener("paste", (event) => {
    if (isEditableTarget(event.target)) return;
    if (!root.contains(document.activeElement) && document.activeElement !== document.body) return;
    const file = firstImageFile(event.clipboardData);
    if (!file) return;
    event.preventDefault();
    void attachReferenceImage({ store, runtime, file });
  });
}

async function attachReferenceImage({ store, runtime, file, clientX = null, clientY = null }) {
  const targetId = selectedUploadTarget(store) || createReferenceNode(store, clientX, clientY);
  if (!targetId) return;
  await uploadSelectedImage(store, runtime, targetId, file);
}

function selectedUploadTarget(store) {
  const state = store.get();
  const selected = state.selection?.nodeIds?.length === 1 ? state.selection.nodeIds[0] : "";
  const node = selected ? state.nodes?.[selected] : null;
  return node && DIRECT_REFERENCE_TYPES.has(node.type) ? node.id : "";
}

function createReferenceNode(store, clientX, clientY) {
  const state = store.get();
  const root = document.getElementById("canvas-root");
  const rect = root?.getBoundingClientRect?.();
  const sx = Number.isFinite(Number(clientX)) ? clientX : (rect ? rect.left + rect.width / 2 : 420);
  const sy = Number.isFinite(Number(clientY)) ? clientY : (rect ? rect.top + rect.height / 2 : 320);
  const point = clientToWorld(state.viewport, sx, sy, root);
  const node = createNode(store, "ref", point.x - 140, point.y - 120);
  store.set((s) => {
    const current = s.nodes[node.id];
    if (!current) return;
    current.title = "参考图";
    current.params.referenceIntent = "canvas_direct_image";
    current.prompt = "直接拖放或粘贴到画布的参考图；可继续连接到角色、场景、镜头或生成节点。";
    current.status = "empty";
  });
  if (!runtime?.uploadImageAsset) {
    setNodeError(store, node.id, "当前运行服务没有开放安全图片上传接口；参考图节点已创建。");
  }
  return node.id;
}

function hasImageTransfer(dataTransfer) {
  return Boolean(firstImageFile(dataTransfer));
}

function firstImageFile(dataTransfer) {
  const files = Array.from(dataTransfer?.files || []);
  return files.find((file) => String(file.type || "").startsWith("image/")) || null;
}

function isEditableTarget(target) {
  return Boolean(target?.closest?.("textarea,input,select,[contenteditable='true']"));
}
