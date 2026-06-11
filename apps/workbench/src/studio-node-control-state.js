import { el } from "./dom.js";

export function selectedNodeControl(state, group, fallback = "") {
  return state.nodeControlSelections?.[group] || fallback;
}

export function selectNodeControl(state, group, value) {
  if (!group || !value) return;
  state.nodeControlSelections = {
    ...(state.nodeControlSelections || {}),
    [group]: value,
  };
  state.lastResult = {
    status: "node_control_updated",
    message: `${group}:${value}`,
  };
}

export function nodeControlButton(label, group, value, state, fallback = "") {
  const controlValue = value || label;
  const active = selectedNodeControl(state, group, fallback) === controlValue;
  return el("button", {
    className: active ? "active node-control-active" : "",
    text: label,
    dataset: { nodeControl: group, nodeControlValue: controlValue },
    attrs: { type: "button", "aria-pressed": active ? "true" : "false" },
  });
}

export function nodeControlSelect(label, group, options, state, fallback = "") {
  const selected = selectedNodeControl(state, group, fallback || optionValue(options[0]));
  return el("article", { className: "node-control-select", attrs: { "data-node-control-group": group } }, [
    el("span", { text: label }),
    el("strong", { text: selected }),
    el("div", { className: "node-control-options" }, options.map((option) =>
      nodeControlButton(optionLabel(option), group, optionValue(option), state, fallback || optionValue(options[0])),
    )),
  ]);
}

export function nodeControlToggle(label, group, state) {
  const selected = selectedNodeControl(state, group, "off");
  const nextValue = selected === "on" ? "off" : "on";
  return el("button", {
    className: selected === "on" ? "active node-control-active" : "",
    text: label,
    dataset: { nodeControl: group, nodeControlValue: nextValue },
    attrs: { type: "button", "aria-pressed": selected === "on" ? "true" : "false" },
  });
}

function optionLabel(option) {
  return Array.isArray(option) ? option[0] : option;
}

function optionValue(option) {
  return Array.isArray(option) ? option[1] : option;
}
