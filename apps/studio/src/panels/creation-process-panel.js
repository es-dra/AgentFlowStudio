import { icon } from "../icons.js";
import { el, showModal } from "../overlay.js";
import { qualityFeedbackView } from "../quality-feedback.js";

export function openCreationProcessPanel(state, node) {
  if (!node) return null;
  const modal = el("div", "modal compact creation-process-modal");
  const head = el("div", "modal-head creation-process-head");
  head.appendChild(el("strong", "", "创作过程"));
  head.appendChild(el("small", "", workType(node)));
  const closeBtn = el("button", "modal-close");
  closeBtn.innerHTML = icon("x", 15);
  head.appendChild(el("span", "head-spacer"));
  head.appendChild(closeBtn);

  const body = el("div", "modal-body creation-process-body");
  body.appendChild(hero(node));
  body.appendChild(stepList(state, node));
  body.appendChild(detailGrid(node));
  const feedback = qualityFeedbackView(node);
  if (feedback) body.appendChild(reviewSection(feedback));

  modal.append(head, body);
  const close = showModal(modal);
  closeBtn.addEventListener("click", close);
  return close;
}

function hero(node) {
  const wrap = el("section", "creation-process-hero");
  const media = el("div", `creation-process-media ${node.type || "text"}`);
  if (node.previewUrl && node.type === "image") {
    const img = document.createElement("img");
    img.src = node.previewUrl;
    img.alt = "";
    media.appendChild(img);
  } else {
    media.innerHTML = icon(node.type === "video" ? "video" : node.type === "image" ? "image" : "layers", 22);
  }
  const copy = el("div", "creation-process-copy");
  copy.appendChild(el("span", "", "当前作品"));
  copy.appendChild(el("h3", "", node.title || "未命名输出"));
  copy.appendChild(el("p", "", summary(node)));
  wrap.append(media, copy);
  return wrap;
}

function stepList(state, node) {
  const section = el("section", "creation-process-section");
  section.appendChild(el("h4", "", "来源链路"));
  const list = el("div", "creation-process-steps");
  for (const item of lineage(state, node)) {
    const row = el("div", "creation-step");
    row.innerHTML = [
      `<span class="creation-step-icon">${icon(iconName(item.node), 13)}</span>`,
      `<strong>${escapeHtml(item.node.title || item.node.id)}</strong>`,
      `<small>${escapeHtml(item.reason)}</small>`,
    ].join("");
    list.appendChild(row);
  }
  section.appendChild(list);
  return section;
}

function detailGrid(node) {
  const section = el("section", "creation-process-section");
  section.appendChild(el("h4", "", "可继续操作"));
  const grid = el("div", "creation-process-actions");
  grid.appendChild(action(
    node,
    node.status === "partial" ? "Retry failed items" : "继续生成",
    node.status === "partial" ? "保留 partial result，只重试失败项" : "沿用当前结果创建下一步",
    node.status === "partial" ? "retry" : "play",
    "afs:studio-open-generation-panel",
  ));
  grid.appendChild(action(node, "固定为素材", "把稳定结果加入项目素材", "bookmark", "afs:studio-fix-visual-asset"));
  grid.appendChild(action(node, "整理卡片", "整理画面、片段和可复用信息", "frames", "afs:video-asset-card-draft"));
  section.appendChild(grid);
  const note = el("p", "creation-process-note", "这些入口只展示当前可用方向；真实生成仍需在节点中确认。");
  section.appendChild(note);
  return section;
}

function reviewSection(feedback) {
  const section = el("section", "creation-process-section");
  section.appendChild(el("h4", "", "Review feedback"));
  section.appendChild(feedback);
  return section;
}

function action(node, title, text, iconNameValue, eventName) {
  const item = el("button", "creation-action");
  item.type = "button";
  item.innerHTML = `${icon(iconNameValue, 14)}<strong>${escapeHtml(title)}</strong><small>${escapeHtml(text)}</small>`;
  item.addEventListener("click", () => {
    window.dispatchEvent(new CustomEvent(eventName, { detail: { node_id: node.id, node } }));
  });
  return item;
}

function lineage(state, node) {
  const nodes = state?.nodes || {};
  const upstreamIds = Object.values(state?.edges || {})
    .filter((edge) => edge?.to === node.id)
    .map((edge) => edge.from)
    .filter((id) => nodes[id]);
  const rows = upstreamIds.map((id) => ({ node: nodes[id], reason: "引用素材或上游说明" }));
  rows.push({ node, reason: node.previewUrl ? "生成结果与安全预览" : "节点草稿与结果摘要" });
  return rows.slice(-5);
}

function workType(node) {
  if (node.type === "video") return "视频作品";
  if (node.type === "image") return "关键帧作品";
  if (node.type === "script") return "脚本输出";
  return "创作节点";
}

function summary(node) {
  if (node.result) return String(node.result).replace(/\s+/g, " ").slice(0, 120);
  if (node.prompt) return String(node.prompt).replace(/\s+/g, " ").slice(0, 120);
  return "还没有生成摘要。";
}

function iconName(node) {
  if (node.type === "video") return "video";
  if (node.type === "image") return "image";
  if (node.type === "script") return "script";
  if (node.type === "director") return "layers";
  return "text";
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[ch]));
}
