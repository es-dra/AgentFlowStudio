import { buildOptimizationRequest, normalizeOptimization, buildLocalOptimization } from "./optimizer-contract.js";
import { showPopover, el } from "./overlay.js";
import { icon } from "./icons.js";
import { connect } from "./nodes.js";

// Prompt optimization stays anchored to the node input and hides internal assembly details.

export function openOptimizer(store, runtime, nodeId, anchorEl, textarea) {
  const pop = el("div", "optimizer-pop");

  const head = el("div", "opt-head");
  const title = el("span", "opt-title");
  title.innerHTML = `${icon("sparkles", 14)} 优化提示词`;
  head.appendChild(title);
  const stateLabel = el("span", "opt-state", "优化中...");
  head.appendChild(stateLabel);
  const closeBtn = el("button", "opt-close");
  closeBtn.innerHTML = icon("x", 14);
  head.appendChild(closeBtn);
  pop.appendChild(head);

  const body = el("div", "opt-body");
  pop.appendChild(body);

  const actions = el("div", "opt-actions");
  pop.appendChild(actions);

  const close = showPopover(anchorEl, pop, { place: "top", alignRight: true, avoidSelector: ".prompt-bar" });
  closeBtn.addEventListener("click", close);

  run();

  async function run() {
    stateLabel.textContent = "优化中...";
    actions.replaceChildren();
    body.replaceChildren(loadingView());
    const node = store.get().nodes[nodeId];
    if (!node) { close(); return; }
    const request = buildOptimizationRequest(store.get(), node);
    let outcome;
    try {
      const result = await runtime.optimizePrompt(request);
      outcome = normalizeOptimization(result, request);
    } catch {
      outcome = buildLocalOptimization(request);
    }
    renderResult(outcome, request);
  }

  function renderResult(outcome, request) {
    stateLabel.textContent = outcome.source === "runtime" ? "已优化" : "本地优化";
    body.replaceChildren();

    body.appendChild(sourceChips(request));
    const bundle = contextBundleView(outcome.context_bundle);
    if (bundle) body.appendChild(bundle);

    body.appendChild(el("div", "opt-section-label", "原始提示词"));
    body.appendChild(el("div", "opt-original", outcome.original));

    body.appendChild(el("div", "opt-section-label", "优化后"));
    const result = el("div", "opt-result");
    if (outcome.sections?.length) {
      for (const section of outcome.sections) {
        const line = el("div");
        const name = el("span", "opt-sec-name", `【${section.name}】`);
        line.appendChild(name);
        line.appendChild(document.createTextNode(section.text));
        result.appendChild(line);
      }
    } else {
      result.textContent = outcome.optimized;
    }
    body.appendChild(result);

    actions.replaceChildren();
    const replaceBtn = el("button", "opt-btn primary", "替换");
    replaceBtn.addEventListener("click", () => {
      applyPrompt(outcome.optimized);
      stateLabel.textContent = "已替换";
      setTimeout(close, 260);
    });
    const appendBtn = el("button", "opt-btn", "追加");
    appendBtn.addEventListener("click", () => {
      const current = store.get().nodes[nodeId]?.prompt || "";
      applyPrompt(current ? `${current}\n${outcome.optimized}` : outcome.optimized);
      stateLabel.textContent = "已追加";
      setTimeout(close, 260);
    });
    const copyBtn = el("button", "opt-btn", "复制");
    copyBtn.addEventListener("click", async () => {
      try { await navigator.clipboard.writeText(outcome.optimized); copyBtn.textContent = "已复制"; }
      catch { copyBtn.textContent = "复制失败"; }
      setTimeout(() => { copyBtn.textContent = "复制"; }, 1200);
    });
    const retryBtn = el("button", "opt-btn", "重新优化");
    retryBtn.addEventListener("click", run);
    actions.appendChild(replaceBtn);
    actions.appendChild(appendBtn);
    actions.appendChild(copyBtn);
    actions.appendChild(el("span", "row-spacer"));
    actions.appendChild(retryBtn);
    requestAnimationFrame(() => close.reposition?.());
  }

  function sourceChips(request) {
    const chips = el("div", "opt-source-chips");
    for (const label of optimizationSources(request)) {
      chips.appendChild(el("span", "opt-source-chip", label));
    }
    return chips;
  }

  function optimizationSources(request) {
    const labels = ["影视结构"];
    if (request.style) labels.push("项目风格");
    if (request.director_setup) labels.push("导演台布置");
    if (request.asset_refs?.length) labels.push("角色/场景设定");
    return labels;
  }

  function contextBundleView(bundle) {
    if (!bundle) return null;
    const wrap = el("div", "opt-context-assets");
    const included = Array.isArray(bundle.included_assets) ? bundle.included_assets : [];
    const available = Array.isArray(bundle.available_project_assets) ? bundle.available_project_assets : [];
    const warnings = Array.isArray(bundle.warnings) ? bundle.warnings : [];
    const title = el("div", "opt-section-label", "fixed assets");
    const chips = el("div", "opt-source-chips");
    for (const item of included) {
      const suffix = item.connected ? "connected" : "unconnected";
      chips.appendChild(el("span", "opt-source-chip", `${item.label || item.asset_id} · ${suffix}`));
    }
    for (const item of available.filter((asset) => !asset.injected).slice(0, 6)) {
      chips.appendChild(el("span", "opt-source-chip muted", `${item.label || item.asset_id} · available`));
    }
    wrap.append(title, chips);
    renderConnectionWarnings(wrap, warnings);
    renderLockWarnings(wrap, warnings);
    return wrap;
  }

  function renderConnectionWarnings(wrap, warnings) {
    for (const warning of warnings.filter((item) => item.warning_id === "named_asset_not_connected")) {
      const row = el("div", "opt-asset-warning");
      row.appendChild(document.createTextNode(`已引用但未连线，生成时不会携带：${warning.label || warning.asset_id}`));
      const connectBtn = el("button", "opt-inline-btn", "一键连线");
      connectBtn.dataset.action = "connect-named-asset";
      connectBtn.addEventListener("click", () => {
        if (connectNamedAssetToTarget(warning.asset_id)) run();
      });
      row.appendChild(connectBtn);
      wrap.appendChild(row);
    }
  }

  function renderLockWarnings(wrap, warnings) {
    for (const warning of warnings.filter((item) => item.warning_id === "best_effort_lock_conflict")) {
      const row = el("div", "opt-asset-warning");
      row.appendChild(document.createTextNode(`best-effort conflict: ${warning.lock_text || warning.asset_id}`));
      const unlockBtn = el("button", "opt-inline-btn", "本次解除");
      unlockBtn.dataset.action = "temporary-unlock";
      unlockBtn.addEventListener("click", () => addTemporaryLockOverride(warning));
      row.appendChild(unlockBtn);
      wrap.appendChild(row);
    }
  }

  function connectNamedAssetToTarget(assetId) {
    const state = store.get();
    const source = Object.values(state.nodes).find((item) => item.id !== nodeId && hasVisualAsset(item, assetId));
    if (!source || !state.nodes[nodeId]) return false;
    connect(store, source.id, nodeId);
    return true;
  }

  function addTemporaryLockOverride(warning) {
    const assetId = String(warning.asset_id || "").trim();
    const lockText = String(warning.lock_text || "").trim();
    if (!assetId || !lockText) return;
    store.set((s) => {
      const node = s.nodes[nodeId];
      if (!node) return;
      const existing = Array.isArray(node.params?.temporaryLockOverrides) ? node.params.temporaryLockOverrides : [];
      node.params.temporaryLockOverrides = [
        ...existing.filter((item) => !(item.asset_id === assetId && item.lock_text === lockText)),
        { asset_id: assetId, lock_text: lockText, reason: "one-off-ui-unlock" },
      ];
    });
    stateLabel.textContent = "本次生成已解除锁定";
  }

  function applyPrompt(text) {
    store.set((s) => {
      const node = s.nodes[nodeId];
      if (node) node.prompt = text;
    });
    if (textarea) textarea.value = text;
  }

  function loadingView() {
    const wrap = el("div", "opt-loading");
    wrap.innerHTML = '<span class="spinner"></span><span>正在结合专业知识与项目上下文优化...</span>';
    return wrap;
  }
}

function hasVisualAsset(node, assetId) {
  const values = [
    ...(Array.isArray(node?.params?.visualAssets) ? node.params.visualAssets : []),
    ...(Array.isArray(node?.params?.visual_asset_ids) ? node.params.visual_asset_ids : []),
  ];
  return values.some((item) => String(item?.asset_id || item?.assetId || item || "") === String(assetId || ""));
}
