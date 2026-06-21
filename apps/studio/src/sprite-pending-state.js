let spritePendingTimer = null;
let spritePendingIndex = 0;
let inputFocused = false;
let inputComposing = false;
let inputSelection = { start: 0, end: 0 };

export const SPRITE_PENDING_LINES = [
  "团团正在整理画布上下文...",
  "团团正在看当前选中的节点...",
  "团团正在把素材、进度和画布关系放到一起...",
  "团团正在组织一句短建议...",
];

export function resetSpritePendingLine() {
  spritePendingIndex = 0;
}

export function pendingSpriteText() {
  return SPRITE_PENDING_LINES[spritePendingIndex % SPRITE_PENDING_LINES.length];
}

export function startSpritePendingTicker({ messages, isSending, render }) {
  stopSpritePendingTicker();
  spritePendingTimer = window.setInterval(() => {
    const pending = [...messages].reverse().find((message) => message?.role === "pending");
    if (!pending || !isSending()) {
      stopSpritePendingTicker();
      return;
    }
    spritePendingIndex += 1;
    pending.text = pendingSpriteText();
    render();
  }, 2600);
}

export function stopSpritePendingTicker() {
  if (!spritePendingTimer) return;
  window.clearInterval(spritePendingTimer);
  spritePendingTimer = null;
}

export function captureSpriteInputFocus(root) {
  const input = root.querySelector?.(".afs-sprite-form input");
  const active = input && document.activeElement === input;
  return {
    active: Boolean(active || inputFocused),
    start: active ? input.selectionStart : inputSelection.start,
    end: active ? input.selectionEnd : inputSelection.end,
  };
}

export function restoreSpriteInputFocus(root, snapshot, { open, settingsOpen, sending }) {
  if (!snapshot?.active || !open || settingsOpen || sending || inputComposing) return;
  window.requestAnimationFrame(() => {
    const input = root.querySelector?.(".afs-sprite-form input");
    if (!input) return;
    input.focus({ preventScroll: true });
    const length = input.value.length;
    const start = Math.max(0, Math.min(Number(snapshot.start ?? length), length));
    const end = Math.max(start, Math.min(Number(snapshot.end ?? start), length));
    input.setSelectionRange?.(start, end);
  });
}

export function captureSpriteLogScroll(root) {
  const log = root.querySelector?.(".afs-sprite-log");
  if (!log) return null;
  return {
    top: Number(log.scrollTop || 0),
    nearBottom: log.scrollHeight - log.clientHeight - log.scrollTop < 8,
  };
}

export function restoreSpriteLogScroll(root, snapshot) {
  window.requestAnimationFrame(() => {
    const log = root.querySelector?.(".afs-sprite-log");
    if (!log) return;
    log.scrollTop = snapshot?.nearBottom ? log.scrollHeight : Number(snapshot?.top || 0);
  });
}

export function isSpriteInputComposing() {
  return inputComposing;
}

export function spriteInputComposing(value, input) {
  inputComposing = Boolean(value);
  if (input) rememberSpriteInputSelection(input);
}

export function spriteInputFocused(value, input) {
  inputFocused = Boolean(value);
  if (input) rememberSpriteInputSelection(input);
}

export function rememberSpriteInputSelection(input) {
  inputSelection = {
    start: Number(input.selectionStart ?? input.value.length),
    end: Number(input.selectionEnd ?? input.value.length),
  };
}
