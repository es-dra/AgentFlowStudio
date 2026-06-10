import { el } from "./dom.js";
import { nodeIcon } from "./render-studio-starter-flows.js";

export function renderAudioNodeFlow(attrs) {
  const modes = ["文生视频", "全能参考", "图生视频", "首尾帧", "图片参考"];
  const tools = ["标记", "运镜", "角色库"];

  return el("div", { className: "libtv-audio-node-flow", dataset: { canvasContent: "true" }, attrs }, [
    el("article", { className: "libtv-audio-node-card selected", attrs: { "aria-label": "音频节点" } }, [
      el("header", {}, [
        el("span", { className: "node-icon", text: nodeIcon("audio") }),
        el("strong", { text: "音频节点" }),
        el("em", { text: "00:00 / 00:03" }),
      ]),
      el("div", { className: "libtv-audio-node-waveform", attrs: { "aria-hidden": "true" } }, [
        ...[34, 52, 76, 58, 88, 46, 66, 42].map((height) => el("span", { attrs: { style: `--bar-height:${height}%` } })),
      ]),
      el("p", { text: "点击按钮，可替换上传你的音频文件" }),
    ]),
    el("aside", { className: "libtv-audio-node-control" }, [
      el("div", { className: "libtv-audio-target-row" }, ["图片", "视频"].map((label, index) =>
        el("button", { className: index === 1 ? "active" : "", text: label, attrs: { type: "button" } }),
      )),
      el("div", { className: "libtv-audio-mode-tabs" }, modes.map((label, index) =>
        el("button", { className: index === 0 ? "active" : "", text: label, attrs: { type: "button" } }),
      )),
      el("div", { className: "libtv-audio-tool-row" }, tools.map((label) =>
        el("button", { text: label, attrs: { type: "button" } }),
      )),
      el("strong", { text: "根据上传的音频生成对应场景画面，镜头语言、节奏、音乐匹配情绪变化，电影级质感。" }),
      el("div", { className: "libtv-audio-param-grid" }, [
        audioParam("模型", "Seedance 2.0 VIP"),
        audioParam("规格", "16:9 · 720P · 5s"),
        audioParam("数量", "1个"),
        audioParam("种子", "135"),
      ]),
      el("div", { className: "libtv-audio-switch-row" }, ["联网搜索", "自动校验素材"].map((label) =>
        el("button", { text: label, attrs: { type: "button", "aria-pressed": "false" } }),
      )),
      el("p", { text: "音频节点只登记音频摘要，不读取本地文件字节、不启动生成。" }),
      el("small", { text: "音频生成未启动" }),
    ]),
  ]);
}

function audioParam(label, value) {
  return el("article", {}, [
    el("span", { text: label }),
    el("strong", { text: value }),
  ]);
}
