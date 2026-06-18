// 轻量浮层管理器：popover（锚定小弹层）与 modal（全屏窗口）。
// Escape / 点击外部关闭；栈式管理，closeTop 只关最上层。

const stack = [];

function overlayRoot() {
  return document.getElementById("overlay-root");
}

export function showPopover(anchorEl, contentEl, options = {}) {
  const root = overlayRoot();
  contentEl.classList.add("popover");
  root.appendChild(contentEl);
  positionPopover(anchorEl, contentEl, options);
  const entry = pushEntry(contentEl, options);
  entry.close.reposition = () => positionPopover(anchorEl, contentEl, options);
  return entry.close;
}

export function showModal(contentEl, options = {}) {
  const root = overlayRoot();
  const backdrop = document.createElement("div");
  backdrop.className = "modal-backdrop";
  backdrop.appendChild(contentEl);
  root.appendChild(backdrop);
  const entry = pushEntry(backdrop, { ...options, isModal: true, content: contentEl });
  return entry.close;
}

export function closeTop() {
  const entry = stack[stack.length - 1];
  if (entry) entry.close();
  return Boolean(entry);
}

export function closeAll() {
  while (stack.length) stack[stack.length - 1].close();
}

export function hasOpenOverlay() {
  return stack.length > 0;
}

function pushEntry(el, options) {
  const entry = {
    el,
    close() {
      const idx = stack.indexOf(entry);
      if (idx >= 0) stack.splice(idx, 1);
      el.remove();
      document.removeEventListener("pointerdown", onOutside, true);
      options.onClose?.();
    },
  };
  function onOutside(event) {
    if (stack[stack.length - 1] !== entry) return;
    if (options.closeOnOutside === false) return;
    const target = options.isModal ? options.content : el;
    if (!target.contains(event.target)) {
      if (options.isModal && event.target !== el) return;
      entry.close();
    }
  }
  setTimeout(() => document.addEventListener("pointerdown", onOutside, true), 0);
  stack.push(entry);
  return entry;
}

function positionPopover(anchorEl, el, options) {
  const margin = 8;
  const rect = anchorEl.getBoundingClientRect();
  const place = options.place || "bottom";
  el.style.visibility = "hidden";
  const { width, height } = el.getBoundingClientRect();
  let left;
  let top;
  if (place === "bottom") {
    left = options.alignRight ? rect.right - width : rect.left;
    top = rect.bottom + margin;
  } else if (place === "top") {
    left = options.alignRight ? rect.right - width : rect.left;
    top = rect.top - height - margin;
  } else {
    left = rect.right + margin;
    top = rect.top;
  }
  left = Math.max(8, Math.min(left, window.innerWidth - width - 8));
  if (top + height > window.innerHeight - 8) top = Math.max(8, rect.top - height - margin);
  if (options.avoidSelector) {
    top = avoidOverlap(top, height, rect, options.avoidSelector, margin);
  }
  el.style.left = `${Math.round(left)}px`;
  el.style.top = `${Math.round(top)}px`;
  el.style.visibility = "";
}

function avoidOverlap(top, height, anchorRect, selector, margin) {
  const avoid = document.querySelector(selector);
  if (!avoid) return top;
  const avoidRect = avoid.getBoundingClientRect();
  const bottom = top + height;
  const overlaps = bottom > avoidRect.top - margin && top < avoidRect.bottom + margin;
  if (!overlaps) return top;
  const above = avoidRect.top - height - margin;
  const below = avoidRect.bottom + margin;
  if (above >= 8) return above;
  if (below + height <= window.innerHeight - 8) return below;
  return Math.max(8, Math.min(anchorRect.top - height - margin, window.innerHeight - height - 8));
}

export function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
