import { el } from "./dom.js";

export function renderScriptStarterFlow(attrs) {
  return el("div", { className: "libtv-script-flow", dataset: { canvasContent: "true" }, attrs }, [
    el("article", { className: "libtv-script-node selected", attrs: { "aria-label": "剧本内容节点" } }, [
      el("header", {}, [
        el("span", { className: "node-icon", text: nodeIcon("script") }),
        el("strong", { text: "剧本" }),
      ]),
      el("div", { className: "libtv-script-scroll" }, [
        el("h3", { text: "《我在盛唐写天下》" }),
        el("p", { text: "类型：古风 / 穿越 / 爽文短剧" }),
        el("p", { text: "时长建议：60-90秒" }),
        el("p", { text: "基调：热血、史诗感、爽点节奏" }),
        el("p", { text: "序幕：现代深夜办公室，主角在加班中进入盛唐。" }),
        el("p", { text: "第一幕：金銮殿上临场作诗，冲突和反转同时出现。" }),
      ]),
    ]),
    el("div", { className: "libtv-script-connector", attrs: { "aria-hidden": "true" } }, [
      el("span", { className: "connector-dot" }),
      el("span", { className: "connector-line" }),
    ]),
    el("div", { className: "libtv-edit-tip", text: "双击剧本内容，可直接编辑或替换" }),
    el("article", { className: "libtv-script-target", attrs: { "aria-label": "下游生成节点" } }, [
      el("span", { className: "preview-bars", attrs: { "aria-hidden": "true" } }),
    ]),
    el("aside", { className: "libtv-script-control-card" }, [
      el("span", { className: "node-icon", text: nodeIcon("script") }),
      el("strong", { text: "根据我上传的剧本生成一个完整的故事脚本" }),
      el("div", { className: "libtv-script-control-row" }, [
        el("button", { text: "GVLM 3.1", attrs: { type: "button" } }),
        el("button", { text: "生成前检查", attrs: { type: "button" } }),
        el("small", { text: "Provider 未启动" }),
      ]),
    ]),
  ]);
}

export function renderCharacterStarterFlow(attrs) {
  return el("div", { className: "libtv-character-flow", dataset: { canvasContent: "true" }, attrs }, [
    renderCharacterToolbar(),
    el("article", { className: "libtv-character-source selected", attrs: { "aria-label": "角色图节点" } }, [
      el("header", {}, [
        el("span", { className: "node-icon", text: nodeIcon("character") }),
        el("strong", { text: "角色图" }),
      ]),
      el("div", { className: "libtv-character-portrait", attrs: { "aria-hidden": "true" } }, [
        el("span", { className: "portrait-head" }),
        el("span", { className: "portrait-body" }),
      ]),
      el("button", { className: "libtv-character-upload", text: "替换上传", attrs: { type: "button" } }),
    ]),
    el("div", { className: "libtv-character-connector", attrs: { "aria-hidden": "true" } }, [
      el("span", { className: "connector-dot" }),
      el("span", { className: "connector-line" }),
    ]),
    el("div", { className: "libtv-character-replace-tip", text: "点击按钮，可替换上传你的角色图" }),
    el("article", { className: "libtv-character-result", attrs: { "aria-label": "角色三视图节点" } }, [
      el("header", {}, [
        el("span", { className: "node-icon", text: nodeIcon("character") }),
        el("strong", { text: "角色三视图" }),
      ]),
      el("div", { className: "libtv-three-view-grid" }, ["正面", "侧面", "背面"].map((label) =>
        el("figure", { className: "libtv-three-view-card" }, [
          el("span", { className: "view-silhouette", attrs: { "aria-hidden": "true" } }),
          el("figcaption", { text: label }),
        ]),
      )),
      el("footer", {}, [
        el("span", { text: "一致性检查" }),
        el("small", { text: "生成器未启动" }),
      ]),
    ]),
    el("aside", { className: "libtv-character-status" }, [
      el("strong", { text: "Provider Gate 未授权" }),
      el("span", { text: "仅展示安全占位与画布结构，不复制真实站图片或启动生成。" }),
    ]),
  ]);
}

export function renderImageVideoStarterFlow(attrs) {
  return el("div", { className: "libtv-image-video-flow", dataset: { canvasContent: "true" }, attrs }, [
    el("article", { className: "libtv-first-frame-source selected", attrs: { "aria-label": "首帧图节点" } }, [
      el("header", {}, [
        el("span", { className: "node-icon", text: nodeIcon("image") }),
        el("strong", { text: "首帧" }),
      ]),
      el("div", { className: "libtv-first-frame-preview", attrs: { "aria-hidden": "true" } }, [
        el("span", { className: "frame-sun" }),
        el("span", { className: "frame-ridge" }),
      ]),
      el("button", { className: "libtv-frame-upload", text: "替换上传", attrs: { type: "button" } }),
    ]),
    el("div", { className: "libtv-video-connector", attrs: { "aria-hidden": "true" } }, [
      el("span", { className: "connector-dot" }),
      el("span", { className: "connector-line" }),
    ]),
    el("div", { className: "libtv-video-replace-tip", text: "点击按钮，可替换上传你的首帧图" }),
    el("article", { className: "libtv-video-result", attrs: { "aria-label": "视频结果节点" } }, [
      el("header", {}, [
        el("span", { className: "node-icon", text: "▶" }),
        el("strong", { text: "视频" }),
      ]),
      el("div", { className: "libtv-video-preview", attrs: { "aria-hidden": "true" } }, [
        el("span", { className: "play-triangle" }),
      ]),
    ]),
    el("aside", { className: "libtv-video-control-card" }, [
      el("div", { className: "libtv-video-mode-tabs" }, ["文生视频", "全能参考", "图生视频", "首尾帧", "图片参考"].map((label, index) =>
        el("button", { className: index === 1 ? "active" : "", text: label, attrs: { type: "button" } }),
      )),
      el("div", { className: "libtv-video-tool-row" }, ["标记", "运镜", "角色库"].map((label) =>
        el("button", { text: label, attrs: { type: "button" } }),
      )),
      el("p", { text: "描述你想要生成的画面内容，@引用素材" }),
      el("div", { className: "libtv-video-param-row" }, [
        el("button", { text: "Seedance 2.0 VIP", attrs: { type: "button" } }),
        el("button", { text: "16:9 · 720P · 5s ·", attrs: { type: "button" } }),
        el("small", { text: "视频生成未启动" }),
      ]),
    ]),
  ]);
}

export function renderAudioVideoStarterFlow(attrs) {
  return el("div", { className: "libtv-audio-video-flow", dataset: { canvasContent: "true" }, attrs }, [
    el("article", { className: "libtv-audio-source selected", attrs: { "aria-label": "音频节点" } }, [
      el("header", {}, [
        el("span", { className: "node-icon", text: nodeIcon("audio") }),
        el("strong", { text: "音频" }),
      ]),
      el("div", { className: "libtv-audio-waveform", attrs: { "aria-hidden": "true" } },
        [24, 38, 52, 34, 64, 46, 28, 58, 42, 70, 36, 54].map((height) =>
          el("span", { attrs: { style: `height:${height}px` } }),
        ),
      ),
      el("div", { className: "libtv-audio-timeline" }, [
        el("span", { text: "00:00 / 00:03" }),
        el("span", { text: "00:00 / 00:03" }),
      ]),
      el("button", { className: "libtv-audio-upload", text: "选择文件上传", attrs: { type: "button" } }),
    ]),
    el("div", { className: "libtv-audio-connector", attrs: { "aria-hidden": "true" } }, [
      el("span", { className: "connector-dot" }),
      el("span", { className: "connector-line" }),
    ]),
    el("div", { className: "libtv-audio-replace-tip", text: "点击按钮，可替换上传你的音频文件" }),
    el("article", { className: "libtv-audio-video-result", attrs: { "aria-label": "音频驱动视频结果节点" } }, [
      el("header", {}, [
        el("span", { className: "node-icon", text: "▶" }),
        el("strong", { text: "视频" }),
        el("small", { text: "图片" }),
      ]),
      el("div", { className: "libtv-audio-video-preview", attrs: { "aria-hidden": "true" } }, [
        el("span", { className: "play-triangle" }),
      ]),
    ]),
    el("aside", { className: "libtv-audio-control-card" }, [
      el("div", { className: "libtv-audio-mode-tabs" }, ["文生视频", "全能参考", "图生视频", "首尾帧", "图片参考"].map((label, index) =>
        el("button", { className: index === 1 ? "active" : "", text: label, attrs: { type: "button" } }),
      )),
      el("div", { className: "libtv-audio-tool-row" }, ["标记", "运镜", "角色库"].map((label) =>
        el("button", { text: label, attrs: { type: "button" } }),
      )),
      el("p", { text: "根据上传的音频生成对应场景画面，镜头语言、节奏、音乐匹配情绪变化，电影级质感。" }),
      el("div", { className: "libtv-audio-param-row" }, [
        el("button", { text: "Seedance 2.0 VIP", attrs: { type: "button" } }),
        el("button", { text: "16:9 · 720P · 5s ·", attrs: { type: "button" } }),
        el("button", { text: "1个", attrs: { type: "button" } }),
        el("span", { text: "135" }),
      ]),
      el("div", { className: "libtv-audio-toggle-row" }, ["联网搜索", "自动校验素材"].map((label) =>
        el("label", {}, [
          el("input", { attrs: { type: "checkbox", checked: true } }),
          el("span", { text: label }),
        ]),
      )),
      el("small", { text: "音频驱动未启动" }),
    ]),
  ]);
}

function renderCharacterToolbar() {
  const tools = [
    ["全景", "NEW"],
    ["多角度", ""],
    ["打光", ""],
    ["九宫格", ""],
    ["高清", ""],
    ["宫格切分", ""],
  ];
  return el("nav", { className: "libtv-character-toolbar", attrs: { "aria-label": "角色三视图能力条" } }, tools.map(([label, badge]) =>
    el("button", { attrs: { type: "button" } }, [
      el("span", { text: label }),
      badge ? el("em", { text: badge }) : null,
    ]),
  ));
}

export function renderStarterNodes(attrs, selectedKind = "") {
  const starters = [
    ["script", "故事脚本生成", "从需求摘要进入脚本和分镜规划"],
    ["character", "角色三视图", "准备角色设定、参考帧和一致性约束"],
    ["image", "首帧图生视频", "配置关键帧、镜头意图和安全参考"],
    ["audio", "音频生视频", "整理旁白、节奏和音频驱动画面"],
  ];
  return el("div", { className: "libtv-starter-row", dataset: { canvasContent: "true" }, attrs }, starters.map(([kind, title, summary]) =>
    el("button", {
      className: `libtv-starter-card${kind === selectedKind ? " selected" : ""}`,
      dataset: { studioStarterKind: kind },
      attrs: { type: "button" },
    }, [
      el("span", { className: "node-icon", text: nodeIcon(kind) }),
      el("strong", { text: title }),
      el("small", { text: summary }),
      el("em", { text: "去配置" }),
    ]),
  ));
}

export function selectedStarterNode(kind) {
  const labels = {
    script: ["故事脚本生成", "先整理故事目标、结构、镜头段落和安全边界。"],
    character: ["角色三视图", "先配置角色设定、视觉参考和一致性检查点。"],
    image: ["首帧图生视频", "先配置关键帧摘要、镜头意图和 provider gate。"],
    audio: ["音频生视频", "先配置旁白、节奏和音频摘要，再进入视频节点。"],
  };
  const [title, summary] = labels[kind] || ["起步节点", "选择一个生产入口开始配置。"];
  return {
    title,
    summary,
    status: "not_started",
    inspector: {
      prompt: "这是本地起步模板，不会启动真实生成能力。",
      reference_summary: "只使用 safe summary / artifact ref；不读取本地私有素材字节。",
      style_direction: "先完成计划、参考和 gate，再进入 provider-gated smoke。",
    },
  };
}

export function nodeIcon(kind) {
  const icons = {
    brief: "□",
    source: "▣",
    script: "▤",
    character: "◈",
    scene: "▧",
    review: "▥",
    memory: "●",
    gate: "⚑",
    image: "▩",
    audio: "♪",
  };
  return icons[kind] || "□";
}
