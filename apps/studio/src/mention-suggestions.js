import { assetReferenceCandidates } from "./asset-reference-candidates.js";
import { el, showPopover } from "./overlay.js";

const MENTION_QUERY_RE = /@([A-Za-z0-9_\-\u4e00-\u9fff·]*)$/u;

export function bindAssetMentionSuggestions(textarea, store, nodeId) {
  let close = null;

  const closeMenu = () => {
    if (close) close();
    close = null;
  };

  const refresh = () => {
    const match = mentionQuery(textarea);
    if (!match) {
      closeMenu();
      return;
    }
    const candidates = assetReferenceCandidates(store.get(), nodeId, match.query);
    if (!candidates.length) {
      closeMenu();
      return;
    }
    closeMenu();
    const pop = el("div", "mention-popover");
    pop.appendChild(el("div", "mention-title", "引用资产"));
    for (const candidate of candidates) {
      const item = el("button", "mention-item");
      item.innerHTML = [
        `<strong>@${escapeHtml(candidate.label)}</strong>`,
        `<small>${escapeHtml(scopeLabel(candidate.scope))} · ${escapeHtml(typeLabel(candidate.asset_type))}</small>`,
      ].join("");
      item.addEventListener("pointerdown", (event) => {
        event.preventDefault();
        applyMention(textarea, match, candidate.label);
        textarea.dispatchEvent(new Event("input", { bubbles: true }));
        closeMenu();
      });
      pop.appendChild(item);
    }
    close = showPopover(textarea, pop, { place: "top", closeOnOutside: true });
  };

  textarea.addEventListener("input", refresh);
  textarea.addEventListener("keyup", refresh);
  textarea.addEventListener("blur", () => setTimeout(closeMenu, 120));
}

function mentionQuery(textarea) {
  const end = textarea.selectionStart ?? textarea.value.length;
  const prefix = textarea.value.slice(0, end);
  const match = prefix.match(MENTION_QUERY_RE);
  if (!match) return null;
  return { start: end - match[0].length, end, query: match[1] || "" };
}

function applyMention(textarea, match, label) {
  const token = String.fromCharCode(64) + label;
  textarea.value = textarea.value.slice(0, match.start) + token + textarea.value.slice(match.end);
  const pos = match.start + token.length;
  textarea.setSelectionRange(pos, pos);
  textarea.focus();
}

function scopeLabel(scope) {
  return scope === "project_fixed" ? "项目固定" : "同树候选";
}

function typeLabel(type) {
  if (type === "scene") return "场景";
  if (type === "prop") return "道具";
  return "角色";
}

function escapeHtml(value) {
  return String(value || "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[ch]));
}
