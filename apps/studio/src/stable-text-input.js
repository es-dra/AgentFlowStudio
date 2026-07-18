const EDITOR_EVENT_NAMES = [
  "pointerdown",
  "keydown",
  "keyup",
  "beforeinput",
  "paste",
  "compositionstart",
  "compositionupdate",
  "compositionend",
  "wheel",
];

export function bindStableTextInputLifecycle(textarea, onCommit, options = {}) {
  if (!textarea || typeof onCommit !== "function") return;
  let composing = false;

  textarea.addEventListener("compositionstart", (event) => {
    composing = true;
    textarea.dataset.afsComposing = "true";
    event.stopPropagation();
    options.onCompositionStart?.(event);
  });

  textarea.addEventListener("compositionupdate", (event) => {
    event.stopPropagation();
    options.onCompositionUpdate?.(event);
  });

  textarea.addEventListener("compositionend", (event) => {
    composing = false;
    textarea.dataset.afsComposing = "false";
    event.stopPropagation();
    queueMicrotask(() => onCommit({ reason: "compositionend", inputType: event.inputType || "" }));
    options.onCompositionEnd?.(event);
  });

  textarea.addEventListener("beforeinput", (event) => {
    event.stopPropagation();
    options.onBeforeInput?.(event);
  });

  textarea.addEventListener("input", (event) => {
    event.stopPropagation();
    if (composing || textarea.dataset.afsComposing === "true") return;
    onCommit({ reason: "input", inputType: event.inputType || "" });
  });

  textarea.addEventListener("paste", (event) => {
    event.stopPropagation();
    options.onPaste?.(event);
  });

  textarea.addEventListener("keydown", (event) => {
    options.onKeyDown?.(event);
    event.stopPropagation();
  });

  textarea.addEventListener("keyup", (event) => {
    event.stopPropagation();
    options.onKeyUp?.(event);
  });

  textarea.addEventListener("blur", () => {
    composing = false;
    textarea.dataset.afsComposing = "false";
    onCommit({ reason: "blur", inputType: "" });
  });

  textarea.addEventListener("pointerdown", (event) => event.stopPropagation());
  textarea.addEventListener("wheel", (event) => event.stopPropagation(), { passive: true });
}

export function isStableTextInputEvent(event) {
  return EDITOR_EVENT_NAMES.includes(event?.type || "");
}
