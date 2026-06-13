export function resultView(node) {
  const result = document.createElement("div");
  result.className = `node-result${node.previewUrl ? " has-preview" : ""}`;
  if (node.previewUrl) {
    if (node.type === "video") {
      const video = document.createElement("video");
      video.className = "node-preview-video";
      video.src = node.previewUrl;
      video.controls = true;
      video.playsInline = true;
      video.preload = "metadata";
      video.style.aspectRatio = previewAspectRatio(node);
      video.setAttribute("aria-label", "generated video");
      result.appendChild(video);
    } else {
      const img = document.createElement("img");
      img.className = "node-preview-img";
      img.src = node.previewUrl;
    img.alt = "生成的关键帧";
      img.loading = "lazy";
      img.style.aspectRatio = previewAspectRatio(node);
      result.appendChild(img);
    }
  }
  const text = document.createElement("div");
  text.className = "node-result-text";
  text.textContent = node.result;
  result.appendChild(text);
  return result;
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
      chip.textContent = `${item.asset_type === "scene" ? "场景" : "人物"} · ${item.label || item.asset_id}${subjectSuffix(item, bundle)}`;
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
        ? `${item.label || item.asset_id} · 超出上限，仅签名参与，锁定未生效`
        : `${item.label || item.asset_id} · 已被同名新版本替代，本次未携带`;
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

function subjectSuffix(item, bundle) {
  if (bundle.subject_reference_asset_id && item.asset_id === bundle.subject_reference_asset_id) return "（含参考图）";
  return "";
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
