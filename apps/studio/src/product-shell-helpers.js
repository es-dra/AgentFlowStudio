import { icon } from "./icons.js";

export function clearedProjectSnapshot(snapshot) {
  return {
    ...snapshot,
    project: null,
    sequenceWorkspace: null,
    mediaOperations: null,
    runtimeAssetBible: null,
    imageAdmission: null,
    videoAdmission: null,
    mediaGates: {},
    mediaCommandPreview: null,
    error: "",
  };
}

export function cachedProjectSummary(studioState) {
  const name = String(studioState?.meta?.projectName || "").trim() || "离线项目缓存";
  return {
    project_id: String(studioState?.meta?.projectId || ""),
    name,
    episode: "只读缓存",
    current_stage: "等待重新验证",
    next_action: "重试连接并验证项目身份",
    stages: [],
  };
}

export function statusItem(iconName, label, tone) {
  const item = node("span", `studio-status-item ${tone}`);
  item.innerHTML = `${icon(iconName, 13)}<span>${escapeHtml(label)}</span>`;
  return item;
}

export function emptyScene() {
  return { name: "尚未创建场景", shots: [], duration: "00:00", blocked: false };
}

export function emptyShot() {
  return {
    nodeId: "",
    title: "等待创作简报",
    description: "确认创作简报前不会创建场景或镜头。",
    duration: "0.0s",
    preview: "",
    state: "draft",
  };
}

export function shotTitle(index) {
  return `镜头 ${Number(index || 0) + 1}`;
}

export function splitList(value) {
  return String(value || "")
    .split(/[、,，;\n]+/)
    .map((item) => item.trim())
    .filter(Boolean)
    .slice(0, 24);
}

export function assetCommandLabel(value) {
  return {
    generate_candidates: "建立本地确定性资产候选",
    regenerate_candidates: "重新识别并预览替换",
    create_asset: "补充人工审核资产",
    set_art_direction: "确认统一美术方向",
    approve: "批准资产候选",
    reject: "拒绝资产候选",
    edit: "编辑资产候选",
    merge: "合并资产候选",
    split: "拆分资产候选",
    reassign_occurrences: "重分配必要出现范围",
    mark_not_needed: "标记出现范围为无需",
    lock: "锁定 Asset Bible 版本",
  }[String(value || "")] || "更新 Asset Bible";
}

export function resolutionStatusLabel(value) {
  return {
    approved: "已由批准资产覆盖",
    pending: "等待资产批准",
    rejected: "引用资产已拒绝",
    superseded: "引用资产已取代",
    orphaned: "引用去向缺失",
    not_needed: "已明确无需",
  }[String(value || "")] || "待解决";
}

export function cleanTitle(value) {
  return String(value || "镜头").replace(/[_-]+/g, " ").trim().slice(0, 28) || "镜头";
}

export function cleanDescription(value) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  return text.slice(0, 72) || "等待补充镜头说明";
}

export function formatDuration(value) {
  const seconds = Math.max(0, Number(value || 0));
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds - minutes * 60;
  const secondText = Number.isInteger(remainder) ? String(remainder).padStart(2, "0") : remainder.toFixed(1).padStart(4, "0");
  return `${String(minutes).padStart(2, "0")}:${secondText}`;
}

export function safePreview(value) {
  const text = String(value || "").trim();
  return /^(\/|https?:\/\/)/i.test(text) && !/^file:/i.test(text) ? text : "";
}

export function userLabel(user) {
  return String(user?.display_name || user?.email || "账户").slice(0, 2).toUpperCase();
}

export function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
}

export function node(tag, className = "", text = "") {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== "") element.textContent = String(text);
  return element;
}

export function explicitUrlProjectId() {
  try {
    const params = new URLSearchParams(window.location.search || "");
    return {
      present: params.has("project"),
      value: params.has("project") ? String(params.get("project") || "") : "",
    };
  } catch {
    return { present: false, value: "" };
  }
}

export function projectIdentityMismatch() {
  const error = new Error("Runtime returned a different project identity");
  error.status = 409;
  error.errorCode = "project_identity_mismatch";
  return error;
}
