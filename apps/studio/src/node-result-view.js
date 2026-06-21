import { assetTypeLabel, assetLabel, subjectSuffix } from "./asset-reference-summary.js";
import { icon } from "./icons.js";
import { setRuntimeMediaSource } from "./runtime-media-source.js";

export function resultView(node) {
  const result = document.createElement("div");
  const candidates = candidatePreviews(node);
  result.className = `node-result${node.previewUrl ? " has-preview" : ""}${candidates.length > 1 ? " has-candidates" : ""}`;
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
    result.appendChild(frame);
    if (candidates.length > 1) result.appendChild(candidateGrid(candidates));
    if (node.type === "video") result.appendChild(resultActions(node, result));
  }
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
  continueButton.innerHTML = `${icon("play", 12)}<span>继续生成</span>`;
  actions.appendChild(continueButton);

  const assetButton = document.createElement("button");
  assetButton.className = "mini-btn";
  assetButton.type = "button";
  assetButton.dataset.action = "fix-visual-asset";
  assetButton.innerHTML = `${icon("bookmark", 12)}<span>固定素材</span>`;
  actions.appendChild(assetButton);

  const download = downloadPreviewLink(node);
  download.innerHTML = `${icon("archive", 12)}<span>${node.type === "video" ? "下载视频" : "下载图片"}</span>`;
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

function candidateGrid(candidates) {
  const grid = document.createElement("div");
  grid.className = "candidate-grid";
  candidates.slice(0, 9).forEach((candidate, index) => {
    const item = document.createElement("button");
    item.className = "candidate-card";
    item.type = "button";
    item.title = `候选 ${index + 1}`;
    const img = document.createElement("img");
    setRuntimeMediaSource(img, candidate.url || candidate.preview_url);
    img.alt = `候选 ${index + 1}`;
    img.loading = "lazy";
    item.appendChild(img);
    item.appendChild(candidateBadge(index + 1));
    grid.appendChild(item);
  });
  return grid;
}

function candidateBadge(index) {
  const badge = document.createElement("span");
  badge.className = "candidate-badge";
  badge.textContent = String(index).padStart(2, "0");
  return badge;
}

function candidatePreviews(node) {
  const raw = node.params?.candidatePreviewUrls || node.params?.candidate_previews || node.params?.candidates || [];
  if (!Array.isArray(raw)) return [];
  return raw
    .map((item) => (typeof item === "string" ? { url: item } : item))
    .filter((item) => item?.url || item?.preview_url);
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

function downloadPreviewLink(node) {
  const link = document.createElement("a");
  link.className = "mini-btn node-preview-download";
  setRuntimeMediaSource(link, node.previewUrl);
  link.download = previewDownloadName(node);
  link.textContent = node.type === "video" ? "下载视频" : "下载图片";
  return link;
}

function previewDownloadName(node) {
  const fallback = node.type === "video" ? "afs-video" : "afs-image";
  const base = String(node.title || node.id || fallback)
    .replace(/[\\/:*?"<>|]+/g, "-")
    .trim()
    .slice(0, 80) || fallback;
  return `${base}.${node.type === "video" ? "mp4" : "png"}`;
}
