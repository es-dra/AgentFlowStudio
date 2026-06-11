import { button, el } from "./dom.js";

const DIRECTOR_ELEMENTS = [
  ["key-light", "Key Light", "director-light key-light", "强度 70 / 色温 4300K / 柔硬 60"],
  ["fill-light", "Fill Light", "director-light fill-light", "强度 25 / 色温 5000K / 柔硬 80"],
  ["back-light", "Back Light", "director-light back-light", "强度 35 / 色温 5600K / 柔硬 45"],
  ["practical-light", "Practical", "director-light practical-light", "暖色台灯 / 20% / 动机光"],
  ["camera-a", "Camera A", "director-camera", "35mm / 低机位 / 中近景"],
  ["subject-a", "Subject A", "director-subject", "坐姿 / 面向窗户 / 情绪低落"],
];

export function renderDirectorDesk(attrs, state) {
  const selectedId = state.directorSelectedElementId || "key-light";
  const selected = DIRECTOR_ELEMENTS.find((item) => item[0] === selectedId) || DIRECTOR_ELEMENTS[0];
  return el("div", { className: "director-desk-board", dataset: { canvasContent: "true" }, attrs }, [
    el("section", { className: "director-reference-frame" }, [
      el("header", {}, [
        el("strong", { text: "画面参考" }),
        el("span", { text: "关键帧 / 实拍参考 / 场景图" }),
      ]),
      el("div", { className: "director-reference-image" }, [
        el("span", { text: "昏暗卧室参考" }),
      ]),
      el("p", { text: "画面重点：少年坐在床边，墙上海报可见，窗户冷光作为情绪动机。" }),
    ]),
    el("section", { className: "director-floor-plan" }, [
      el("div", { className: "director-room" }),
      ...DIRECTOR_ELEMENTS.map((item) => renderDirectorElement(item, selectedId)),
      el("span", { className: "director-prop bed", text: "床" }),
      el("span", { className: "director-prop table", text: "桌" }),
      el("span", { className: "director-prop poster", text: "海报" }),
      el("span", { className: "director-prop window", text: "窗户光" }),
      el("span", { className: "director-modifier reflector", text: "反光板" }),
      el("span", { className: "director-modifier diffusion", text: "柔光布" }),
      el("span", { className: "director-modifier flag", text: "遮光旗" }),
    ]),
    el("aside", { className: "director-inspector" }, [
      el("header", {}, [
        el("strong", { text: selected[1] }),
        el("span", { text: "布光 / 机位参数" }),
      ]),
      ...["位置", "朝向", "焦段", "机位高度", "强度", "色温", "角度", "柔硬", "距离"].map((label) =>
        el("label", {}, [
          el("span", { text: label }),
          el("input", { attrs: { value: inspectorValue(label), readonly: "readonly" } }),
        ]),
      ),
      el("p", { text: selected[3] }),
      el("div", { className: "director-action-row" }, [
        button("保存为场景资产", "save-director-setup", "primary"),
        button("生成专业提示词", "optimize-current-prompt", "secondary"),
        button("应用到当前镜头", "apply-director-setup-to-shot", "secondary"),
      ]),
    ]),
  ]);
}

function renderDirectorElement([id, label, className], selectedId) {
  return el("button", {
    className: `${className}${id === selectedId ? " selected" : ""}`,
    text: label,
    dataset: { directorElementId: id },
    attrs: { type: "button" },
  });
}

function inspectorValue(label) {
  return {
    位置: "X 4.5 / Y 2.2",
    朝向: "面向主体",
    焦段: "35mm",
    机位高度: "1.2m",
    强度: "70%",
    色温: "4300K",
    角度: "45°",
    柔硬: "Soft 60",
    距离: "2.8m",
  }[label] || "已设置";
}
