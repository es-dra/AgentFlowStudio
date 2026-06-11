import { badge, button, el, sectionTitle } from "./dom.js";
import { displayStatus, displayText } from "./display-labels.js";

function payloadOf(artifact) {
  return artifact ? artifact.payload ?? artifact.text ?? artifact : null;
}

function artifactTitle(artifact) {
  if (!artifact) return displayText("No artifact loaded");
  return displayText(artifact.artifact_type || artifact.role || "artifact");
}

function artifactMeta(artifact) {
  if (!artifact) return [];
  return [
    artifact.artifact_id ? badge(artifact.artifact_id, "ready") : null,
    artifact.role ? badge(artifact.role, "quiet") : null,
    artifact.media_type ? badge(artifact.media_type, "quiet") : null,
  ].filter(Boolean);
}

function fact(label, value, tone = "quiet") {
  return el("div", { className: "fact-row" }, [el("span", { text: displayText(label) }), badge(displayText(value ?? "unknown"), tone)]);
}

function listItems(title, items, key = "block_id") {
  const rows = Array.isArray(items) && items.length
    ? items.map((item) => el("li", { text: typeof item === "object" ? item[key] || item.reason || item.ref || JSON.stringify(item) : item }))
    : [el("li", { text: "无" })];
  return el("div", { className: "report-section" }, [el("h3", { text: title }), el("ul", {}, rows)]);
}

function projectManifestView(payload) {
  return [
    fact("状态", displayStatus(payload.status), payload.status === "blocked" ? "blocked" : "good"),
    fact("素材", Array.isArray(payload.source_assets) ? payload.source_assets.length : 0, "ready"),
    fact("内容卡片", Array.isArray(payload.content_cards) ? payload.content_cards.length : 0, "ready"),
    fact("运行记录", Array.isArray(payload.runs) ? payload.runs.length : 0, "ready"),
    fact("反馈", Array.isArray(payload.feedback_refs) ? payload.feedback_refs.length : 0, "ready"),
  ];
}

function assetTestView(payload) {
  return [
    fact("运行", displayStatus(payload.run_status || payload.status), payload.blocks?.length ? "blocked" : "good"),
    fact("生成能力调用", payload.provider_calls_started === true ? "已启动" : "未启动", "quiet"),
    fact("长期记忆", payload.writes_long_term_memory === true ? "已写入" : "未写入", "quiet"),
    listItems("阻塞项", payload.blocks || [], "block_id"),
  ];
}

function twoRoundView(payload) {
  return [
    fact("验证", displayStatus(payload.runtime_verification_status || payload.status), "good"),
    fact("评估", payload.improvement_assessment || "unknown", "ready"),
    listItems("已纳入引用", payload.included_refs || [], "ref"),
    listItems("阻塞引用", payload.blocked_refs || [], "ref"),
  ];
}

function feedbackView(payload) {
  const feedback = payload.feedback || {};
  return [
    fact("反馈是否记忆", payload.feedback_is_memory === true ? "是" : "否", "quiet"),
    fact("结果", feedback.result || "unknown", "ready"),
    el("p", { className: "artifact-note", text: feedback.note || "" }),
  ];
}

function reviewDecisionView(payload) {
  return [
    fact("决定", payload.decision || "unknown", payload.decision === "reject" ? "blocked" : "ready"),
    fact("卡片", payload.card_id || "unknown", "quiet"),
    fact("长期记忆", payload.writes_long_term_memory === true ? "已写入" : "未写入", "quiet"),
    el("p", { className: "artifact-note", text: payload.note || "" }),
  ];
}

function providerView(payload) {
  return [
    fact("状态", displayStatus(payload.status || "unknown"), payload.status === "blocked" ? "blocked" : "good"),
    fact("生成能力调用", payload.provider_calls_started === true ? "已启动" : "未启动", "quiet"),
    listItems("生成能力阻塞", payload.blockers || payload.blocks || [], "blocker_id"),
  ];
}

function scriptStoryboardView(payload) {
  const scripts = Array.isArray(payload.scripts) ? payload.scripts : [];
  const storyboard = Array.isArray(payload.storyboard) ? payload.storyboard : [];
  return [
    fact("脚本", scripts.length, "ready"),
    fact("分镜", storyboard.length, "ready"),
    fact("Provider 输出", payload.provider_output === true ? "是" : "否", "quiet"),
    fact("远程调用", payload.remote_provider_calls_started === true ? "已启动" : "未启动", "quiet"),
    listItems("分镜镜头", storyboard.slice(0, 6), "shot_id"),
  ];
}

function reportView(artifact) {
  const payload = payloadOf(artifact);
  if (!payload || typeof payload !== "object") return [];
  const type = artifact.artifact_type || payload.artifact_type || payload.kind || "";
  if (type === "agentflow_project_manifest") return projectManifestView(payload);
  if (type === "agentflow_real_asset_test_report") return assetTestView(payload);
  if (type === "agentflow_two_round_context_runtime_report") return twoRoundView(payload);
  if (type === "agentflow_runtime_feedback_event") return feedbackView(payload);
  if (type === "agentflow_runtime_review_decision") return reviewDecisionView(payload);
  if (type === "agentflow_provider_safe_manifest") return providerView(payload);
  if (type === "agentflow_script_storyboard_safe_artifact") return scriptStoryboardView(payload);
  return [];
}

function artifactBody(artifact) {
  if (!artifact) return el("p", { className: "muted", text: displayText("Select a card with a safe artifact ref.") });
  const payload = payloadOf(artifact);
  const serialized = JSON.stringify(payload, null, 2);
  return el("details", { className: "artifact-details" }, [
    el("summary", { text: "JSON 详情" }),
    el("pre", { className: "artifact-json", text: serialized.slice(0, 6000) }),
  ]);
}

export function renderArtifactPanel(state) {
  return el("section", { className: "artifact-panel" }, [
    sectionTitle("安全产物", artifactTitle(state.artifact)),
    el("div", { className: "chips" }, artifactMeta(state.artifact)),
    el("div", { className: "report-view" }, reportView(state.artifact)),
    artifactBody(state.artifact),
    state.selectedArtifactId ? button(displayText("Reload Artifact"), "open-selected-artifact", "ghost") : null,
  ]);
}
