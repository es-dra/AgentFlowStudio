import { el } from "./dom.js";
import { nodeIcon } from "./render-studio-starter-flows.js";

export function renderVideoNodeFlow(attrs) {
  const modes = ["文生视频", "全能参考", "图生视频", "首尾帧", "图片参考"];
  const tools = ["标记", "运镜", "角色库"];

  return el("div", { className: "libtv-video-node-flow", dataset: { canvasContent: "true" }, attrs }, [
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
        el("button", { className: index === 0 ? "active" : "", text: label, attrs: { type: "button" } }),
      )),
      el("div", { className: "libtv-video-tool-row" }, tools.map((label) =>
        el("button", { text: label, attrs: { type: "button" } }),
      )),
      el("div", { className: "libtv-video-param-grid" }, [
        videoParam("模型", "Seedance 2.0 VIP"),
        videoParam("规格", "16:9 · 720P · 5s"),
        videoParam("数量", "1个"),
        videoParam("种子", "135"),
      ]),
      el("div", { className: "libtv-video-switch-row" }, ["联网搜索", "自动校验素材"].map((label) =>
        el("button", { text: label, attrs: { type: "button", "aria-pressed": "false" } }),
      )),
      el("p", { text: "视频节点只登记画面摘要，不上传素材、不启动生成。" }),
      el("small", { text: "视频生成未启动" }),
    ]),
  ]);
}

function videoParam(label, value) {
  return el("article", {}, [
    el("span", { text: label }),
    el("strong", { text: value }),
  ]);
}
