import { el } from "./dom.js";
import { displayStatus, displayText } from "./display-labels.js";

export function renderHistoryPanel(workspace) {
  const records = historyRecords(workspace || {});
  const counts = countByKind(records);
  return el("div", { className: "libtv-floating libtv-history-panel libtv-history-modal" }, [
    el("header", { className: "libtv-history-head" }, [
      el("div", {}, [
        el("h2", { text: "历史资产" }),
        el("span", { text: `${records.length} 条可复用记录` }),
      ]),
      renderHistoryZoom(),
    ]),
    el("div", { className: "libtv-history-tabs" }, [
      historyTab("图片历史", counts.image, true),
      historyTab("视频历史", counts.video, false),
      historyTab("音频历史", counts.audio, false),
    ]),
    el("div", { className: "libtv-history-actions" }, [
      el("button", { text: "创建时间倒序", attrs: { type: "button" } }),
      el("button", { text: "批量选择", attrs: { type: "button" } }),
      el("button", { text: "仅看可复用", attrs: { type: "button" } }),
    ]),
    records.length
      ? el("div", { className: "libtv-history-grid" }, records.map(renderHistoryCard))
      : renderHistoryEmpty(),
  ]);
}

function renderHistoryZoom() {
  return el("div", { className: "libtv-history-zoom" }, [
    el("button", { text: "-", attrs: { type: "button", "aria-label": "缩小历史视图" } }),
    el("span", { text: "100%" }),
    el("button", { text: "+", attrs: { type: "button", "aria-label": "放大历史视图" } }),
    el("button", { className: "libtv-history-close", text: "×", dataset: { studioTool: "history" }, attrs: { type: "button", "aria-label": "关闭历史资产" } }),
  ]);
}

function historyTab(label, count, active) {
  return el("button", {
    className: active ? "active" : "",
    text: `${label}(${count})`,
    attrs: { type: "button" },
  });
}

function historyRecords(workspace) {
  const filmstrip = Array.isArray(workspace.filmstrip) ? workspace.filmstrip : [];
  const candidates = Array.isArray(workspace.side_rail?.review_candidates) ? workspace.side_rail.review_candidates : [];
  return [
    ...candidates.map((item, index) => ({
      kind: "image",
      title: item.title || `图片候选 ${index + 1}`,
      summary: item.summary || item.status || "待审片候选",
      status: item.status,
      artifactId: item.artifact_id,
      candidateId: item.candidate_id,
    })),
    ...filmstrip.map((item, index) => ({
      kind: "video",
      title: item.title || `视频分镜 ${index + 1}`,
      summary: item.summary || item.status || "已登记分镜",
      status: item.status,
      artifactId: item.artifact_id || item.primary_artifact_id,
    })),
  ];
}

function countByKind(records) {
  return records.reduce((counts, record) => {
    counts[record.kind] = (counts[record.kind] || 0) + 1;
    return counts;
  }, { image: 0, video: 0, audio: 0 });
}

function renderHistoryCard(record) {
  return el("article", {
    className: `libtv-history-card history-kind-${record.kind}`,
    dataset: { artifactId: record.artifactId || "", variantId: record.candidateId || "" },
  }, [
    el("div", { className: "libtv-history-thumb" }, [
      el("span", { text: historyIcon(record.kind) }),
    ]),
    el("div", { className: "libtv-history-card-body" }, [
      el("strong", { text: displayText(record.title) }),
      el("small", { text: displayText(record.summary) }),
      el("em", { text: displayStatus(record.status || "ready") }),
    ]),
  ]);
}

function renderHistoryEmpty() {
  return el("div", { className: "libtv-history-empty" }, [
    el("span", { text: "▧" }),
    el("strong", { text: "暂无历史资产" }),
    el("p", { text: "完成一次安全预检或审片后，图片、视频、音频记录会在这里按类型归档。" }),
  ]);
}

function historyIcon(kind) {
  return { image: "▣", video: "▶", audio: "♪" }[kind] || "▧";
}
