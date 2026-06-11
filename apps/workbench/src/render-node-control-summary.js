import { el } from "./dom.js";
import { selectedNodeControl } from "./studio-node-control-state.js";

const MODE_HINTS = {
  image: {
    "图生图": "保留上传图的主体关系，优先调整画面内容和局部细节。",
    "图片高清": "面向最终可用素材，强化清晰度、边缘和材质一致性。",
    "风格": "把当前描述转成风格参考，方便复用到后续关键帧。",
    "标记": "记录局部修改点，后续生成会优先保持主体不漂移。",
  },
  video: {
    "文生视频": "从纯文字生成镜头，重点关注主体、运动和镜头节奏。",
    "全能参考": "综合素材、角色和场景参考生成，适合保持连续性。",
    "图生视频": "以首帧为主约束生成运动，降低人物和场景漂移。",
    "首尾帧": "用起止画面约束镜头变化，适合明确动作路径。",
    "图片参考": "把图片作为画面气质和构图参考，不直接读取原始文件。",
  },
  audio: {
    "文本输入": "按台词和旁白生成声音内容，适合先定语义。",
    "停顿": "调整句间节奏，让画面剪辑点更自然。",
    "语气词": "增强口语化表达，适合角色对白。",
    "音色": "锁定声音气质，方便后续复用。",
    "语速": "控制节奏密度，和 5s 镜头长度对齐。",
  },
};

export function renderNodeControlSummary(state, config) {
  const surface = config.surface || "node";
  const activeMode = selectedNodeControl(state, config.modeGroup || "", config.modeFallback || "");
  const rows = (config.items || []).map(([label, group, fallback]) => [
    label,
    selectedNodeControl(state, group, fallback),
  ]);
  const toggles = (config.toggles || []).map(([label, group]) => [
    label,
    selectedNodeControl(state, group, "off") === "on" ? "开启" : "关闭",
  ]);
  return el("section", {
    className: "node-control-summary",
    attrs: {
      "data-node-control-summary": surface,
      "data-active-node-mode": activeMode,
    },
  }, [
    el("header", {}, [
      el("strong", { text: config.title || "当前设置" }),
      activeMode ? el("small", { text: activeMode }) : null,
    ]),
    el("div", { className: "node-control-summary-chips" }, rows.map(([label, value]) =>
      el("span", { attrs: { "data-node-control-summary-chip": label } }, [
        el("em", { text: label }),
        el("b", { text: value }),
      ]),
    )),
    toggles.length ? el("div", { className: "node-control-summary-toggles" }, toggles.map(([label, value]) =>
      el("span", { className: value === "开启" ? "enabled" : "", text: `${label} ${value}` }),
    )) : null,
    el("p", {
      className: "node-control-summary-hint",
      text: modeHint(surface, activeMode, config.fallbackHint),
    }),
  ]);
}

function modeHint(surface, mode, fallback = "点击上方控制项后，当前节点的生成设置会立即同步。") {
  return MODE_HINTS[surface]?.[mode] || fallback;
}
