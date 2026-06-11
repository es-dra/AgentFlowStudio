import { badge, button, el, field, selectField, textareaField } from "./dom.js";
import { renderNodePrompt } from "./render-node-prompt.js";

export function renderScriptStarterFlow(attrs, state = {}) {
  const lastScriptRef = state.lastResult?.artifacts?.script_storyboard_safe_artifact;
  return el("div", { className: "libtv-script-flow script-vertical-flow", dataset: { canvasContent: "true" }, attrs }, [
    el("article", { className: "libtv-script-node selected", attrs: { "aria-label": "剧本输入节点" } }, [
      el("header", {}, [
        el("span", { className: "node-icon", text: nodeIcon("script") }),
        el("strong", { text: "剧本输入" }),
        badge("本地预览", "quiet"),
      ]),
      el("div", { className: "libtv-script-scroll" }, [
        renderNodePrompt(state, {
          id: "script-draft-goal",
          value: state.scriptDraftGoal,
          rows: 6,
          label: "剧本 / 创作目标",
          surface: "script",
          placeholder: "粘贴剧本、剧情梗概或一句创作目标。第一版会先生成可审看的分镜计划。",
          primaryAction: "生成分镜",
          note: "点击下方生成分镜计划后继续。",
        }),
        el("div", { className: "script-vertical-grid" }, [
          field("目标时长", "script-draft-duration", state.scriptDraftDurationSeconds, {
            inputmode: "numeric",
            "data-script-draft-duration": "true",
          }),
          selectField("风格方向", "script-draft-tone", state.scriptDraftTone, [
            { value: "cinematic_storyboard", label: "电影分镜" },
            { value: "commercial_short", label: "广告短片" },
            { value: "character_trailer", label: "角色预告" },
          ]),
        ]),
      ]),
    ]),
    connector("libtv-script-connector"),
    el("div", { className: "libtv-edit-tip", text: "AI 会先整理出可审看的分镜计划" }),
    el("article", { className: "libtv-script-target", attrs: { "aria-label": "分镜脚本节点" } }, [
      el("header", {}, [
        el("span", { className: "node-icon", text: nodeIcon("scene") }),
        el("strong", { text: "分镜脚本" }),
      ]),
      el("div", { className: "script-vertical-result" }, [
        el("span", { className: "preview-bars", attrs: { "aria-hidden": "true" } }),
        el("p", { text: lastScriptRef ? "已生成可审看的分镜脚本。" : "等待生成分镜脚本。" }),
        lastScriptRef ? button("打开分镜 artifact", "open-artifact-ref", "ghost", { artifactId: lastScriptRef.artifact_id }) : null,
      ]),
    ]),
    el("aside", { className: "libtv-script-control-card" }, [
      el("span", { className: "node-icon", text: nodeIcon("script") }),
      el("strong", { text: "从剧本生成分镜" }),
      el("div", { className: "libtv-script-control-row" }, [
        button("生成分镜计划", "run-script-draft-plan", "primary"),
        lastScriptRef ? badge("已有分镜", "ready") : badge("待生成", "quiet"),
        el("small", { text: "当前先返回本地分镜计划。" }),
      ]),
      textareaField("审片反馈", "script-draft-feedback-note", state.scriptDraftFeedbackNote, {
        rows: "3",
        "data-script-draft-feedback-note": "true",
        placeholder: "补充你想修改的镜头、节奏或角色一致性要求。",
      }),
      field("上一版分镜", "script-draft-previous-artifact-id", state.scriptDraftPreviousArtifactId, {
        "data-script-draft-previous-artifact-id": "true",
        placeholder: "可选 artifact id",
      }),
      field("反馈来源", "script-draft-review-feedback-artifact-id", state.scriptDraftReviewFeedbackArtifactId, {
        "data-script-draft-review-feedback-artifact-id": "true",
        placeholder: "可选反馈 artifact id",
      }),
    ]),
  ]);
}

export function renderCharacterStarterFlow(attrs, state = {}) {
  return el("div", { className: "libtv-character-flow", dataset: { canvasContent: "true" }, attrs }, [
    renderCharacterToolbar(),
    el("article", { className: "libtv-character-source selected", attrs: { "aria-label": "角色参考节点" } }, [
      nodeHeader("character", "角色参考"),
      el("div", { className: "libtv-character-portrait", attrs: { "aria-hidden": "true" } }, [
        el("span", { className: "portrait-head" }),
        el("span", { className: "portrait-body" }),
      ]),
      el("button", { className: "libtv-character-upload", text: "上传参考", attrs: { type: "button" } }),
    ]),
    connector("libtv-character-connector"),
    el("div", { className: "libtv-character-replace-tip", text: "可替换参考图或继续描述角色" }),
    el("article", { className: "libtv-character-result", attrs: { "aria-label": "角色三视图节点" } }, [
      nodeHeader("character", "角色三视图"),
      el("div", { className: "libtv-three-view-grid" }, ["正面", "侧面", "背面"].map((label) =>
        el("figure", { className: "libtv-three-view-card" }, [
          el("span", { className: "view-silhouette", attrs: { "aria-hidden": "true" } }),
          el("figcaption", { text: label }),
        ]),
      )),
      el("footer", {}, [
        el("span", { text: "一致性约束" }),
        el("small", { text: "未生成" }),
      ]),
    ]),
    el("aside", { className: "libtv-character-status" }, [
      el("strong", { text: "角色设定" }),
      renderNodePrompt(state, {
        placeholder: "描述角色年龄、服装、表情、三视图要保持的一致性。",
        surface: "character",
        primaryAction: "生成三视图",
        note: "角色生成未启动",
      }),
      el("span", { text: "当前展示占位结构，后续接入真实图片生成。" }),
    ]),
  ]);
}

export function renderImageVideoStarterFlow(attrs, state = {}) {
  return el("div", { className: "libtv-image-video-flow", dataset: { canvasContent: "true" }, attrs }, [
    el("article", { className: "libtv-first-frame-source selected", attrs: { "aria-label": "首帧图片节点" } }, [
      nodeHeader("image", "首帧"),
      el("div", { className: "libtv-first-frame-preview", attrs: { "aria-hidden": "true" } }, [
        el("span", { className: "frame-sun" }),
        el("span", { className: "frame-ridge" }),
      ]),
      el("button", { className: "libtv-frame-upload", text: "上传参考", attrs: { type: "button" } }),
    ]),
    connector("libtv-video-connector"),
    el("div", { className: "libtv-video-replace-tip", text: "可替换首帧或引用素材" }),
    el("article", { className: "libtv-video-result", attrs: { "aria-label": "视频节点" } }, [
      nodeHeader("video", "视频"),
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
      renderNodePrompt(state, {
        placeholder: "描述你想要生成的画面内容，@引用素材",
        surface: "image-video",
        primaryAction: "生成视频",
        note: "视频生成未启动",
      }),
      el("div", { className: "libtv-video-param-row" }, [
        el("button", { text: "Seedance 2.0 VIP", attrs: { type: "button" } }),
        el("button", { text: "16:9 / 720P / 5s", attrs: { type: "button" } }),
        el("small", { text: "视频生成未启动" }),
      ]),
    ]),
  ]);
}

export function renderAudioVideoStarterFlow(attrs, state = {}) {
  return el("div", { className: "libtv-audio-video-flow", dataset: { canvasContent: "true" }, attrs }, [
    el("article", { className: "libtv-audio-source selected", attrs: { "aria-label": "音频节点" } }, [
      nodeHeader("audio", "音频"),
      el("div", { className: "libtv-audio-waveform", attrs: { "aria-hidden": "true" } },
        [24, 38, 52, 34, 64, 46, 28, 58, 42, 70, 36, 54].map((height) =>
          el("span", { attrs: { style: `height:${height}px` } }),
        ),
      ),
      el("div", { className: "libtv-audio-timeline" }, [
        el("span", { text: "00:00 / 00:03" }),
        el("span", { text: "00:00 / 00:03" }),
      ]),
      el("button", { className: "libtv-audio-upload", text: "选择音频", attrs: { type: "button" } }),
    ]),
    connector("libtv-audio-connector"),
    el("div", { className: "libtv-audio-replace-tip", text: "可替换音频或继续描述" }),
    el("article", { className: "libtv-audio-video-result", attrs: { "aria-label": "音频生成视频节点" } }, [
      nodeHeader("video", "视频"),
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
      renderNodePrompt(state, {
        placeholder: "描述音频对应的画面、节奏、音乐情绪和镜头语言。",
        surface: "audio-video",
        primaryAction: "生成视频",
        note: "音频驱动未启动",
      }),
    ]),
  ]);
}

export function renderStarterNodes(attrs, selectedKind = "") {
  const starters = [
    ["script", "剧本生成分镜", "从剧本生成镜头脚本"],
    ["character", "角色三视图", "确定角色正面、侧面、背面"],
    ["image", "首帧图生视频", "从关键帧生成 5s 视频"],
    ["audio", "音频生视频", "根据音频节奏生成视频"],
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
      el("em", { text: "进入" }),
    ]),
  ));
}

function nodeHeader(kind, title) {
  return el("header", {}, [
    el("span", { className: "node-icon", text: nodeIcon(kind) }),
    el("strong", { text: title }),
  ]);
}

function connector(className) {
  return el("div", { className, attrs: { "aria-hidden": "true" } }, [
    el("span", { className: "connector-dot" }),
    el("span", { className: "connector-line" }),
  ]);
}

function renderCharacterToolbar() {
  const tools = [["全身", "NEW"], ["换装", ""], ["表情", ""], ["姿态", ""], ["风格", ""], ["细节", ""]];
  return el("nav", { className: "libtv-character-toolbar", attrs: { "aria-label": "角色工具" } }, tools.map(([label, tag]) =>
    el("button", { attrs: { type: "button" } }, [
      el("span", { text: label }),
      tag ? el("em", { text: tag }) : null,
    ]),
  ));
}

export function nodeIcon(kind) {
  const icons = {
    brief: "TXT",
    source: "SRC",
    script: "SCR",
    character: "CHR",
    scene: "SCN",
    review: "REV",
    memory: "MEM",
    image: "IMG",
    video: "VID",
    audio: "AUD",
    director: "DIR",
    text: "TXT",
    video_merge: "CUT",
  };
  return icons[kind] || "AFS";
}
