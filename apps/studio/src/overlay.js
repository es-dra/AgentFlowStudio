// 轻量浮层管理器：popover（锚定小弹层）与 modal（全屏窗口）。
// Escape / 点击外部关闭；栈式管理，closeTop 只关最上层。

const stack = [];
let modalId = 0;
let keydownBound = false;

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
  const previousFocus = activeElement();
  const backdrop = document.createElement("div");
  backdrop.className = "modal-backdrop";
  prepareModalContent(contentEl, options);
  backdrop.appendChild(contentEl);
  root.appendChild(backdrop);
  const entry = pushEntry(backdrop, { ...options, isModal: true, content: contentEl, previousFocus });
  scheduleModalFocus(entry);
  return entry.close;
}

export function closeTop(reason = "programmatic") {
  const entry = stack[stack.length - 1];
  if (!entry) return false;
  return entry.close(reason);
}

export function closeAll() {
  while (stack.length) stack[stack.length - 1].close("programmatic");
}

export function hasOpenOverlay() {
  return stack.length > 0;
}

function pushEntry(el, options) {
  const entry = {
    el,
    options,
    close(reason = "programmatic") {
      if (reason === "escape" && options.closeOnEscape === false) return false;
      if (reason === "outside" && options.closeOnOutside === false) return false;
      const idx = stack.indexOf(entry);
      if (idx < 0) return false;
      stack.splice(idx, 1);
      el.remove();
      document.removeEventListener("pointerdown", onOutside, true);
      options.onClose?.();
      syncGlobalKeydown();
      afterEntryClosed(entry);
      return true;
    },
  };
  function onOutside(event) {
    if (stack[stack.length - 1] !== entry) return;
    const target = options.isModal ? options.content : el;
    if (!target.contains(event.target)) {
      if (options.isModal && event.target !== el) return;
      entry.close("outside");
    }
  }
  setTimeout(() => document.addEventListener("pointerdown", onOutside, true), 0);
  stack.push(entry);
  syncGlobalKeydown();
  return entry;
}

function prepareModalContent(contentEl, options) {
  if (!contentEl.hasAttribute("role")) contentEl.setAttribute("role", "dialog");
  contentEl.setAttribute("aria-modal", "true");
  if (!contentEl.hasAttribute("tabindex")) contentEl.tabIndex = -1;
  labelModal(contentEl, options);
}

function labelModal(contentEl, options) {
  if (options.ariaLabel) {
    contentEl.setAttribute("aria-label", options.ariaLabel);
    return;
  }
  if (options.labelledBy) {
    contentEl.setAttribute("aria-labelledby", options.labelledBy);
    return;
  }
  if (contentEl.hasAttribute("aria-label") || contentEl.hasAttribute("aria-labelledby")) return;
  const title = contentEl.querySelector("[data-modal-title], .modal-head strong, h1, h2, h3");
  if (!title) {
    contentEl.setAttribute("aria-label", "Dialog");
    return;
  }
  if (!title.id) title.id = `afs-modal-title-${++modalId}`;
  contentEl.setAttribute("aria-labelledby", title.id);
}

function syncGlobalKeydown() {
  if (stack.length && !keydownBound) {
    document.addEventListener("keydown", onOverlayKeydown, true);
    keydownBound = true;
  } else if (!stack.length && keydownBound) {
    document.removeEventListener("keydown", onOverlayKeydown, true);
    keydownBound = false;
  }
}

function onOverlayKeydown(event) {
  const entry = stack[stack.length - 1];
  if (!entry) return;
  if (event.key === "Escape") {
    event.preventDefault();
    event.stopPropagation();
    entry.close("escape");
    return;
  }
  if (event.key === "Tab" && entry.options.isModal) {
    trapModalFocus(event, entry);
    event.stopPropagation();
  }
}

function trapModalFocus(event, entry) {
  const content = entry.options.content;
  const focusables = focusableElements(content);
  if (!focusables.length) {
    event.preventDefault();
    focusElement(content);
    return;
  }
  const first = focusables[0];
  const last = focusables[focusables.length - 1];
  const current = activeElement();
  if (!content.contains(current)) {
    event.preventDefault();
    focusElement(event.shiftKey ? last : first);
    return;
  }
  if (event.shiftKey && current === first) {
    event.preventDefault();
    focusElement(last);
  } else if (!event.shiftKey && current === last) {
    event.preventDefault();
    focusElement(first);
  }
}

function focusableElements(container) {
  return Array.from(container.querySelectorAll([
    "a[href]",
    "button:not([disabled])",
    "input:not([disabled])",
    "select:not([disabled])",
    "textarea:not([disabled])",
    "[tabindex]:not([tabindex='-1'])",
    "[contenteditable='true']",
  ].join(","))).filter(isFocusable);
}

function isFocusable(node) {
  if (!(node instanceof HTMLElement)) return false;
  if (node.hidden || node.getAttribute("aria-hidden") === "true") return false;
  const style = window.getComputedStyle ? window.getComputedStyle(node) : null;
  return !style || (style.display !== "none" && style.visibility !== "hidden");
}

function scheduleModalFocus(entry) {
  requestAnimationFrame(() => {
    if (stack[stack.length - 1] === entry) focusModal(entry);
  });
}

function focusModal(entry) {
  const content = entry.options.content;
  const target = initialFocusTarget(entry.options.initialFocus, content)
    || focusableElements(content)[0]
    || content;
  focusElement(target);
}

function initialFocusTarget(initialFocus, content) {
  if (!initialFocus) return null;
  if (typeof initialFocus === "string") return content.querySelector(initialFocus);
  if (typeof initialFocus === "function") return initialFocus(content);
  return initialFocus;
}

function afterEntryClosed(entry) {
  const next = stack[stack.length - 1];
  if (next?.options?.isModal) {
    scheduleModalFocus(next);
    return;
  }
  const previous = entry.options.previousFocus;
  if (previous?.isConnected) requestAnimationFrame(() => focusElement(previous));
}

function activeElement() {
  return document.activeElement instanceof HTMLElement ? document.activeElement : null;
}

function focusElement(node) {
  if (!(node instanceof HTMLElement)) return;
  try {
    node.focus({ preventScroll: true });
  } catch {
    node.focus();
  }
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
  top = Math.max(8, Math.min(top, Math.max(8, window.innerHeight - height - 8)));
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
