import { createProductShell } from "./product-shell.js";

const CANVAS_SHELL_HTML = `<main id="canvas-root"><div id="canvas-viewport"><div id="world"><svg id="edge-layer" xmlns="http://www.w3.org/2000/svg"></svg><div id="node-layer"></div></div></div><div id="canvas-empty-hint" hidden><div class="empty-kicker">Canvas</div><div class="canvas-empty-title">双击画布创建文本节点</div><div class="canvas-empty-copy">从一个想法、剧本片段或参考说明开始，内容会保存到当前项目。</div><div class="canvas-empty-shortcuts"><span class="hint-chip primary">双击创建</span><span class="hint-dim">也可按 Tab 或使用底部 +</span></div></div><div id="prompt-bar-layer"></div></main><footer id="dock"></footer>`;

export function mountStudioDom() {
  const app = document.getElementById("app");
  app.className = "product-mode";
  app.replaceChildren();
  const productRoot = document.createElement("div");
  productRoot.id = "product-shell-root";
  app.appendChild(productRoot);
  const editorMounted = !window.matchMedia("(max-width: 760px)").matches;
  let editorParking = null;
  let editorShell = null;
  if (editorMounted) {
    editorParking = document.createElement("div");
    editorParking.id = "studio-canvas-parking";
    editorParking.hidden = true;
    editorShell = document.createElement("div");
    editorShell.id = "studio-editor-shell";
    editorShell.innerHTML = CANVAS_SHELL_HTML;
    editorParking.appendChild(editorShell);
    app.appendChild(editorParking);
  }
  const overlay = document.createElement("div");
  overlay.id = "overlay-root";
  app.appendChild(overlay);
  return { editorMounted, editorParking, editorShell };
}

export function createStudioProductShell(options) {
  const getStore = options.getStore;
  return createProductShell({
    ...options,
    getStudioState: () => getStore()?.get?.() || null,
    parkCanvas: () => {
      const editorShell = options.getCanvasShell?.();
      const editorParking = options.getCanvasParking?.();
      if (editorShell && editorParking && editorShell.parentElement !== editorParking) editorParking.appendChild(editorShell);
    },
    onSelectCanvasNode: (nodeId) => {
      const store = getStore();
      const node = nodeId ? store?.get?.().nodes?.[nodeId] : null;
      if (node) {
        window.dispatchEvent(new CustomEvent("afs:studio-select-node", { detail: { node_id: nodeId } }));
        return true;
      }
      store?.set?.((state) => {
        state.selection = { nodeIds: [], edgeId: null };
      }, { history: false, persist: false });
      return false;
    },
    onApplyDirectorDraft: (nodeId, draft) => {
      const store = getStore();
      if (!nodeId || !store?.get?.().nodes?.[nodeId]) return false;
      store.set((state) => {
        const target = state.nodes[nodeId];
        target.params = target.params || {};
        target.params.directorDraft = {
          text: String(draft || ""),
          scope: "current_shot",
          updated_at: new Date().toISOString(),
        };
      });
      return true;
    },
    onRetrySave: () => getStore()?.flushRuntimeSave?.(),
  });
}
