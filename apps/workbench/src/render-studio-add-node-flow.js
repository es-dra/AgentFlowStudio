import { el } from "./dom.js";
import { nodeIcon } from "./render-studio-starter-flows.js";
import { renderAudioNodeFlow } from "./render-studio-audio-node-flow.js";
import { renderVideoNodeFlow } from "./render-studio-video-node-flow.js";

const ADD_NODE_CONFIG = {
  text: {
    title: "文本",
    kindLabel: "剧本、广告词、品牌文案",
    prompt: "输入剧本、广告词或品牌文案要求",
    status: "文本生成未启动",
    tools: ["剧本", "广告词", "品牌文案"],
  },
  image: {
    title: "图片",
    kindLabel: "海报、分镜、角色设计",
    prompt: "描述海报、分镜或角色设计",
    status: "图片生成未启动",
    tools: ["海报", "分镜", "角色设计"],
  },
  video: {
    title: "视频",
    kindLabel: "创意广告、动画、电影",
    prompt: "描述创意广告、动画或电影片段",
    status: "视频生成未启动",
    tools: ["文生视频", "图生视频", "首尾帧"],
  },
  video_merge: {
    title: "视频合成",
    kindLabel: "多个视频片段合为一个",
    prompt: "排列需要合成为一条成片的视频片段",
    status: "视频合成未启动",
    tools: ["片段排序", "转场", "节奏"],
  },
  director: {
    title: "导演台",
    kindLabel: "搭建3D场景，截图作为构图参考",
    prompt: "搭建镜头构图、机位和场景走位",
    status: "导演台未启动",
    tools: ["机位", "场景", "截图参考"],
  },
  audio: {
    title: "音频",
    kindLabel: "音效、配音、音乐",
    prompt: "描述音效、配音或音乐方向",
    status: "音频生成未启动",
    tools: ["音效", "配音", "音乐"],
  },
  script: {
    title: "脚本",
    kindLabel: "创意脚本、生成故事板",
    prompt: "输入创意脚本或故事板方向",
    status: "脚本生成未启动",
    tools: ["创意脚本", "故事板", "分镜"],
  },
};

export function selectedAddNode(kind) {
  const config = ADD_NODE_CONFIG[kind] || ADD_NODE_CONFIG.text;
  return {
    title: config.title,
    summary: config.kindLabel,
    status: "not_started",
    inspector: {
      prompt: config.prompt,
      reference_summary: "选择节点只创建本地安全占位，不上传素材、不启动生成。",
      style_direction: "保持 provider gate 关闭，后续再按能力授权接入真实生成。",
    },
  };
}

export function renderAddNodeFlow(kind, attrs) {
  if (kind === "director") return renderDirectorFlow(attrs);
  if (kind === "video_merge") return renderVideoMergeFlow(attrs);
  if (kind === "text") return renderTextNodeFlow(attrs);
  if (kind === "image") return renderImageNodeFlow(attrs);
  if (kind === "video") return renderVideoNodeFlow(attrs);
  if (kind === "audio") return renderAudioNodeFlow(attrs);
  if (kind === "script") return renderScriptGeneratorFlow(attrs);

  const config = ADD_NODE_CONFIG[kind] || ADD_NODE_CONFIG.text;
  return el("div", { className: "libtv-add-node-flow", dataset: { canvasContent: "true" }, attrs }, [
    el("article", { className: "libtv-added-node selected", attrs: { "aria-label": `${config.title}节点` } }, [
      el("header", {}, [
        el("span", { className: "node-icon", text: nodeIcon(kind) }),
        el("strong", { text: config.title }),
        el("em", { className: "libtv-added-node-kind", text: config.kindLabel }),
      ]),
      el("div", { className: "libtv-added-node-preview", attrs: { "aria-hidden": "true" } }, [
        el("span", { className: "preview-bars" }),
        el("span", { className: "preview-bars" }),
      ]),
      el("p", { text: config.prompt }),
    ]),
    el("div", { className: "libtv-added-node-connector", attrs: { "aria-hidden": "true" } }, [
      el("span", { className: "connector-dot" }),
      el("span", { className: "connector-line" }),
    ]),
    el("aside", { className: "libtv-added-node-control" }, [
      el("strong", { text: config.prompt }),
      el("div", { className: "libtv-added-node-tabs" }, config.tools.map((label, index) =>
        el("button", { className: index === 0 ? "active" : "", text: label, attrs: { type: "button" } }),
      )),
      el("p", { text: "选择节点只创建本地安全占位，不上传素材、不启动生成。" }),
      el("small", { text: config.status }),
    ]),
  ]);
}

export function renderTextNodeFlow(attrs) {
  const attempts = ["自己编写内容", "文生视频", "图片反推提示词", "文字生音乐"];
  return el("div", { className: "libtv-text-node-flow", dataset: { canvasContent: "true" }, attrs }, [
    el("article", { className: "libtv-text-node-card selected", attrs: { "aria-label": "文本节点 2" } }, [
      el("header", {}, [
        el("span", { className: "node-icon", text: nodeIcon("text") }),
        el("strong", { text: "文本节点 2" }),
      ]),
      el("div", { className: "libtv-text-node-placeholder", attrs: { "aria-hidden": "true" } }, [
        el("span", { className: "preview-bars" }),
        el("span", { className: "preview-bars" }),
        el("span", { className: "preview-bars" }),
      ]),
      renderAttemptGroup(attempts, "libtv-text-attempts"),
    ]),
    el("aside", { className: "libtv-text-generator-control" }, [
      el("strong", { text: "写下你想讲的故事、场景或角色设定。例如：一个来自未来的机器人，在城市屋顶看星星。" }),
      el("div", { className: "libtv-text-model-row" }, [
        el("span", { text: "GVLM 3.1" }),
        el("span", { text: "1" }),
      ]),
      el("p", { text: "文本只登记安全摘要，不上传素材、不启动生成。" }),
      el("small", { text: "文本生成未启动" }),
    ]),
  ]);
}

export function renderScriptGeneratorFlow(attrs) {
  const scriptAttempts = ["剧本生成分镜脚本", "视频参考生成分镜脚本", "角色生成分镜脚本"];
  const textAttempts = ["自己编写内容", "文生视频", "图片反推提示词", "文字生音乐"];
  return el("div", { className: "libtv-script-generator-flow", dataset: { canvasContent: "true" }, attrs }, [
    el("article", { className: "libtv-script-generator-card selected", attrs: { "aria-label": "脚本生成器" } }, [
      el("header", {}, [
        el("span", { className: "node-icon", text: nodeIcon("script") }),
        el("strong", { text: "脚本生成器" }),
      ]),
      el("div", { className: "libtv-script-placeholder", attrs: { "aria-hidden": "true" } }, [
        el("span", { className: "preview-bars" }),
      ]),
      renderAttemptGroup(scriptAttempts),
    ]),
    el("aside", { className: "libtv-script-generator-control" }, [
      el("strong", { text: "描述剧情或添加角色参考、视频参考等，为你生成分镜脚本" }),
      el("div", { className: "libtv-script-model-row" }, [
        el("span", { text: "GVLM 3.1" }),
        el("span", { text: "1" }),
      ]),
      el("p", { text: "参考文本只登记安全摘要，不上传素材、不启动生成。" }),
      el("small", { text: "脚本生成未启动" }),
    ]),
    el("article", { className: "libtv-script-reference-node" }, [
      el("header", {}, [
        el("span", { className: "node-icon", text: nodeIcon("text") }),
        el("strong", { text: "文本节点 2" }),
      ]),
      renderAttemptGroup(textAttempts),
    ]),
  ]);
}

export function renderImageNodeFlow(attrs) {
  return el("div", { className: "libtv-image-node-flow", dataset: { canvasContent: "true" }, attrs }, [
    el("article", { className: "libtv-image-node-card selected", attrs: { "aria-label": "图片节点" } }, [
      el("button", { className: "libtv-image-upload-pill", text: "上传", attrs: { type: "button" } }),
      el("header", {}, [
        el("span", { className: "node-icon", text: nodeIcon("image") }),
        el("strong", { text: "图片节点" }),
        el("em", { text: "5" }),
      ]),
      el("div", { className: "libtv-image-node-preview", attrs: { "aria-hidden": "true" } }, [
        el("span", { text: "▧" }),
      ]),
      el("div", { className: "libtv-image-tries" }, [
        el("span", { text: "尝试：" }),
        ...["图生图", "图片高清"].map((label) => el("button", { text: label, attrs: { type: "button" } })),
      ]),
    ]),
    el("aside", { className: "libtv-image-control-card" }, [
      el("strong", { text: "可直接文字生图，或上传图片输入文字指令对图片进行编辑，如：将背景改为雪夜" }),
      el("div", { className: "libtv-image-tool-row" }, ["图生图", "图片高清", "风格", "标记"].map((label, index) =>
        el("button", { className: index === 0 ? "active" : "", text: label, attrs: { type: "button" } }),
      )),
      el("div", { className: "libtv-image-param-grid" }, [
        imageParam("模型", "Lib Image"),
        imageParam("规格", "自适应 · 标准画质 · 2K"),
        imageParam("镜头", "摄像机 · 全景"),
        imageParam("数量", "1张 · 18"),
      ]),
      el("p", { text: "上传入口只登记安全摘要，不读取本地文件字节。" }),
      el("small", { text: "图片生成未启动" }),
    ]),
  ]);
}

function renderAttemptGroup(items, className = "libtv-script-attempts") {
  return el("div", { className }, [
    el("span", { text: "尝试：" }),
    ...items.map((label) => el("button", { text: label, attrs: { type: "button" } })),
  ]);
}

export function renderDirectorFlow(attrs) {
  return el("div", { className: "libtv-director-flow", dataset: { canvasContent: "true" }, attrs }, [
    el("section", { className: "libtv-director-canvas" }, [
      el("header", { className: "libtv-director-toolbar" }, [
        el("strong", { text: "3D导演台" }),
        ...["导演视角", "机位视角", "场景"].map((label, index) =>
          el("button", { className: index === 0 ? "active" : "", text: label, attrs: { type: "button" } }),
        ),
      ]),
      el("div", { className: "libtv-director-stage" }, [
        el("div", { className: "libtv-director-grid", attrs: { "aria-hidden": "true" } }),
        el("span", { className: "libtv-director-camera", text: "机位1" }),
        el("span", { className: "libtv-director-role", text: "角色A" }),
      ]),
      el("div", { className: "libtv-director-object-list" }, [
        el("input", { attrs: { placeholder: "搜索场景对象", autocomplete: "off" } }),
        ...["机位1", "角色A"].map((label) => el("button", { text: label, attrs: { type: "button" } })),
      ]),
      el("div", { className: "libtv-director-action-row" }, ["移动 (V)", "添加角色", "全景图", "添加机位"].map((label) =>
        el("button", { text: label, attrs: { type: "button" } }),
      )),
    ]),
    el("aside", { className: "libtv-director-camera-panel" }, [
      el("header", {}, [
        el("strong", { text: "摄像机" }),
        el("span", { text: "属性" }),
        el("em", { text: "摄像机截图" }),
      ]),
      el("button", { className: "libtv-director-reset", text: "重置视角", attrs: { type: "button" } }),
      el("section", {}, [
        el("label", {}, [el("span", { text: "名称" }), el("button", { text: "切换机位 机位1", attrs: { type: "button" } })]),
        el("label", {}, [el("span", { text: "位置 X Y Z" }), el("input", { attrs: { value: "0 0 0", readonly: "readonly" } })]),
        el("label", {}, [el("span", { text: "注视目标" }), el("button", { text: "手动坐标 角色A", attrs: { type: "button" } })]),
        el("label", {}, [el("span", { text: "注视坐标 X Y Z" }), el("input", { attrs: { value: "0 1 0", readonly: "readonly" } })]),
      ]),
      el("div", { className: "libtv-director-fov" }, [
        el("strong", { text: "视野角度 (FOV)" }),
        el("span", { text: "FOV 50°" }),
        el("p", { text: "控制镜头视野范围。数值越小，画面越近、越聚焦；数值越大，画面越广、能看到更多环境。" }),
      ]),
      el("div", { className: "libtv-director-action-row" }, ["相机截图", "选择画幅比例", "截图", "AI 识图导入", "全屏"].map((label) =>
        el("button", { text: label, attrs: { type: "button" } }),
      )),
      el("small", { text: "导演台未启动" }),
    ]),
  ]);
}

function imageParam(label, value) {
  return el("article", {}, [
    el("span", { text: label }),
    el("strong", { text: value }),
  ]);
}

export function renderVideoMergeFlow(attrs) {
  return el("div", { className: "libtv-video-merge-flow", dataset: { canvasContent: "true" }, attrs }, [
    el("article", { className: "libtv-video-merge-preview selected", attrs: { "aria-label": "视频合成预览" } }, [
      el("header", {}, [
        el("span", { className: "node-icon", text: nodeIcon("video_merge") }),
        el("strong", { text: "视频合成" }),
        el("em", { text: "多个视频片段合为一个" }),
      ]),
      el("div", { className: "libtv-video-merge-screen", attrs: { "aria-hidden": "true" } }, [
        el("span", { className: "play-triangle" }),
      ]),
    ]),
    el("section", { className: "libtv-video-merge-timeline" }, ["片段 01", "片段 02", "片段 03"].map((label, index) =>
      el("article", { className: "libtv-video-merge-clip" }, [
        el("span", { text: label }),
        el("small", { text: index === 1 ? "转场" : "安全引用" }),
      ]),
    )),
    el("aside", { className: "libtv-video-merge-control" }, [
      el("strong", { text: "排列需要合成为一条成片的视频片段" }),
      el("div", { className: "libtv-added-node-tabs" }, ["片段排序", "转场", "节奏", "统一画幅"].map((label, index) =>
        el("button", { className: index === 0 ? "active" : "", text: label, attrs: { type: "button" } }),
      )),
      el("p", { text: "生成历史素材仅以安全引用进入时间线。" }),
      el("small", { text: "视频合成未启动" }),
    ]),
  ]);
}
