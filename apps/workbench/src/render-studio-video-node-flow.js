import { el } from "./dom.js";
import { renderNodePrompt } from "./render-node-prompt.js";
import { renderNodeControlSummary } from "./render-node-control-summary.js";
import { renderNodeOpenContext } from "./render-studio-node-context.js";
import { nodeIcon } from "./render-studio-starter-flows.js";
import { nodeControlButton, nodeControlSelect, nodeControlToggle, selectedNodeControl } from "./studio-node-control-state.js";

export function renderVideoNodeFlow(attrs, state = {}) {
  const modes = ["文生视频", "全能参考", "图生视频", "首尾帧", "图片参考"];
  const tools = ["标记", "运镜", "角色库"];

  return el("div", { className: "libtv-video-node-flow node-flow-shell", dataset: { canvasContent: "true" }, attrs }, [
    renderNodeOpenContext(state, "video"),
    el("article", { className: "libtv-video-node-card selected", attrs: { "aria-label": "视频节点" } }, [
      el("header", {}, [
        el("span", { className: "node-icon", text: nodeIcon("video") }),
        el("strong", { text: "视频节点" }),
        el("em", { text: "1" }),
      ]),
      el("div", { className: "libtv-video-node-screen", attrs: { "aria-hidden": "true" } }, [
        el("span", { className: "play-triangle" }),
      ]),
      el("p", { text: "描述你想要生成的画面内容，@引用素材" }),
    ]),
    el("aside", { className: "libtv-video-node-control" }, [
      el("div", { className: "libtv-video-mode-tabs" }, modes.map((label, index) =>
        nodeControlButton(label, "video-mode", label, state, index === 0 ? label : ""),
      )),
      el("div", { className: "libtv-video-tool-row" }, tools.map((label) =>
        nodeControlButton(label, "video-tool", label, state, "运镜"),
      )),
      renderVideoMotionPanel(state),
      renderNodePrompt(state, {
        placeholder: "描述你想要生成的画面内容，@引用素材",
        surface: "video",
        primaryAction: "生成视频",
        note: "视频生成未启动",
      }),
      renderNodeControlSummary(state, {
        surface: "video",
        title: "视频生成设置",
        modeGroup: "video-mode",
        modeFallback: "文生视频",
        items: [
          ["模式", "video-mode", "文生视频"],
          ["工具", "video-tool", "运镜"],
          ["模型", "video-model", "Seedance 2.0 VIP"],
          ["规格", "video-spec", "16:9 / 720P / 5s"],
          ["数量", "video-count", "1个"],
          ["种子", "video-seed", "135"],
          ["镜头运动", "video-motion", "推进"],
          ["运动强度", "video-motion-strength", "标准"],
          ["主体动作", "video-subject-motion", "静止凝视"],
          ["镜头节奏", "video-motion-rhythm", "标准"],
        ],
        toggles: [
          ["联网搜索", "video-toggle-联网搜索"],
          ["素材校验", "video-toggle-自动校验素材"],
        ],
      }),
      el("p", { text: "视频节点只登记画面摘要，不上传素材、不启动生成。" }),
      el("div", { className: "libtv-video-param-grid" }, [
        nodeControlSelect("模型", "video-model", ["Seedance 2.0 VIP", "MiniMax Video", "本地预览"], state, "Seedance 2.0 VIP"),
        nodeControlSelect("规格", "video-spec", ["16:9 / 720P / 5s", "9:16 / 720P / 5s", "16:9 / 1080P / 5s"], state, "16:9 / 720P / 5s"),
        nodeControlSelect("数量", "video-count", ["1个", "2个", "4个"], state, "1个"),
        nodeControlSelect("种子", "video-seed", ["135", "随机", "锁定"], state, "135"),
      ]),
      el("div", { className: "libtv-video-switch-row" }, ["联网搜索", "自动校验素材"].map((label) =>
        nodeControlToggle(label, `video-toggle-${label}`, state),
      )),
    ]),
  ]);
}

function renderVideoMotionPanel(state) {
  const selectedTool = selectedNodeControl(state, "video-tool", "运镜");
  if (selectedTool !== "运镜") return null;
  const motion = selectedNodeControl(state, "video-motion", "推进");
  const strength = selectedNodeControl(state, "video-motion-strength", "标准");
  const subject = selectedNodeControl(state, "video-subject-motion", "静止凝视");
  const rhythm = selectedNodeControl(state, "video-motion-rhythm", "标准");
  return el("section", { className: "video-motion-panel", attrs: { "data-video-motion-panel": "true" } }, [
    el("header", {}, [
      el("strong", { text: "运镜" }),
      el("span", { text: `${motion} · ${strength} · ${rhythm}` }),
    ]),
    el("div", { className: `video-motion-preview motion-${motionClass(motion)}` }, [
      el("span", { className: "video-motion-frame" }),
      el("span", { className: "video-motion-path", attrs: { "aria-hidden": "true" } }),
      el("span", { className: "video-motion-camera", text: "CAM" }),
      el("small", { text: subject }),
    ]),
    motionControlGroup("镜头运动", "video-motion", ["推进", "拉远", "横移", "环绕", "上摇", "手持"], state, "推进"),
    motionControlGroup("运动强度", "video-motion-strength", ["轻微", "标准", "强"], state, "标准"),
    motionControlGroup("主体动作", "video-subject-motion", ["静止凝视", "走入画面", "回头", "抬头"], state, "静止凝视"),
    motionControlGroup("镜头节奏", "video-motion-rhythm", ["慢", "标准", "快"], state, "标准"),
  ]);
}

function motionControlGroup(label, group, values, state, fallback) {
  return el("article", { className: "video-motion-control" }, [
    el("span", { text: label }),
    el("div", {}, values.map((value) => nodeControlButton(value, group, value, state, fallback))),
  ]);
}

function motionClass(value) {
  const classes = { "推进": "push", "拉远": "pull", "横移": "track", "环绕": "orbit", "上摇": "tilt", "手持": "handheld" };
  return classes[value] || "push";
}
