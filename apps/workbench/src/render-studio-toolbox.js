import { el } from "./dom.js";

const TV_TOOLBOX_ITEMS = [
  ["angles", "多角度", "为当前节点补充分镜整理、全景、中景、近景和可复用参考角度。", "ANG"],
  ["motion", "运镜标记", "整理机位运镜、推拉摇移、速度、方向和镜头衔接。", "MOV"],
  ["keyframes", "首尾帧", "标记首帧、尾帧、动作变化和负面提示词边界。", "KEY"],
  ["enhance_image", "图片高清", "整理图片高清、画面细节、材质清晰度和灯光方案。", "2K"],
  ["text_music", "文字生音乐", "把文字情绪转为音乐节奏、段落、氛围和旁白停顿。", "AUD"],
  ["character_library", "角色库", "复用角色一致性、服装轮廓、面部特征和三视图约束。", "CHR"],
];

export function renderToolboxPanel(state = {}) {
  const active = TV_TOOLBOX_ITEMS.find(([kind]) => state.studioToolIntent === kind);
  return el("div", { className: "libtv-floating libtv-toolbox-panel" }, [
    el("header", { className: "libtv-panel-header" }, [
      el("h2", { text: "TV工具箱" }),
      el("span", { text: "选择工具后会带入当前节点" }),
    ]),
    el("section", { className: "libtv-toolbox-body" }, [
      el("div", { className: "libtv-toolbox-section" }, [
        el("h3", { text: "节点辅助工具" }),
        ...TV_TOOLBOX_ITEMS.map(([kind, title, summary, icon]) => renderToolRow(kind, title, summary, icon, state)),
      ]),
      active ? renderToolboxStatus(active) : renderToolboxStatus(["idle", "等待选择", "尚未登记工具意图。", "KIT"]),
      el("p", {
        className: "libtv-safe-tool-note",
        text: "当前只登记本地工具意图，未创建真实任务，未启动 provider。",
      }),
    ]),
  ]);
}

function renderToolRow(kind, title, summary, icon, state) {
  return el("button", {
    className: `libtv-tv-tool-row${state.studioToolIntent === kind ? " active" : ""}`,
    attrs: { type: "button", "data-toolbox-intent": kind },
  }, [
    el("span", { className: "node-icon", text: icon }),
    el("strong", { text: title }),
    el("small", { text: summary }),
  ]);
}

function renderToolboxStatus([kind, title, summary]) {
  const hasIntent = kind !== "idle";
  return el("div", { className: "libtv-toolbox-status" }, [
    el("h3", { text: hasIntent ? "本地工具意图已登记" : "本地工具待选择" }),
    el("strong", { text: title }),
    el("p", { text: summary }),
    el("ul", { className: "libtv-tool-intent-flow" }, [
      intentStep("工具选择", hasIntent ? "status-done" : "status-active", "仅写入浏览器本地状态"),
      intentStep("任务创建", "status-locked", "未创建真实任务"),
      intentStep("生成能力", "status-locked", "未启动 provider"),
    ]),
  ]);
}

function intentStep(label, status, detail) {
  return el("li", { className: status }, [
    el("span", { text: label }),
    el("small", { text: detail }),
  ]);
}
