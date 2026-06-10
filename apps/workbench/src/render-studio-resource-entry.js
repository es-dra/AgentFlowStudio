import { el } from "./dom.js";
import { displayStatus, displayText } from "./display-labels.js";

const EMPTY_HISTORY_LABELS = ["图片历史(0)", "视频历史(0)", "音频历史(0)"];

export function renderResourceEntryPanel(mode, workspace) {
  const activeMode = mode === "history" ? "history" : "upload";
  return el("div", { className: `libtv-floating libtv-resource-entry-panel ${modeClass(activeMode)}` }, [
    renderResourceHeader(activeMode),
    activeMode === "history" ? renderHistoryResourcePicker(workspace) : renderUploadResourcePanel(),
  ]);
}

function renderResourceHeader(activeMode) {
  return el("header", { className: "libtv-resource-header" }, [
    el("div", {}, [
      el("h2", { text: "添加资源" }),
      el("span", { text: "素材只进入安全摘要和画布引用，不触发真实 provider 或上传。" }),
    ]),
    el("div", { className: "libtv-resource-tabs" }, [
      resourceTab("upload", "上传素材", activeMode),
      resourceTab("history", "从生成历史选择", activeMode),
      el("button", { text: "取消", dataset: { studioTool: "resource" }, attrs: { type: "button" } }),
    ]),
  ]);
}

function resourceTab(kind, label, activeMode) {
  return el("button", {
    className: activeMode === kind ? "active" : "",
    text: label,
    dataset: { addResourceKind: kind },
    attrs: { type: "button" },
  });
}

function renderUploadResourcePanel() {
  const kinds = [
    ["图片", "分镜、海报、角色参考"],
    ["视频", "样片、片段、首尾帧参考"],
    ["音频", "旁白、配乐、音效方向"],
    ["文本", "脚本、品牌语气、审核备注"],
  ];
  return el("section", { className: "libtv-upload-resource-panel" }, [
    el("div", { className: "libtv-upload-dropzone" }, [
      el("span", { text: "⇧" }),
      el("strong", { text: "拖放文件或选择安全摘要" }),
      el("p", { text: "只登记素材摘要，不读取本地文件字节。" }),
      el("button", { text: "选择摘要", attrs: { type: "button" } }),
    ]),
    el("div", { className: "libtv-resource-kind-grid" }, kinds.map(([title, summary]) =>
      el("article", {}, [
        el("strong", { text: title }),
        el("small", { text: summary }),
      ]),
    )),
    renderResourceActionRow("upload"),
  ]);
}

function renderHistoryResourcePicker(workspace) {
  const records = historyResourceRecords(workspace || {});
  const labels = records.length ? [
    `图片历史(${countByKind(records, "image")})`,
    `视频历史(${countByKind(records, "video")})`,
    `音频历史(${countByKind(records, "audio")})`,
  ] : EMPTY_HISTORY_LABELS;
  return el("section", { className: "libtv-history-resource-picker" }, [
    el("div", { className: "libtv-resource-history-head" }, [
      el("strong", { text: "从生成历史选择" }),
      el("span", { text: "100%" }),
    ]),
    el("div", { className: "libtv-resource-tabs" }, [
      el("button", { className: "active", text: labels[0], attrs: { type: "button" } }),
      el("button", { text: labels[1], attrs: { type: "button" } }),
      el("button", { text: labels[2], attrs: { type: "button" } }),
    ]),
    el("div", { className: "libtv-resource-history-actions" }, ["时间降序", "批量操作", "仅看可复用"].map((label) =>
      el("button", { text: label, attrs: { type: "button" } }),
    )),
    records.length ? el("div", { className: "libtv-resource-history-grid" }, records.map(renderHistoryResourceCard)) : renderResourceEmpty("暂无历史记录"),
    renderResourceActionRow("history"),
  ]);
}

function renderResourceActionRow(kind) {
  return el("footer", { className: "libtv-resource-action-row" }, [
    el("button", { className: "primary", text: "添加到画布", dataset: { addNodeKind: kind === "history" ? "video_merge" : "source" }, attrs: { type: "button" } }),
    el("button", { text: "取消", dataset: { studioTool: "resource" }, attrs: { type: "button" } }),
  ]);
}

function historyResourceRecords(workspace) {
  const filmstrip = Array.isArray(workspace.filmstrip) ? workspace.filmstrip : [];
  const candidates = Array.isArray(workspace.side_rail?.review_candidates) ? workspace.side_rail.review_candidates : [];
  return [
    ...candidates.map((item, index) => ({
      kind: "image",
      title: item.title || `图片候选 ${index + 1}`,
      summary: item.summary || item.status || "待审片候选",
      status: item.status || "ready",
    })),
    ...filmstrip.map((item, index) => ({
      kind: "video",
      title: item.title || `视频分镜 ${index + 1}`,
      summary: item.summary || item.status || "已登记分镜",
      status: item.status || "ready",
    })),
  ];
}

function renderHistoryResourceCard(record) {
  return el("article", { className: `libtv-resource-history-card history-kind-${record.kind}` }, [
    el("span", { text: record.kind === "video" ? "▶" : "▣" }),
    el("strong", { text: displayText(record.title) }),
    el("small", { text: displayText(record.summary) }),
    el("em", { text: displayStatus(record.status) }),
  ]);
}

function renderResourceEmpty(text) {
  return el("div", { className: "libtv-resource-empty" }, [
    el("span", { text: "▧" }),
    el("strong", { text }),
    el("p", { text: "完成一次安全预检或审片后，图片、视频、音频记录会在这里归档。" }),
  ]);
}

function countByKind(records, kind) {
  return records.filter((record) => record.kind === kind).length;
}

function modeClass(mode) {
  return mode === "history" ? "libtv-history-resource-picker" : "libtv-upload-resource-panel";
}
