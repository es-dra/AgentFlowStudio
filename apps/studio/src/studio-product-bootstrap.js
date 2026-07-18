import { createProductShell } from "./product-shell.js";

const CANVAS_SHELL_HTML = `<main id="canvas-root"><div id="canvas-viewport"><div id="world"><svg id="edge-layer" xmlns="http://www.w3.org/2000/svg"></svg><div id="node-layer"></div></div></div><section id="canvas-empty-hint" hidden aria-label="空画布开始"><form class="canvas-empty-onboarding"><div class="empty-kicker">AgentFlow Studio</div><h1 class="canvas-empty-title">从一个想法开始制作</h1><p class="canvas-empty-copy">画布现在是空的。先写下故事方向、导入剧本，或创建一个空白文本节点；确认前不会生成角色、场景或镜头。</p><textarea data-empty-action="idea-text" rows="4" maxlength="12000" placeholder="写下想法、故事梗概或一段剧本文字"></textarea><div class="canvas-empty-actions"><button type="submit" class="empty-primary-action">输入想法</button><button type="button" data-empty-action="import-script">导入剧本</button><button type="button" data-empty-action="blank-node">空白节点</button><button type="button" data-empty-action="ask-agent">询问智能体</button></div><dl class="canvas-empty-counts"><div><dt>节点</dt><dd>0</dd></div><div><dt>场景</dt><dd>0</dd></div><div><dt>镜头</dt><dd>0</dd></div></dl></form></section><div id="prompt-bar-layer"></div></main><div id="corner-controls" aria-label="画布视图控制"></div>`;

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
