import { assetTypeLabel, assetLabel, subjectSuffix } from "./asset-reference-summary.js";
import {
  candidateSelectionSummary,
  handleCandidateGridKeydown,
  isCandidateSelectable,
} from "./candidate-selection-controller.js";
import { icon } from "./icons.js";
import { downloadResolvedMedia, openMediaPreviewModal } from "./media-preview-modal.js";
import { candidatePreviewsFromNode } from "./node-candidate-previews.js";
import { setRuntimeMediaSource } from "./runtime-media-source.js";

export function resultView(node) {
  const result = document.createElement("div");
  const candidates = candidatePreviews(node);
  result.className = `node-result${node.previewUrl ? " has-preview" : ""}${candidates.length > 1 ? " has-candidates" : ""}`;
  if (node.type === "image" && node.previewUrl) result.classList.add("full-bleed-image");
  result.dataset.feedbackEvent = "afs:studio-quality-feedback";
  if (node.type === "video") {
    result.classList.add("video-asset-card-draft");
    result.dataset.videoAssetCardDraft = "afs:video-asset-card-draft";
  }
  if (node.previewUrl) {
    const frame = document.createElement("div");
    frame.className = `node-preview-frame ${node.type === "video" ? "video" : "image"}`;
    frame.style.aspectRatio = previewAspectRatio(node);
    if (node.type === "video") {
      const video = document.createElement("video");
      video.className = "node-preview-video";
      setRuntimeMediaSource(video, node.previewUrl);
      video.controls = true;
      video.playsInline = true;
      video.preload = "metadata";
      video.setAttribute("aria-label", "生成的视频预览");
      frame.appendChild(video);
    } else {
      const img = document.createElement("img");
      img.className = "node-preview-img";
      setRuntimeMediaSource(img, node.previewUrl);
      img.alt = "生成的关键帧";
      img.loading = "lazy";
      frame.appendChild(img);
    }
    frame.appendChild(previewOverlay(node));
    frame.addEventListener("dblclick", () => openNodeMediaPreview(node));
    result.appendChild(frame);
    if (["image", "video"].includes(node.type)) result.appendChild(resultActions(node, result));
  }
  if (candidates.length > 1) result.appendChild(candidateSelectionPanel(node, candidates));
  const text = document.createElement("div");
  text.className = "node-result-text";
  text.textContent = node.result;
  result.appendChild(text);
  return result;
}

function previewOverlay(node) {
  const overlay = document.createElement("div");
  overlay.className = "node-preview-overlay";
  overlay.innerHTML = [
    `<span>${icon(node.type === "video" ? "video" : "image", 12)}${node.type === "video" ? "视频预览" : "关键帧预览"}</span>`,
    `<span>${previewAspectRatio(node).replace(" / ", ":")}</span>`,
  ].join("");
  return overlay;
}

function resultActions(node, result) {
  const actions = document.createElement("div");
  actions.className = "media-result-actions";
  const continueButton = document.createElement("button");
  continueButton.className = "mini-btn";
  continueButton.type = "button";
  continueButton.dataset.action = "continue-generate";
  continueButton.title = regenerateActionTitle(node);
  continueButton.innerHTML = node.status === "partial"
    ? `${icon("retry", 12)}<span>Retry failed items</span>`
    : `${icon("play", 12)}<span>${regenerateActionLabel(node)}</span>`;
  actions.appendChild(continueButton);

  const assetButton = document.createElement("button");
  assetButton.className = "mini-btn";
  assetButton.type = "button";
  assetButton.dataset.action = "fix-visual-asset";
  assetButton.innerHTML = `${icon("bookmark", 12)}<span>固定素材</span>`;
  actions.appendChild(assetButton);

  const previewButton = document.createElement("button");
  previewButton.className = "mini-btn";
  previewButton.type = "button";
  previewButton.innerHTML = `${icon("expand", 12)}<span>放大查看</span>`;
  previewButton.addEventListener("click", () => openNodeMediaPreview(node));
  actions.appendChild(previewButton);

  const download = downloadPreviewButton(node);
  actions.appendChild(download);
  if (node.type === "video") {
    const draftButton = document.createElement("button");
    draftButton.className = "mini-btn video-asset-card-draft";
    draftButton.type = "button";
    draftButton.dataset.action = "video-asset-card-draft";
    draftButton.innerHTML = `${icon("frames", 12)}<span>整理视频卡片</span>`;
    draftButton.addEventListener("click", () => {
      result.dispatchEvent(new CustomEvent("afs:video-asset-card-draft", { bubbles: true, detail: { node } }));
    });
    actions.appendChild(draftButton);
  }
  return actions;
}

function regenerateActionLabel(node) {
  if (node.type === "video" && node.params?.videoRevision?.enabled) return "重生成尝试";
  if (node.type === "video") return "重新生成整段";
  return "重新生成整张";
}

function regenerateActionTitle(node) {
  if (node.status === "partial") return "只重试失败项，保留已完成输出。";
  if (node.type === "video" && node.params?.videoRevision?.enabled) {
    return "提交视频重生成尝试；这不是局部编辑，未点名内容也可能变化。";
  }
  if (node.type === "video") return "按当前提示词重新生成整段视频；这不是局部编辑。";
  return "按当前提示词重新生成整张图片；这不是局部编辑。";
}

function candidateSelectionPanel(node, candidates) {
  const selection = candidateSelectionSummary(node);
  const selectedCandidateId = String(selection.selected_candidate_id || "");
  const busy = selection.status === "saving";
  const panel = document.createElement("section");
  panel.className = "candidate-selection-panel";
  panel.setAttribute("aria-label", "创作候选选择与修订");
  panel.setAttribute("aria-busy", busy ? "true" : "false");
  panel.dataset.busy = busy ? "true" : "false";

  const head = document.createElement("div");
  head.className = "candidate-selection-head";
  const title = document.createElement("strong");
  title.textContent = "选择创作候选";
  const refresh = document.createElement("button");
  refresh.className = "candidate-refresh";
  refresh.type = "button";
  refresh.dataset.action = "candidate-refresh";
  refresh.textContent = "刷新已保存选择";
  refresh.disabled = busy;
  head.append(title, refresh);
  panel.appendChild(head);

  panel.appendChild(candidateGrid(candidates, selectedCandidateId, busy));

  const status = document.createElement("p");
  status.className = "candidate-selection-status";
  status.dataset.candidateSelectionStatus = "true";
  status.dataset.state = selection.status || (selectedCandidateId ? "persisted" : "idle");
  status.setAttribute("aria-live", "polite");
  status.textContent = candidateSelectionStatusText(selection, selectedCandidateId);
  panel.appendChild(status);
  const identity = candidateSelectionIdentity(selection);
  if (identity) panel.appendChild(identity);

  const revision = document.createElement("div");
  revision.className = "candidate-revision-control";
  const label = document.createElement("label");
  label.textContent = "修订意图";
  const input = document.createElement("textarea");
  input.rows = 2;
  input.maxLength = 800;
  input.placeholder = "说明希望如何修改当前已选候选";
  input.dataset.candidateRevisionIntent = "true";
  input.disabled = busy;
  input.addEventListener("pointerdown", (event) => event.stopPropagation());
  input.addEventListener("wheel", (event) => event.stopPropagation(), { passive: true });
  label.appendChild(input);
  const revise = document.createElement("button");
  revise.className = "candidate-revise";
  revise.type = "button";
  revise.dataset.action = "candidate-revise";
  revise.dataset.candidateId = selectedCandidateId;
  revise.disabled = busy || !selectedCandidateId;
  revise.textContent = "基于已选候选请求修订";
  revision.append(label, revise);
  panel.appendChild(revision);
  return panel;
}

function candidateGrid(candidates, selectedCandidateId, busy) {
  const grid = document.createElement("div");
  grid.className = "candidate-grid";
  grid.setAttribute("role", "radiogroup");
  grid.setAttribute("aria-label", "生成候选");
  grid.setAttribute("aria-disabled", busy ? "true" : "false");
  grid.addEventListener("keydown", handleCandidateGridKeydown);
  const firstSelectableIndex = candidates.findIndex(isCandidateSelectable);
  candidates.forEach((candidate, index) => {
    const url = candidate.url || candidate.preview_url;
    const status = candidateStatus(candidate, url);
    const selectable = isCandidateSelectable(candidate);
    const selected = selectable && candidate.candidate_id === selectedCandidateId;
    const shell = document.createElement("article");
    shell.className = `candidate-card-shell ${status}${selected ? " selected" : ""}`;

    const item = document.createElement("button");
    item.className = `candidate-card ${status}${selected ? " selected" : ""}`;
    item.type = "button";
    item.setAttribute("role", "radio");
    item.setAttribute("aria-checked", selected ? "true" : "false");
    item.setAttribute("aria-label", candidateTitle(candidate, index + 1, status));
    item.dataset.action = "candidate-select";
    item.dataset.candidateId = candidate.candidate_id || "";
    item.disabled = busy || !selectable;
    item.tabIndex = selected || (!selectedCandidateId && index === firstSelectableIndex) ? 0 : -1;
    if (url) {
      const img = document.createElement("img");
      setRuntimeMediaSource(img, url);
      img.alt = `候选 ${index + 1}`;
      img.loading = "lazy";
      item.appendChild(img);
    } else {
      item.appendChild(candidatePlaceholder(status));
    }
    item.appendChild(candidateBadge(index + 1));
    const stateLabel = document.createElement("span");
    stateLabel.className = "candidate-selected-label";
    stateLabel.textContent = selected ? "已选择" : selectable ? "可选择" : "不可选择";
    item.appendChild(stateLabel);
    shell.appendChild(item);

    if (url) {
      const preview = document.createElement("button");
      preview.className = "candidate-preview-open";
      preview.type = "button";
      preview.setAttribute("aria-label", `放大查看候选 ${index + 1}，不会改变选择`);
      preview.textContent = "放大查看";
      preview.addEventListener("click", () => openMediaPreviewModal({
        url,
        type: "image",
        title: `候选 ${index + 1}`,
        downloadName: `候选-${String(index + 1).padStart(2, "0")}.png`,
      }));
      shell.appendChild(preview);
    }
    grid.appendChild(shell);
  });
  return grid;
}

function candidateSelectionIdentity(selection) {
  if (!selection.selected_candidate_id) return null;
  const summary = document.createElement("dl");
  summary.className = "candidate-selection-identity";
  const fields = [
    ["Candidate", selection.selected_candidate_id],
    ["Revision", selection.selected_revision_id],
    ["Checkpoint", Number.isInteger(selection.checkpoint_version) ? `v${selection.checkpoint_version}` : ""],
    ["Lineage job", selection.selected_parent_job_id],
    ["Parent candidate", selection.selected_parent_candidate_id],
    ["Asset source", selection.selected_asset_id],
  ].filter(([, value]) => String(value || "").trim());
  for (const [label, value] of fields) {
    const term = document.createElement("dt");
    term.textContent = label;
    const detail = document.createElement("dd");
    detail.textContent = compactSafeIdentifier(value);
    detail.title = String(value);
    summary.append(term, detail);
  }
  return summary;
}

function compactSafeIdentifier(value) {
  const text = String(value || "");
  return text.length > 34 ? `${text.slice(0, 18)}…${text.slice(-10)}` : text;
}

function candidateSelectionStatusText(selection, selectedCandidateId) {
  if (selection.message) return String(selection.message);
  if (selectedCandidateId) return `已从生产状态恢复候选 ${selectedCandidateId}`;
  return "尚未选择。放大查看不会改变选择。";
}

function candidatePlaceholder(status) {
  const placeholder = document.createElement("span");
  placeholder.className = "candidate-empty";
  placeholder.textContent = candidateStatusLabel(status);
  return placeholder;
}

function candidateTitle(candidate, index, status) {
  const id = candidate.candidate_id ? ` · ${candidate.candidate_id}` : "";
  const reason = candidate.reason ? ` · ${candidate.reason}` : "";
  return `候选 ${index} · ${candidateStatusLabel(status)}${id}${reason}`;
}

function candidateStatus(candidate, url) {
  const status = String(candidate?.status || candidate?.state || "").trim().toLowerCase();
  if (url && (!status || status === "complete" || status === "succeeded")) return "succeeded";
  if (["complete", "completed", "success", "succeeded"].includes(status)) return "succeeded";
  if (["failed", "failure", "error", "timeout", "timed_out"].includes(status)) return "failed";
  if (["blocked", "needs_attention", "cancelled", "retryable", "partial"].includes(status)) return status;
  return url ? "succeeded" : "needs_attention";
}

function candidateStatusLabel(status) {
  if (status === "succeeded") return "succeeded";
  if (status === "failed") return "failed";
  if (status === "blocked") return "blocked";
  if (status === "retryable") return "retryable";
  if (status === "partial") return "partial";
  if (status === "cancelled") return "cancelled";
  return "needs_attention";
}

function candidateBadge(index) {
  const badge = document.createElement("span");
  badge.className = "candidate-badge";
  badge.textContent = String(index).padStart(2, "0");
  return badge;
}

function candidatePreviews(node) {
  return candidatePreviewsFromNode(node);
}

export function bundleSummary(node) {
  const bundle = node.params?.lastContextBundle;
  if (!bundle) return null;
  const included = Array.isArray(bundle.included_assets) ? bundle.included_assets : [];
  const warnings = Array.isArray(bundle.warnings) ? bundle.warnings : [];
  const overrides = Array.isArray(bundle.temporary_lock_overrides) ? bundle.temporary_lock_overrides : [];

  const box = document.createElement("details");
  box.className = "context-bundle-summary";
  const summary = document.createElement("summary");
  summary.textContent = included.length
    ? `本次携带 ${included.length} 项资产${warnings.length ? ` · ${warnings.length} 条提醒` : ""}`
    : "本次未携带固定资产";
  box.appendChild(summary);

  const detail = document.createElement("div");
  detail.className = "bundle-detail";

  if (included.length) {
    const chips = document.createElement("div");
    chips.className = "bundle-chips";
    for (const item of included) {
      const chip = document.createElement("span");
      chip.className = `bundle-chip ${item.asset_type === "scene" ? "scene" : "character"}`;
      chip.textContent = `${assetTypeLabel(item)} · ${assetLabel(item)}${subjectSuffix(item, bundle)}`;
      chips.appendChild(chip);
    }
    detail.appendChild(chips);
  }

  // 超限降级与同名替代的资产不在 included 里,但用户必须看到它们的真实状态,
  // 否则"凡固定且连线即遵守"的契约出现静默例外。
  const excluded = Array.isArray(bundle.excluded_assets) ? bundle.excluded_assets : [];
  const notable = excluded.filter((item) =>
    item.reason === "degraded_to_signature_over_limit" || item.reason === "superseded_by_newer_label_version");
  if (notable.length) {
    const chips = document.createElement("div");
    chips.className = "bundle-chips";
    for (const item of notable) {
      const chip = document.createElement("span");
      chip.className = "bundle-chip degraded";
      chip.textContent = item.reason === "degraded_to_signature_over_limit"
        ? `${assetLabel(item)} · 超出上限，仅签名参与，锁定未生效`
        : `${assetLabel(item)} · 已被同名新版本替代，本次未携带`;
      chips.appendChild(chip);
    }
    detail.appendChild(chips);
  }

  for (const warning of warnings) {
    const row = document.createElement("div");
    row.className = "bundle-warning";
    row.textContent = humanWarning(warning);
    detail.appendChild(row);
  }

  for (const override of overrides) {
    const row = document.createElement("div");
    row.className = "bundle-override";
    row.textContent = `本次已解除锁定：${override.lock_text}`;
    detail.appendChild(row);
  }

  const budget = bundle.budget;
  if (budget?.enforcement_applied) {
    const truncated = Object.entries(budget.segments || {})
      .filter(([, seg]) => seg?.truncated)
      .map(([name]) => segmentLabel(name));
    if (truncated.length) {
      const row = document.createElement("div");
      row.className = "bundle-budget-note";
      row.textContent = `超出预算已压缩：${truncated.join("、")}（锁定与身份段不受影响）`;
      detail.appendChild(row);
    }
  }

  box.appendChild(detail);
  return box;
}

export function humanWarning(warning) {
  if (warning.warning_id === "best_effort_lock_conflict") {
    const attr = ATTRIBUTE_LABELS[warning.attribute] || warning.attribute || "特征";
    const values = warning.lock_value && warning.prompt_value ? `（${attr}：${warning.lock_value} ↔ ${warning.prompt_value}）` : "";
    return `提示词可能与锁定项冲突：「${warning.lock_text}」${values}，未解除时以锁定为准。`;
  }
  if (warning.warning_id === "named_asset_not_connected") {
    return `提示词提到了「${warning.label || warning.asset_id}」但未连线，本次生成不携带它。`;
  }
  return String(warning.warning_id || "提醒");
}

const ATTRIBUTE_LABELS = {
  hair_color: "发色",
  hair_length: "发长",
  hair_texture: "发型",
  eye_color: "瞳色",
  outfit_color: "服装颜色",
  build: "体态",
  facial_mark: "面部标记",
};

const SEGMENT_LABELS = {
  visible_prompt: "提示词正文",
  lock_identity: "锁定与身份",
  scene_director: "场景与导演",
  upstream_summary: "上游摘要",
  preference: "风格偏好",
};

function segmentLabel(name) {
  return SEGMENT_LABELS[name] || name;
}

function previewAspectRatio(node) {
  const value = String(node.params?.previewAspectRatio || node.params?.spec?.ratio || "9:16");
  return /^\d+:\d+$/.test(value) ? value.replace(":", " / ") : "9 / 16";
}

function downloadPreviewButton(node) {
  const button = document.createElement("button");
  button.className = "mini-btn node-preview-download";
  button.type = "button";
  button.innerHTML = `${icon("archive", 12)}<span>${node.type === "video" ? "下载视频" : "导出原图"}</span>`;
  button.addEventListener("click", () => downloadResolvedMedia(node.previewUrl, previewDownloadName(node), button));
  return button;
}

function previewDownloadName(node) {
  const fallback = node.type === "video" ? "afs-video" : "afs-image";
  const base = String(node.title || node.id || fallback)
    .replace(/[\\/:*?"<>|]+/g, "-")
    .trim()
    .slice(0, 80) || fallback;
  return `${base}.${node.type === "video" ? "mp4" : "png"}`;
}

function openNodeMediaPreview(node) {
  openMediaPreviewModal({
    url: node.previewUrl,
    type: node.type === "video" ? "video" : "image",
    title: node.title || (node.type === "video" ? "视频预览" : "图片预览"),
    aspectRatio: previewAspectRatio(node),
    downloadName: previewDownloadName(node),
  });
}
