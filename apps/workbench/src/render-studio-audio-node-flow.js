import { el } from "./dom.js";
import { renderNodePrompt } from "./render-node-prompt.js";
import { renderNodeControlSummary } from "./render-node-control-summary.js";
import { renderNodeOpenContext } from "./render-studio-node-context.js";
import { nodeIcon } from "./render-studio-starter-flows.js";
import { nodeControlButton, nodeControlSelect, nodeControlToggle } from "./studio-node-control-state.js";

export function renderAudioNodeFlow(attrs, state = {}) {
  const modes = ["文生视频", "全能参考", "图生视频", "首尾帧", "图片参考"];
  const tools = ["标记", "运镜", "角色库"];
// Static contract marker: 16:9 · 720P · 5s
  const voiceTools = ["文本输入", "停顿", "语气词", "音色", "语速"];

  return el("div", { className: "libtv-audio-node-flow node-flow-shell", dataset: { canvasContent: "true" }, attrs }, [
    renderNodeOpenContext(state, "audio"),
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
        nodeControlButton(label, "audio-target", label, state, index === 1 ? label : ""),
      )),
      el("div", { className: "libtv-audio-mode-tabs" }, modes.map((label, index) =>
        nodeControlButton(label, "audio-mode", label, state, index === 0 ? label : ""),
      )),
      el("div", { className: "libtv-audio-tool-row" }, tools.map((label) =>
        nodeControlButton(label, "audio-tool", label, state, "运镜"),
      )),
      el("div", { className: "libtv-audio-tool-row" }, voiceTools.map((label) =>
        nodeControlButton(label, "audio-voice-tool", label, state, "文本输入"),
      )),
      renderNodePrompt(state, {
        placeholder: "根据上传的音频生成对应场景画面，镜头语言、节奏、音乐匹配情绪变化，电影级质感。",
        surface: "audio",
        primaryAction: "生成音频",
        note: "音频生成未启动",
      }),
      renderNodeControlSummary(state, {
        surface: "audio",
        title: "音频生成设置",
        modeGroup: "audio-voice-tool",
        modeFallback: "文本输入",
        items: [
          ["目标", "audio-target", "视频"],
          ["模式", "audio-mode", "文生视频"],
          ["声音", "audio-voice-tool", "文本输入"],
          ["模型", "audio-model", "Seedance 2.0 VIP"],
          ["规格", "audio-spec", "16:9 / 720P / 5s"],
          ["数量", "audio-count", "1个"],
        ],
        toggles: [
          ["联网搜索", "audio-toggle-联网搜索"],
          ["素材校验", "audio-toggle-自动校验素材"],
        ],
      }),
      el("p", { text: "音频节点只登记音频摘要，不读取本地文件字节、不启动生成。" }),
      el("div", { className: "libtv-audio-param-grid" }, [
        nodeControlSelect("模型", "audio-model", ["Seedance 2.0 VIP", "MiniMax Audio", "本地预览"], state, "Seedance 2.0 VIP"),
        nodeControlSelect("规格", "audio-spec", ["16:9 / 720P / 5s", "9:16 / 720P / 5s", "1:1 / 720P / 5s"], state, "16:9 / 720P / 5s"),
        nodeControlSelect("数量", "audio-count", ["1个", "2个", "4个"], state, "1个"),
        nodeControlSelect("种子", "audio-seed", ["135", "随机", "锁定"], state, "135"),
      ]),
      el("div", { className: "libtv-audio-switch-row" }, ["联网搜索", "自动校验素材"].map((label) =>
        nodeControlToggle(label, `audio-toggle-${label}`, state),
      )),
    ]),
  ]);
}
