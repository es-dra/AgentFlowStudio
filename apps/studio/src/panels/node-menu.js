import { el, showPopover } from "../overlay.js";
import { icon } from "../icons.js";
import { duplicateNode, deleteNodes } from "../nodes.js";
import { startLocalPreview } from "../node-actions.js";

// 节点右键菜单 / 「更多」菜单：重命名、复制、折叠、重试、设为参考、删除。
export function openNodeMenu(store, nodeId, anchorOrPoint) {
  const node = store.get().nodes[nodeId];
  if (!node) return;
  const pop = el("div");
  pop.style.minWidth = "188px";

  addItem("pencil", "重命名", () => renameNode(store, nodeId, anchor));
  addItem("copy", "复制节点", () => duplicateNode(store, nodeId));
  addItem(node.collapsed ? "chevronDown" : "chevronUp", node.collapsed ? "展开" : "折叠", () =>
    store.set((s) => { const n = s.nodes[nodeId]; if (n) n.collapsed = !n.collapsed; }));
  addItem("retry", "重试生成", () => {
    const fresh = store.get().nodes[nodeId];
    if (fresh) startLocalPreview(store, fresh);
  });
  addItem("bookmark", node.params?.isReference ? "取消参考" : "设为参考", () =>
    store.set((s) => { const n = s.nodes[nodeId]; if (n) n.params.isReference = !n.params.isReference; }));
  addItem("trash", "删除节点", () => deleteNodes(store, [nodeId]), true);

  const anchor = resolveAnchor(anchorOrPoint);
  const close = showPopover(anchor.el, pop, { place: "bottom", onClose: anchor.cleanup });

  function addItem(iconName, label, onClick, danger = false) {
    const item = el("button", `menu-item${danger ? " danger" : ""}`);
    item.innerHTML = `<span class="mi-icon">${icon(iconName, 13)}</span><span>${label}</span>`;
    item.addEventListener("click", () => { close(); onClick(); });
    pop.appendChild(item);
  }
}

export function renameNode(store, nodeId, anchorOrPoint) {
  const node = store.get().nodes[nodeId];
  if (!node) return;
  const pop = el("div", "rename-pop");
  const input = document.createElement("input");
  input.className = "rename-input";
  input.value = node.title;
  input.maxLength = 40;
  pop.appendChild(input);
  const anchor = resolveAnchor(anchorOrPoint);
  const close = showPopover(anchor.el, pop, { place: "bottom", onClose: anchor.cleanup });
  input.focus();
  input.select();
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      const title = input.value.trim();
      if (title) store.set((s) => { const n = s.nodes[nodeId]; if (n) n.title = title; });
      close();
    }
    if (e.key === "Escape") close();
  });
}

function resolveAnchor(anchorOrPoint) {
  if (anchorOrPoint instanceof Element) return { el: anchorOrPoint, cleanup: undefined };
  const ghost = el("div");
  ghost.style.cssText = `position:fixed;left:${anchorOrPoint.x}px;top:${anchorOrPoint.y}px;width:1px;height:1px;pointer-events:none;`;
  document.body.appendChild(ghost);
  return { el: ghost, cleanup: () => ghost.remove() };
}
