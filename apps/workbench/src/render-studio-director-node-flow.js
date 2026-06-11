import { el } from "./dom.js";
import { directorElements, directorPromptContext, selectedDirectorElement } from "./director-setup-model.js";
import { renderNodeOpenContext } from "./render-studio-node-context.js";

export function renderDirectorFlowV3(attrs, state = {}) {
  const elements = directorElements(state);
  const selected = selectedDirectorElement(state);
  return el("div", { className: "libtv-director-flow director-flow-v3 node-flow-shell", dataset: { canvasContent: "true" }, attrs }, [
    renderNodeOpenContext(state, "director"),
    el("section", { className: "libtv-director-canvas" }, [
      el("header", { className: "libtv-director-toolbar" }, [
        el("strong", { text: "导演台" }),
        ...["导演视角", "机位视角", "场景"].map((label, index) =>
          el("button", { className: index === 0 ? "active" : "", text: label, attrs: { type: "button" } }),
        ),
      ]),
      el("aside", { className: "libtv-director-reference" }, [
        el("strong", { text: "画面参考" }),
        el("span", { text: "选择关键帧或上传画面，辅助整理灯光、机位和场景布置。" }),
      ]),
      el("div", { className: "libtv-director-stage" }, [
        el("div", { className: "libtv-director-grid", attrs: { "aria-hidden": "true" } }),
        el("div", { className: "libtv-director-room", attrs: { "aria-hidden": "true" } }),
        ...elements.map((item) => renderDirectorObject(item, selected.id)),
      ]),
      el("div", { className: "libtv-director-object-list" }, [
        el("input", { attrs: { placeholder: "搜索场景对象", autocomplete: "off" } }),
        ...elements.slice(0, 8).map((item) => el("button", {
          className: item.id === selected.id ? "active" : "",
          text: item.label,
          dataset: { directorElementId: item.id },
          attrs: { type: "button" },
        })),
      ]),
      el("div", { className: "libtv-director-action-row" }, ["移动 (V)", "添加角色", "全景图", "添加机位"].map((label) =>
        el("button", { text: label, attrs: { type: "button" } }),
      )),
    ]),
    el("aside", { className: "libtv-director-camera-panel" }, [
      el("header", {}, [
        el("strong", { text: selected.label }),
        el("span", { text: selected.kind === "light" ? "灯光属性" : "对象属性" }),
        el("em", { text: state.directorSaveStatus || "本地预览" }),
      ]),
      el("button", { className: "libtv-director-reset", text: "重置视角", attrs: { type: "button" } }),
      el("section", {}, [
        labelRow("名称", selected.label),
        labelInput("位置 X / Y", `${Math.round(selected.x)} / ${Math.round(selected.y)}`),
        labelRow("说明", selected.summary),
        ...renderDirectorProps(selected),
      ]),
      el("div", { className: "libtv-director-fov" }, [
        el("strong", { text: "视野角度 (FOV)" }),
        el("span", { text: selected.props?.fov || "FOV 50°" }),
        el("p", { text: "拖动俯视图对象会同步更新位置；保存后会作为导演台布光资产参与后续提示词。" }),
      ]),
      el("div", { className: "libtv-director-action-row" }, ["相机截图", "选择画幅比例", "截图", "AI 识图导入", "全屏"].map((label) =>
        el("button", { text: label, attrs: { type: "button" } }),
      )),
      el("div", { className: "libtv-director-action-row output-row" }, [
        ["保存为场景资产", "save-director-setup"],
        ["生成专业提示词片段", "optimize-current-prompt"],
        ["应用到当前镜头", "apply-director-setup-to-shot"],
        ["生成导演台布光图", "save-director-setup"],
      ].map(([label, action]) => el("button", { text: label, attrs: { type: "button", "data-action": action } }))),
      el("small", { text: state.directorAppliedShotContext || directorPromptContext(state).slice(0, 72) }),
    ]),
  ]);
}

function renderDirectorObject(item, selectedId) {
  return el("button", {
    className: `${item.className}${item.id === selectedId ? " selected" : ""}`,
    text: item.label,
    dataset: { directorElementId: item.id },
    attrs: {
      type: "button",
      "data-director-drag-id": item.id,
      style: `left:${item.x}%;top:${item.y}%;`,
      title: item.summary,
    },
  });
}

function renderDirectorProps(selected) {
  return Object.entries(selected.props || {}).slice(0, 4).map(([label, value]) => labelInput(label, value));
}

function labelRow(label, value) {
  return el("label", {}, [
    el("span", { text: label }),
    el("strong", { text: value }),
  ]);
}

function labelInput(label, value) {
  return el("label", {}, [
    el("span", { text: label }),
    el("input", { attrs: { value, readonly: "readonly" } }),
  ]);
}
