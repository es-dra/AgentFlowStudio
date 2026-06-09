import { badge, button, el, sectionTitle } from "./dom.js";
import { displayList, displayStatus, displayText } from "./display-labels.js";

export function renderStyleMemoryWorkspace(styleMemory, memoryWorkspace) {
  const profile = styleMemory || memoryWorkspace?.style_profile || { reusable_preferences: [], non_claims: [] };
  const memory = memoryWorkspace || { counts: {}, latest_decisions: [], next_round_controls: {}, non_claims: [] };
  return el("section", { className: "style-memory-workspace" }, [
    renderProfileHero(profile, memory.counts || {}),
    renderPreferenceBoard(profile),
    renderNextRoundPanel(profile, memory.next_round_controls || {}),
    renderEvidenceLedger(memory.latest_decisions || []),
    renderBoundary(profile, memory),
  ]);
}

function renderProfileHero(profile, counts) {
  return el("div", { className: "style-memory-hero" }, [
    sectionTitle("项目记忆", displayStatus(profile.status)),
    el("p", { className: "card-summary", text: displayText(profile.summary, "审片反馈会在这里沉淀为下一轮可复用偏好。") }),
    el("div", { className: "style-memory-metrics" }, [
      badge(`${profile.profile_version_count || counts.profile_versions || 0} 个版本`, (profile.profile_version_count || counts.profile_versions) ? "good" : "quiet"),
      badge(`${profile.feedback_count || counts.feedback_refs || 0} 条反馈`, (profile.feedback_count || counts.feedback_refs) ? "active" : "quiet"),
      badge(`${counts.reusable_preferences || profile.reusable_preferences?.length || 0} 条偏好`, (counts.reusable_preferences || profile.reusable_preferences?.length) ? "ready" : "quiet"),
    ]),
    profile.latest_profile_artifact_id ? button("打开记忆档案", "open-artifact-ref", "secondary", { artifactId: profile.latest_profile_artifact_id }) : null,
  ]);
}

function renderPreferenceBoard(profile) {
  const preferences = Array.isArray(profile.reusable_preferences) ? profile.reusable_preferences : [];
  return el("div", { className: "style-preference-board" }, [
    sectionTitle("可复用偏好", `${preferences.length}`),
    preferences.length
      ? el("div", { className: "style-preference-list" }, preferences.map((item, index) => renderPreference(item, index)))
      : el("p", { className: "muted", text: "记录审片反馈后，这里会出现可复用的风格偏好。" }),
  ]);
}

function renderPreference(item, index) {
  return el("article", { className: "style-preference-card" }, [
    badge(String(index + 1).padStart(2, "0"), "quiet"),
    el("p", { text: displayText(item) }),
  ]);
}

function renderNextRoundPanel(profile, controls) {
  const enabled = controls.enabled && controls.ui_action;
  return el("aside", { className: "style-next-round-panel" }, [
    sectionTitle("下一轮复用", displayText(controls.primary_label, "进入下一轮")),
    el("p", { className: "card-summary", text: displayText(profile.next_pass_usage || controls.summary, "先完成审片，再准备下一轮复用。") }),
    controls.requires_input?.length ? el("div", { className: "chips" }, displayList(controls.requires_input).map((item) => badge(item, "quiet"))) : null,
    enabled
      ? button(displayText(controls.primary_label, "进入下一轮"), controls.ui_action, "primary")
      : el("button", { className: "btn ghost disabled", text: "等待审片证据", attrs: { disabled: "disabled" } }),
    controls.blocked_reason ? badge(displayText(controls.blocked_reason), "blocked") : null,
  ]);
}

function renderEvidenceLedger(decisions) {
  return el("div", { className: "style-evidence-ledger" }, [
    sectionTitle("记忆证据", `${decisions.length}`),
    decisions.length
      ? el("div", { className: "style-evidence-list" }, decisions.map(renderDecision))
      : el("p", { className: "muted", text: "当前还没有可用于项目记忆的审片记录。" }),
  ]);
}

function renderDecision(decision) {
  return el("div", { className: "style-evidence-row" }, [
    badge(displayText(decision.decision || "unknown"), decision.decision === "reject" ? "blocked" : "good"),
    el("span", { text: displayText(decision.note || "无说明") }),
    decision.generated_at ? el("small", { text: decision.generated_at }) : null,
  ]);
}

function renderBoundary(profile, memory) {
  const claims = [...(profile.non_claims || []), ...(memory.non_claims || [])];
  return claims.length ? el("div", { className: "chips" }, displayList([...new Set(claims)]).map((item) => badge(item, "quiet"))) : null;
}
