import { showModal, el } from "../overlay.js";
import { icon } from "../icons.js";

const SECTIONS = [
  {
    title: "创作",
    rows: [
      ["成组", ["Ctrl/Alt", "G"]],
      ["解组", ["Ctrl/Alt", "Shift", "G"]],
      ["生成", ["Ctrl", "Enter"]],
      ["新建节点", ["Tab"]],
      ["节点复制", ["Alt", "+拖动节点"]],
      ["复制节点", ["Ctrl", "D"]],
    ],
  },
  {
    title: "缩放",
    rows: [
      ["放大", ["Ctrl", "+"]],
      ["缩小", ["Ctrl", "−"]],
      ["适应画布", ["Ctrl", "0"]],
      ["拓扑排列", ["Ctrl", "L"]],
      ["鼠标", ["Ctrl", "滚轮"]],
    ],
  },
  {
    title: "移动画布",
    rows: [
      ["键盘", ["Space", "拖动"]],
      ["触控板", ["双指"]],
    ],
  },
  {
    title: "其他",
    rows: [
      ["撤销", ["Ctrl", "Z"]],
      ["重做", ["Ctrl", "Shift", "Z"]],
      ["删除", ["Delete"]],
      ["打开本面板", ["?"]],
    ],
  },
];

export function openShortcutsPanel() {
  const modal = el("div", "modal compact shortcuts-modal");
  const head = el("div", "modal-head");
  head.appendChild(el("span", "", "快捷键"));
  head.appendChild(el("span", "head-spacer"));
  const closeBtn = el("button", "modal-close");
  closeBtn.innerHTML = icon("x", 15);
  head.appendChild(closeBtn);
  modal.appendChild(head);

  const cols = el("div", "sc-cols");
  for (const section of SECTIONS) {
    const col = el("div", "sc-col");
    const h = document.createElement("h4");
    h.textContent = section.title;
    col.appendChild(h);
    for (const [label, keys] of section.rows) {
      const row = el("div", "sc-row");
      row.appendChild(el("span", "", label));
      const keysWrap = el("span", "sc-keys");
      keys.forEach((k, i) => {
        keysWrap.appendChild(el("span", "key", k));
        if (i < keys.length - 1) keysWrap.appendChild(el("span", "", "+"));
      });
      row.appendChild(keysWrap);
      col.appendChild(row);
    }
    cols.appendChild(col);
  }
  modal.appendChild(cols);

  const close = showModal(modal);
  closeBtn.addEventListener("click", close);
}
