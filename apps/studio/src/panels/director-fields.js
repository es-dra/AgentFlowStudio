import { el } from "../overlay.js";
import { DIRECTOR_OBJECTS } from "../director-data.js";

export function cameraFields(obj, renderBoard) {
  return [
    numberField("FOV", obj.fov, (value) => { obj.fov = value; }),
    numberField("焦段", obj.focalLength, (value) => { obj.focalLength = value; }),
    selectField("机位高度", obj.height, ["低机位", "平视", "高机位"], (value) => { obj.height = value; }),
    selectField("景别", obj.shot, ["远景", "全景", "中景", "近景", "特写"], (value) => { obj.shot = value; }),
    textField("构图", obj.composition, (value) => { obj.composition = value; }),
    textField("注视目标", obj.lookAt, (value) => { obj.lookAt = value; }),
  ];
}

export function subjectFields(obj) {
  return [
    textField("动作状态", obj.action, (value) => { obj.action = value; }),
    textField("情绪状态", obj.emotion, (value) => { obj.emotion = value; }),
  ];
}

export function lightFields(obj) {
  return [
    numberField("强度", obj.intensity, (value) => { obj.intensity = value; }),
    numberField("色温", obj.colorTemp, (value) => { obj.colorTemp = value; }),
    numberField("柔硬", obj.softness, (value) => { obj.softness = value; }),
    numberField("距离", obj.distance, (value) => { obj.distance = value; }),
    checkField("动机光", obj.motivated, (value) => { obj.motivated = value; }),
  ];
}

export function propFields(obj, renderBoard) {
  return [
    numberField("宽度", obj.width, (value) => { obj.width = value; renderBoard(); }),
    numberField("高度", obj.height, (value) => { obj.height = value; renderBoard(); }),
    checkField("可见", obj.visible !== false, (value) => { obj.visible = value; }),
    textField("叙事作用", obj.narrative, (value) => { obj.narrative = value; }),
  ];
}

export function labelForObject(entry) {
  const found = DIRECTOR_OBJECTS.find((item) => item.kind === entry.object.kind || item.kind === entry.group);
  return found?.label || entry.group;
}

export function readonly(label, value) {
  const wrap = el("div", "p-field");
  wrap.appendChild(el("div", "p-label", label));
  wrap.appendChild(el("div", "p-readonly", value));
  return wrap;
}

export function textField(label, value, onChange, multiline = false) {
  const wrap = el("label", "p-field");
  wrap.appendChild(el("div", "p-label", label));
  const input = multiline ? document.createElement("textarea") : document.createElement("input");
  input.className = "p-input";
  input.value = value || "";
  input.addEventListener("input", () => onChange(input.value));
  wrap.appendChild(input);
  return wrap;
}

export function numberField(label, value, onChange) {
  const wrap = el("label", "p-field");
  wrap.appendChild(el("div", "p-label", label));
  const input = document.createElement("input");
  input.className = "p-input";
  input.type = "number";
  input.value = String(value ?? 0);
  input.addEventListener("input", () => onChange(Number(input.value) || 0));
  wrap.appendChild(input);
  return wrap;
}

function selectField(label, value, options, onChange) {
  const wrap = el("label", "p-field");
  wrap.appendChild(el("div", "p-label", label));
  const input = document.createElement("select");
  input.className = "p-input";
  for (const option of options) {
    const item = document.createElement("option");
    item.value = option;
    item.textContent = option;
    item.selected = option === value;
    input.appendChild(item);
  }
  input.addEventListener("change", () => onChange(input.value));
  wrap.appendChild(input);
  return wrap;
}

function checkField(label, value, onChange) {
  const wrap = el("label", "p-check");
  const input = document.createElement("input");
  input.type = "checkbox";
  input.checked = Boolean(value);
  input.addEventListener("change", () => onChange(input.checked));
  wrap.append(input, el("span", "", label));
  return wrap;
}
