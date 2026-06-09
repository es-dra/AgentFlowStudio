import { badge, button, el, sectionTitle, textareaField } from "./dom.js";
import { displayStatus, displayText } from "./display-labels.js";

export function renderStudioInspector(inspector, state) {
  const fields = inspector.fields || {};
  return el("aside", { className: "studio-inspector" }, [
    sectionTitle("节点检查器", displayStatus(inspector.status || "empty", "空")),
    el("h3", { text: displayText(inspector.title || "未选择卡片") }),
    inspector.summary ? el("p", { className: "card-summary", text: displayText(inspector.summary) }) : null,
    renderInspectorFacts(inspector),
    renderRefs(inspector.refs || []),
    inspector.primary_artifact_id ? button("打开产物", "open-artifact-ref", "secondary", { artifactId: inspector.primary_artifact_id }) : null,
    inspector.mode === "scene"
      ? el("div", { className: "inspector-editor" }, [
          textareaField("提示词", "inspector-prompt", displayText(fields.prompt || state.inspectorPrompt), { rows: "4" }),
          textareaField("参考摘要", "inspector-reference-summary", displayText(fields.reference_summary || state.inspectorReferenceSummary), { rows: "3" }),
          textareaField("风格方向", "inspector-style-direction", displayText(fields.style_direction || state.inspectorStyleDirection), { rows: "3" }),
          textareaField("重试意图", "inspector-retry-intent", displayText(fields.retry_intent || state.inspectorRetryIntent), { rows: "3" }),
          button("保存检查器", "update-scene-inspector", "primary"),
        ])
      : null,
  ]);
}

function renderInspectorFacts(inspector) {
  const actions = Array.isArray(inspector.actions) ? inspector.actions : [];
  const blockers = Array.isArray(inspector.blockers) ? inspector.blockers : [];
  return el("div", { className: "studio-inspector-facts" }, [
    badge(`${actions.length} 个动作`, actions.length ? "ready" : "quiet"),
    badge(`${blockers.length} 个阻塞`, blockers.length ? "blocked" : "quiet"),
    actions.length ? el("div", { className: "chips" }, actions.map((item) => badge(displayText(item), "active"))) : null,
    blockers.length ? el("div", { className: "chips" }, blockers.map((item) => badge(displayText(item.message || item.blocker_id), "blocked"))) : null,
  ]);
}

function renderRefs(refs) {
  if (!refs.length) return el("p", { className: "muted", text: "没有安全预览引用。" });
  return el("div", { className: "ref-list" }, refs.map((ref) =>
    el("div", { className: "ref-row" }, [
      el("span", { text: displayText(ref.label) }),
      el("code", { text: displayText(ref.artifact_type || "artifact") }),
      badge(ref.artifact_id ? "安全引用" : "待生成", ref.artifact_id ? "quiet" : "blocked"),
    ]),
  ));
}
