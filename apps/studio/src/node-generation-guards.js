import { buildAssetReferenceActions } from "./asset-reference-inspector.js";
import { el, showModal } from "./overlay.js";
import { assetLabel, assetTypeLabel } from "./asset-reference-summary.js";
import { preflightSourceEvidenceSummaryText } from "./generation-preflight-source-evidence.js";
import { normalizeVideoCapabilities, videoPreflightBlockMessage } from "./presets/video-capabilities.js";

export async function prepareGenerationRequest(store, runtime, node, request, kind) {
  const preflight = kind === "video_revision"
    ? runtime?.preflightVideoRevision
    : kind === "video"
      ? runtime?.preflightVideo
      : runtime?.preflightKeyframe;
  if (!preflight) return request;
  let working = {
    ...request,
    temporary_asset_exclusions: normalizeAssetExclusions(request.temporary_asset_exclusions),
  };
  while (true) {
    let outcome;
    try {
      outcome = await preflight(working);
    } catch (error) {
      if (missingPreflightRouteError(error)) {
        throw new Error(staleRuntimePreflightMessage(kind));
      }
      throw error;
    }
    cacheVideoPreflightCapabilities(store, node.id, outcome, kind);
    const blockMessage = videoPreflightBlockMessage(outcome);
    if (blockMessage) throw new Error(blockMessage);
    const unconnectedNamed = unconnectedLabelMatchedAssets(outcome);
    if (unconnectedNamed.length) {
      const decision = await showUnconnectedNamedAssetModal(unconnectedNamed, kind);
      if (decision.action === "cancel") return null;
      const nextExclusions = mergeAssetExclusions(
        working.temporary_asset_exclusions,
        decision.assetIds,
        "user_excluded_unconnected_named_asset",
      );
      if (nextExclusions.length === working.temporary_asset_exclusions.length) return { ...working, preflight_token: outcome?.preflight_token || null };
      store.set((s) => {
        const n = s.nodes[node.id];
        if (n) n.params.temporaryAssetExclusions = nextExclusions;
      }, { history: false });
      working = { ...working, temporary_asset_exclusions: nextExclusions, preflight_token: null };
      continue;
    }
    const included = Array.isArray(outcome?.included_assets) ? outcome.included_assets : [];
    if (!included.length) return { ...working, preflight_token: outcome?.preflight_token || null };
    const carryPolicy = assetCardCarryPolicy(node, kind);
    if (carryPolicy.mode === "asset_card_standalone_character") {
      const autoExcluded = unrelatedAssetIdsForStandaloneCharacterAsset(outcome, node);
      if (autoExcluded.length) {
        const nextExclusions = mergeAssetExclusions(
          working.temporary_asset_exclusions,
          autoExcluded,
          "asset_card_character_unrelated_reference",
        );
        if (nextExclusions.length !== working.temporary_asset_exclusions.length) {
          store.set((s) => {
            const n = s.nodes[node.id];
            if (n) n.params.temporaryAssetExclusions = nextExclusions;
          }, { history: false });
          working = { ...working, temporary_asset_exclusions: nextExclusions, preflight_token: null };
          continue;
        }
      }
    }
    const decision = await showCarryConfirmModal(outcome, node, kind, carryPolicy);
    if (decision.action === "cancel") return null;
    if (decision.action === "continue") return { ...working, preflight_token: outcome?.preflight_token || null };
    const nextExclusions = mergeAssetExclusions(
      working.temporary_asset_exclusions,
      decision.assetIds,
      decision.reason || "user_excluded_from_preflight_confirmation",
    );
    if (nextExclusions.length === working.temporary_asset_exclusions.length) continue;
    store.set((s) => {
      const n = s.nodes[node.id];
      if (n) n.params.temporaryAssetExclusions = nextExclusions;
    }, { history: false });
    working = { ...working, temporary_asset_exclusions: nextExclusions, preflight_token: null };
  }
}

export function normalizeStringList(values) {
  const seen = new Set();
  const result = [];
  for (const value of Array.isArray(values) ? values : []) {
    const item = String(value || "").trim().slice(0, 80);
    if (!item || seen.has(item)) continue;
    seen.add(item);
    result.push(item);
  }
  return result;
}

export function clearOneRunOverrides(store, nodeId, options = {}) {
  const clearLocks = options.locks !== false;
  const clearAssets = options.assets !== false;
  store.set((s) => {
    const n = s.nodes[nodeId];
    if (!n) return;
    if (clearLocks) n.params.temporaryLockOverrides = [];
    if (clearAssets) n.params.temporaryAssetExclusions = [];
  }, { history: false });
}

function cacheVideoPreflightCapabilities(store, nodeId, preflight, kind) {
  if (kind !== "video" || !preflight?.provider_capability_limits) return;
  store.set((s) => {
    const n = s.nodes[nodeId];
    if (!n) return;
    if (!n.params || typeof n.params !== "object") n.params = {};
    n.params.videoProviderCapabilities = normalizeVideoCapabilities(preflight.provider_capability_limits);
    n.params.videoProviderCapabilityBlocks = Array.isArray(preflight.blocked_unsupported_combinations)
      ? preflight.blocked_unsupported_combinations
      : [];
  }, { history: false });
}

function unconnectedLabelMatchedAssets(preflight) {
  return buildAssetReferenceActions(preflight).filter((action) => action.blocking);
}

function missingPreflightRouteError(error) {
  return Number(error?.status) === 404 && String(error?.route || "").endsWith("/preflight");
}

function staleRuntimePreflightMessage(kind) {
  const label = kind === "video_revision" ? "视频修改" : kind === "video" ? "视频生成" : "关键帧生成";
  return `${label}服务暂时不可用，请刷新页面后重试。`;
}

function showCarryConfirmModal(preflight, node, kind, policy = {}) {
  return new Promise((resolve) => {
    const optionalCarry = policy.mode === "asset_card_optional_reference";
    const included = Array.isArray(preflight?.included_assets) ? preflight.included_assets : [];
    const excluded = Array.isArray(preflight?.excluded_assets) ? preflight.excluded_assets : [];
    const conflicts = Array.isArray(preflight?.asset_conflicts) ? preflight.asset_conflicts : [];
    const overrides = Array.isArray(preflight?.context_bundle?.temporary_lock_overrides)
      ? preflight.context_bundle.temporary_lock_overrides
      : [];
    const tempExcluded = excluded.filter((item) => item.reason === "temporary_asset_excluded_by_user");
    const subjectId = preflight?.subject_reference_asset_id || "";
    const modal = el("div", "modal compact generation-carry-modal");
    const head = el("div", "modal-head");
    head.appendChild(el("strong", "", "生成前确认"));
    head.appendChild(el("span", "head-spacer"));
    const closeBtn = el("button", "modal-close");
    closeBtn.textContent = "×";
    head.appendChild(closeBtn);

    const body = el("div", "modal-body generation-carry-body");
    body.appendChild(el(
      "p",
      "carry-note",
      optionalCarry
        ? "本次是资产图生成；固定资产只作为可选参考。未勾选的固定资产不会在本次资产图生成中携带。"
        : `${kind === "video" ? "视频" : "图片"}生成将携带以下固定资产。固定资产会约束结果，即使未检测到冲突也会生效。`,
    ));
    const list = el("div", "carry-asset-list");
    const checks = new Map();
    for (const asset of included) {
      const row = el("label", "carry-asset-row");
      const input = document.createElement("input");
      input.type = "checkbox";
      input.value = asset.asset_id;
      checks.set(asset.asset_id, input);
      const text = el("span", "carry-asset-text");
      text.textContent = `${assetTypeLabel(asset)} · ${assetLabel(asset)}${asset.asset_id === subjectId ? " · 主体参考图" : ""}`;
      const sig = el("small", "", asset.signature || asset.detail_level || "");
      row.append(input, text, sig);
      list.appendChild(row);
    }
    body.appendChild(list);
    const sourceEvidenceSummary = preflightSourceEvidenceSummaryText(preflight);
    if (sourceEvidenceSummary) body.appendChild(el("div", "carry-muted", sourceEvidenceSummary));
    const warningBox = el("div", conflicts.length ? "carry-warning" : "carry-muted");
    if (optionalCarry) {
      warningBox.textContent = conflicts.length
        ? `检测到 ${conflicts.length} 条疑似冲突；只勾选仍需携带的资产，其余会在本次生成中排除。`
        : "未勾选的固定资产默认不携带；只勾选与当前场景或道具有明确关系的资产。";
    } else {
      warningBox.textContent = conflicts.length
        ? `检测到 ${conflicts.length} 条疑似冲突；未排除资产或解除锁定时，固定资产约束优先生效。`
        : "未检测到明显冲突，但固定资产仍会约束结果。";
    }
    body.appendChild(warningBox);
    if (overrides.length) {
      body.appendChild(el("div", "carry-muted", `本次已解除 ${overrides.length} 条锁定。`));
    }
    if (tempExcluded.length) {
      body.appendChild(el("div", "carry-muted", `本次已排除 ${tempExcluded.length} 项资产。`));
    }

    const actions = el("div", "modal-actions");
    const cancel = el("button", "ghost-btn", "取消");
    const exclude = el("button", "ghost-btn", "本次不携带选中项");
    const submit = el("button", "primary-btn", optionalCarry ? "按选择继续" : "继续生成");
    exclude.disabled = true;
    if (optionalCarry) {
      actions.append(cancel, submit);
    } else {
      actions.append(cancel, exclude, submit);
    }
    modal.append(head, body, actions);

    let settled = false;
    const close = showModal(modal, { onClose: () => { if (!settled) resolve({ action: "cancel" }); } });
    const finish = (decision) => {
      if (settled) return;
      settled = true;
      close();
      resolve(decision);
    };
    const selectedIds = () => [...checks.entries()].filter(([, input]) => input.checked).map(([assetId]) => assetId);
    const unselectedIds = () => [...checks.entries()].filter(([, input]) => !input.checked).map(([assetId]) => assetId);
    list.addEventListener("change", () => {
      exclude.disabled = selectedIds().length === 0;
    });
    closeBtn.addEventListener("click", () => finish({ action: "cancel" }));
    cancel.addEventListener("click", () => finish({ action: "cancel" }));
    submit.addEventListener("click", () => {
      if (!optionalCarry) {
        finish({ action: "continue" });
        return;
      }
      const assetIds = unselectedIds();
      finish(assetIds.length
        ? { action: "exclude", assetIds, reason: "optional_asset_reference_not_selected" }
        : { action: "continue" });
    });
    exclude.addEventListener("click", () => finish({ action: "exclude", assetIds: selectedIds() }));
  });
}

function assetCardCarryPolicy(node, kind) {
  if (kind === "video" || kind === "video_revision") return { mode: "fixed_asset_guard" };
  if (node?.params?.nodeRole !== "asset_card_draft") return { mode: "fixed_asset_guard" };
  const assetType = String(node.params?.assetCardDraft?.asset_type || "").trim();
  if (assetType === "character") return { mode: "asset_card_standalone_character" };
  if (assetType === "scene" || assetType === "prop") return { mode: "asset_card_optional_reference" };
  return { mode: "fixed_asset_guard" };
}

function unrelatedAssetIdsForStandaloneCharacterAsset(preflight, node) {
  // 角色资产会自动排除其他固定资产，避免新角色被已有角色约束。
  const currentLabel = normalizeAssetLabel(node?.params?.assetCardDraft?.label || node?.title || "");
  const included = Array.isArray(preflight?.included_assets) ? preflight.included_assets : [];
  return included
    .filter((asset) => !sameAssetLabel(asset, currentLabel))
    .map((asset) => String(asset?.asset_id || "").trim())
    .filter(Boolean);
}

function sameAssetLabel(asset, currentLabel) {
  const assetLabel = normalizeAssetLabel(asset?.label || asset?.title || asset?.signature || "");
  return Boolean(assetLabel && currentLabel && assetLabel === currentLabel);
}

function normalizeAssetLabel(value) {
  return String(value || "")
    .replace(/^@+/, "")
    .replace(/^(角色|场景|道具)[资产]*[·:：\s-]*/u, "")
    .trim()
    .toLowerCase();
}
function showUnconnectedNamedAssetModal(assets, kind) {
  return new Promise((resolve) => {
    const modal = el("div", "modal compact generation-carry-modal");
    const head = el("div", "modal-head");
    head.appendChild(el("strong", "", "命名资产未注入"));
    head.appendChild(el("span", "head-spacer"));
    const closeBtn = el("button", "modal-close");
    closeBtn.textContent = "×";
    head.appendChild(closeBtn);

    const body = el("div", "modal-body generation-carry-body");
    body.appendChild(el(
      "p",
      "carry-note",
      `当前${kind === "video" ? "视频" : "图片"}提示词提到了已固定资产，但本次上下文没有成功注入。可以先不携带这些资产继续，或取消后检查资产连接/固定状态。`,
    ));
    const list = el("div", "carry-asset-list");
    for (const asset of assets) {
      const row = el("div", "carry-asset-row");
      row.appendChild(el("span", "carry-asset-text", `${assetTypeLabel(asset)} · ${assetLabel(asset)}`));
      row.appendChild(el("small", "", asset.reason || "未连接且未注入"));
      list.appendChild(row);
    }
    body.appendChild(list);

    const actions = el("div", "modal-actions");
    const cancel = el("button", "ghost-btn", "取消");
    const submit = el("button", "primary-btn", "本次不携带并继续");
    actions.append(cancel, submit);
    modal.append(head, body, actions);

    let settled = false;
    const close = showModal(modal, { onClose: () => { if (!settled) resolve({ action: "cancel" }); } });
    const finish = (decision) => {
      if (settled) return;
      settled = true;
      close();
      resolve(decision);
    };
    const assetIds = () => assets.map((asset) => asset.asset_id).filter(Boolean);
    closeBtn.addEventListener("click", () => finish({ action: "cancel" }));
    cancel.addEventListener("click", () => finish({ action: "cancel" }));
    submit.addEventListener("click", () => finish({ action: "exclude", assetIds: assetIds() }));
  });
}

function normalizeAssetExclusions(values) {
  const seen = new Set();
  const result = [];
  for (const item of Array.isArray(values) ? values : []) {
    const assetId = String(item?.asset_id || item?.assetId || item || "").trim();
    if (!assetId || seen.has(assetId)) continue;
    seen.add(assetId);
    result.push({ asset_id: assetId, reason: String(item?.reason || "one_run_asset_exclusion").slice(0, 120) });
  }
  return result;
}

function mergeAssetExclusions(existing, assetIds, reason = "user_excluded_from_preflight_confirmation") {
  const result = normalizeAssetExclusions(existing);
  const seen = new Set(result.map((item) => item.asset_id));
  for (const assetId of assetIds || []) {
    const id = String(assetId || "").trim();
    if (!id || seen.has(id)) continue;
    seen.add(id);
    result.push({ asset_id: id, reason });
  }
  return result;
}
