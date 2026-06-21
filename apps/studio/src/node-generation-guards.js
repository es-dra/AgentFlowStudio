import { buildAssetReferenceActions } from "./asset-reference-inspector.js";
import { el, showModal } from "./overlay.js";

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
    const unconnectedNamed = unconnectedLabelMatchedAssets(outcome);
    if (unconnectedNamed.length) {
      const labels = unconnectedNamed.map((asset) => asset.label || asset.asset_id).join(", ");
      throw new Error(
        `named_asset_not_connected_fail_closed: prompt mentions fixed asset(s) that are not connected to this node: ${labels}. Connect them first or exclude them for this run.`,
      );
    }
    const included = Array.isArray(outcome?.included_assets) ? outcome.included_assets : [];
    if (!included.length) return { ...working, preflight_token: outcome?.preflight_token || null };
    const decision = await showCarryConfirmModal(outcome, node, kind);
    if (decision.action === "cancel") return null;
    if (decision.action === "continue") return { ...working, preflight_token: outcome?.preflight_token || null };
    const nextExclusions = mergeAssetExclusions(working.temporary_asset_exclusions, decision.assetIds);
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

function unconnectedLabelMatchedAssets(preflight) {
  return buildAssetReferenceActions(preflight).filter((action) => action.blocking);
}

function missingPreflightRouteError(error) {
  return Number(error?.status) === 404 && String(error?.route || "").endsWith("/preflight");
}

function staleRuntimePreflightMessage(kind) {
  const label = kind === "video_revision" ? "video revision" : kind === "video" ? "video" : "keyframe";
  return `Runtime Service version is stale or not started from this branch: missing ${label} preflight route. Restart the 8790 Runtime Service and retry.`;
}

function showCarryConfirmModal(preflight, node, kind) {
  return new Promise((resolve) => {
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
    body.appendChild(el("p", "carry-note", `${kind === "video" ? "视频" : "图片"}生成将携带以下固定资产。固定资产会约束结果，即使未检测到冲突也会生效。`));
    const list = el("div", "carry-asset-list");
    const checks = new Map();
    for (const asset of included) {
      const row = el("label", "carry-asset-row");
      const input = document.createElement("input");
      input.type = "checkbox";
      input.value = asset.asset_id;
      checks.set(asset.asset_id, input);
      const text = el("span", "carry-asset-text");
      text.textContent = `${asset.asset_type === "scene" ? "场景" : "角色"} · ${asset.label || asset.asset_id}${asset.asset_id === subjectId ? " · 主体参考图" : ""}`;
      const sig = el("small", "", asset.signature || asset.detail_level || "");
      row.append(input, text, sig);
      list.appendChild(row);
    }
    body.appendChild(list);
    const warningBox = el("div", conflicts.length ? "carry-warning" : "carry-muted");
    warningBox.textContent = conflicts.length
      ? `检测到 ${conflicts.length} 条疑似冲突；未排除资产或解除锁定时，固定资产约束优先生效。`
      : "未检测到明显冲突，但固定资产仍会约束结果。";
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
    const submit = el("button", "primary-btn", "继续生成");
    exclude.disabled = true;
    actions.append(cancel, exclude, submit);
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
    list.addEventListener("change", () => {
      exclude.disabled = selectedIds().length === 0;
    });
    closeBtn.addEventListener("click", () => finish({ action: "cancel" }));
    cancel.addEventListener("click", () => finish({ action: "cancel" }));
    submit.addEventListener("click", () => finish({ action: "continue" }));
    exclude.addEventListener("click", () => finish({ action: "exclude", assetIds: selectedIds() }));
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

function mergeAssetExclusions(existing, assetIds) {
  const result = normalizeAssetExclusions(existing);
  const seen = new Set(result.map((item) => item.asset_id));
  for (const assetId of assetIds || []) {
    const id = String(assetId || "").trim();
    if (!id || seen.has(id)) continue;
    seen.add(id);
    result.push({ asset_id: id, reason: "user_excluded_from_preflight_confirmation" });
  }
  return result;
}
