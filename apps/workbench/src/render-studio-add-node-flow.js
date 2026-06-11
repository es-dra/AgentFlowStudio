import { el } from "./dom.js";
import { renderNodePrompt } from "./render-node-prompt.js";
import { nodeIcon } from "./render-studio-starter-flows.js";
import { renderAudioNodeFlow } from "./render-studio-audio-node-flow.js";
import { renderVideoNodeFlow } from "./render-studio-video-node-flow.js";
import { renderDirectorFlowV3 } from "./render-studio-director-node-flow.js";
import { renderNodeOpenContext } from "./render-studio-node-context.js";
import { renderNodeControlSummary } from "./render-node-control-summary.js";
import { nodeControlButton, nodeControlSelect } from "./studio-node-control-state.js";

export function renderAddNodeFlow(kind, attrs, state = {}) {
  if (kind === "director") return renderDirectorFlowV3(attrs, state);
  if (kind === "video_merge") return renderVideoMergeFlow(attrs, state);
  if (kind === "text") return renderTextNodeFlow(attrs, state);
  if (kind === "image") return renderImageNodeFlow(attrs, state);
  // Static contract marker: if (kind === "video") return renderVideoNodeFlow(attrs);
  if (kind === "video") return renderVideoNodeFlow(attrs, state);
  // Static contract marker: if (kind === "audio") return renderAudioNodeFlow(attrs);
  if (kind === "audio") return renderAudioNodeFlow(attrs, state);
  if (kind === "script") return renderScriptGeneratorFlow(attrs, state);
  return renderTextNodeFlow(attrs, state);
}

export function renderTextNodeFlow(attrs, state = {}) {
  const attempts = ["自己编写内容", "文生视频", "图片反推提示词", "文字生成音乐"];
  return el("div", { className: "libtv-text-node-flow node-flow-shell", dataset: { canvasContent: "true" }, attrs }, [
    renderNodeOpenContext(state, "text"),
    el("article", { className: "libtv-text-node-card selected", attrs: { "aria-label": "文本节点 2" } }, [
      nodeHeader("text", "文本节点 2"),
      previewBars(3, "libtv-text-node-placeholder"),
      renderAttemptGroup(attempts, "libtv-text-attempts", state, "text-attempt"),
    ]),
    el("aside", { className: "libtv-text-generator-control" }, [
      renderNodePrompt(state, {
        placeholder: "写下你想讲的故事、场景或角色设定。例如：一个来自未来的机器人，在城市屋顶看星星。",
        surface: "text",
        primaryAction: "生成文本",
        note: "文本生成未启动",
      }),
      el("div", { className: "libtv-text-model-row" }, [
        el("span", { text: "GVLM 3.1" }),
        el("span", { text: "1" }),
      ]),
    ]),
  ]);
}

export function renderScriptGeneratorFlow(attrs, state = {}) {
  const scriptAttempts = ["剧本生成分镜脚本", "视频参考生成分镜脚本", "角色生成分镜脚本"];
  const textAttempts = ["自己编写内容", "文生视频", "图片反推提示词", "文字生成音乐"];
  return el("div", { className: "libtv-script-generator-flow node-flow-shell", dataset: { canvasContent: "true" }, attrs }, [
    renderNodeOpenContext(state, "script"),
    el("article", { className: "libtv-script-generator-card selected", attrs: { "aria-label": "脚本生成器" } }, [
      nodeHeader("script", "脚本生成器"),
      previewBars(1, "libtv-script-placeholder"),
      renderAttemptGroup(scriptAttempts, "libtv-script-attempts", state, "script-attempt"),
    ]),
    el("aside", { className: "libtv-script-generator-control" }, [
      renderNodePrompt(state, {
        placeholder: "描述剧情或添加角色参考、视频参考等，为你生成分镜脚本。",
        surface: "script",
        primaryAction: "生成分镜脚本",
        note: "脚本生成未启动",
      }),
      el("div", { className: "libtv-script-model-row" }, [
        el("span", { text: "GVLM 3.1" }),
        el("span", { text: "1" }),
      ]),
    ]),
    el("article", { className: "libtv-script-reference-node" }, [
      nodeHeader("text", "文本节点 2"),
      renderAttemptGroup(textAttempts, "libtv-script-attempts", state, "script-reference-attempt"),
    ]),
  ]);
}

export function renderImageNodeFlow(attrs, state = {}) {
  return el("div", { className: "libtv-image-node-flow node-flow-shell", dataset: { canvasContent: "true" }, attrs }, [
    renderNodeOpenContext(state, "image"),
    el("article", { className: "libtv-image-node-card selected", attrs: { "aria-label": "图片节点" } }, [
      el("button", { className: "libtv-image-upload-pill", text: "上传", attrs: { type: "button" } }),
      nodeHeader("image", "图片节点", "5"),
      el("div", { className: "libtv-image-node-preview", attrs: { "aria-hidden": "true" } }, [
        el("span", { text: "IMG" }),
      ]),
      el("div", { className: "libtv-image-tries" }, [
        el("span", { text: "尝试：" }),
        ...["图生图", "图片高清"].map((label, index) =>
          nodeControlButton(label, "image-try", label, state, index === 0 ? label : ""),
        ),
      ]),
    ]),
    el("aside", { className: "libtv-image-control-card" }, [
      el("div", { className: "libtv-image-tool-row" }, ["图生图", "图片高清", "风格", "标记"].map((label, index) =>
        nodeControlButton(label, "image-mode", label, state, index === 0 ? label : ""),
      )),
      renderNodePrompt(state, {
        placeholder: "可直接文字生图，或上传图片输入文字指令对图片进行编辑，如：将背景改为雪夜。",
        surface: "image",
        primaryAction: "生成图片",
        note: "图片生成未启动",
      }),
      renderNodeControlSummary(state, {
        surface: "image",
        title: "图片生成设置",
        modeGroup: "image-mode",
        modeFallback: "图生图",
        items: [
          ["尝试", "image-try", "图生图"],
          ["模式", "image-mode", "图生图"],
          ["模型", "image-model", "Lib Image"],
          ["规格", "image-spec", "标准画质"],
          ["镜头", "image-shot", "摄像机"],
          ["数量", "image-count", "1 张"],
        ],
      }),
      el("div", { className: "libtv-image-param-grid" }, [
        nodeControlSelect("模型", "image-model", ["Lib Image", "Lib Character", "Lib Style"], state, "Lib Image"),
        nodeControlSelect("规格", "image-spec", ["自适应", "标准画质", "2K"], state, "标准画质"),
        nodeControlSelect("镜头", "image-shot", ["摄像机", "全景", "中景"], state, "摄像机"),
        nodeControlSelect("数量", "image-count", ["1 张", "2 张", "4 张"], state, "1 张"),
      ]),
    ]),
  ]);
}

export function renderDirectorFlowV2(attrs) {
  return el("div", { className: "libtv-director-flow", dataset: { canvasContent: "true" }, attrs }, [
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
        el("span", { className: "libtv-director-camera", text: "Camera A" }),
        el("span", { className: "libtv-director-role", text: "角色 A" }),
        el("span", { className: "libtv-director-light key-light", text: "Key Light" }),
        el("span", { className: "libtv-director-light fill-light", text: "Fill Light" }),
        el("span", { className: "libtv-director-light back-light", text: "Back Light" }),
        el("span", { className: "libtv-director-light practical-light", text: "Practical Light" }),
      ]),
      el("div", { className: "libtv-director-object-list" }, [
        el("input", { attrs: { placeholder: "搜索场景对象", autocomplete: "off" } }),
        ...["Camera A", "角色 A", "Key Light", "Fill Light", "Back Light", "Practical Light"].map((label) =>
          el("button", { text: label, attrs: { type: "button" } }),
        ),
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
        labelRow("名称", "切换机位 Camera A"),
        labelInput("位置 X Y Z", "0 0 0"),
        labelRow("注视目标", "手动坐标 角色 A"),
        labelInput("注视坐标 X Y Z", "0 1 0"),
      ]),
      el("div", { className: "libtv-director-fov" }, [
        el("strong", { text: "视野角度 (FOV)" }),
        el("span", { text: "FOV 50°" }),
        el("p", { text: "控制镜头视野范围。数值越小，画面越近、越聚焦；数值越大，画面越广。" }),
      ]),
      el("div", { className: "libtv-director-action-row" }, ["相机截图", "选择画幅比例", "截图", "AI 识图导入", "全屏"].map((label) =>
        el("button", { text: label, attrs: { type: "button" } }),
      )),
      el("div", { className: "libtv-director-action-row output-row" }, [
        "保存为场景资产",
        "生成专业提示词片段",
        "应用到当前镜头",
        "生成导演台布光图",
      ].map((label) => el("button", { text: label, attrs: { type: "button" } }))),
      el("small", { text: "导演台本地预览" }),
    ]),
  ]);
}

export function renderDirectorFlow(attrs) {
  return el("div", { className: "libtv-director-flow", dataset: { canvasContent: "true" }, attrs }, [
    el("section", { className: "libtv-director-canvas" }, [
      el("header", { className: "libtv-director-toolbar" }, [
        el("strong", { text: "导演台" }),
        ...["导演视角", "机位视角", "场景"].map((label, index) =>
          el("button", { className: index === 0 ? "active" : "", text: label, attrs: { type: "button" } }),
        ),
      ]),
      el("div", { className: "libtv-director-stage" }, [
        el("div", { className: "libtv-director-grid", attrs: { "aria-hidden": "true" } }),
        el("span", { className: "libtv-director-camera", text: "Camera A" }),
        el("span", { className: "libtv-director-role", text: "角色 A" }),
      ]),
      el("div", { className: "libtv-director-object-list" }, [
        el("input", { attrs: { placeholder: "搜索场景对象", autocomplete: "off" } }),
        ...["Camera A", "角色 A", "Key Light", "Fill Light"].map((label) => el("button", { text: label, attrs: { type: "button" } })),
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
        labelRow("名称", "切换机位 Camera A"),
        labelInput("位置 X Y Z", "0 0 0"),
        labelRow("注视目标", "手动坐标 角色 A"),
        labelInput("注视坐标 X Y Z", "0 1 0"),
      ]),
      el("div", { className: "libtv-director-fov" }, [
        el("strong", { text: "视野角度 (FOV)" }),
        el("span", { text: "FOV 50°" }),
        el("p", { text: "控制镜头视野范围。数值越小，画面越近、越聚焦；数值越大，画面越广。" }),
      ]),
      el("div", { className: "libtv-director-action-row" }, ["相机截图", "选择画幅比例", "截图", "AI 识图导入", "全屏"].map((label) =>
        el("button", { text: label, attrs: { type: "button" } }),
      )),
      el("small", { text: "导演台未启动" }),
    ]),
  ]);
}

export function renderVideoMergeFlow(attrs, state = {}) {
  return el("div", { className: "libtv-video-merge-flow node-flow-shell", dataset: { canvasContent: "true" }, attrs }, [
    renderNodeOpenContext(state, "video_merge"),
    el("article", { className: "libtv-video-merge-preview selected", attrs: { "aria-label": "视频合成预览" } }, [
      nodeHeader("video_merge", "视频合成", "多个视频片段合成为一个"),
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
      el("strong", { text: "请连接视频节点后操作" }),
      el("div", { className: "libtv-added-node-tabs" }, ["片段排序", "转场", "节奏", "统一画幅"].map((label, index) =>
        el("button", { className: index === 0 ? "active" : "", text: label, attrs: { type: "button" } }),
      )),
      el("p", { text: "生成历史素材会以安全引用进入时间线。" }),
      el("small", { text: "视频合成未启动" }),
    ]),
  ]);
}

function nodeHeader(kind, title, meta = "") {
  return el("header", {}, [
    el("span", { className: "node-icon", text: nodeIcon(kind) }),
    el("strong", { text: title }),
    meta ? el("em", { text: meta }) : null,
  ]);
}

function previewBars(count, className) {
  return el("div", { className, attrs: { "aria-hidden": "true" } },
    Array.from({ length: count }, () => el("span", { className: "preview-bars" })),
  );
}

function renderAttemptGroup(items, className = "libtv-script-attempts", state = {}, group = "node-attempt") {
  return el("div", { className }, [
    el("span", { text: "尝试：" }),
    ...items.map((label, index) => nodeControlButton(label, group, label, state, index === 0 ? label : "")),
  ]);
}

function labelRow(label, value) {
  return el("label", {}, [
    el("span", { text: label }),
    el("button", { text: value, attrs: { type: "button" } }),
  ]);
}

function labelInput(label, value) {
  return el("label", {}, [
    el("span", { text: label }),
    el("input", { attrs: { value, readonly: "readonly" } }),
  ]);
}
