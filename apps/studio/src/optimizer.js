import { buildOptimizationRequest, normalizeOptimization } from "./optimizer-contract.js";
import { showPopover, el } from "./overlay.js";
import { icon } from "./icons.js";
import { connect } from "./nodes.js";
import { humanWarning } from "./node-result-view.js";
import { buildAssetReferenceActions } from "./asset-reference-inspector.js";

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
    } catch (error) {
      renderError(error, request);
      return;
    }
    renderResult(outcome, request);
  }

  function renderResult(outcome, request) {
    stateLabel.textContent = "已优化";
    body.replaceChildren();

    body.appendChild(sourceChips(request, outcome));
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
      applyPrompt(outcome.optimized, outcome.plain || outcome.optimized);
      stateLabel.textContent = "已替换";
      setTimeout(close, 260);
    });
    const appendBtn = el("button", "opt-btn", "追加");
    appendBtn.addEventListener("click", () => {
      const currentNode = store.get().nodes[nodeId] || {};
      const current = currentNode.prompt || "";
      const currentPlain = currentNode.params?.lastOptimizedPromptPlain || stripSectionHeaders(current);
      applyPrompt(
        current ? `${current}\n${outcome.optimized}` : outcome.optimized,
        currentPlain ? `${currentPlain}\n${outcome.plain || stripSectionHeaders(outcome.optimized)}` : (outcome.plain || stripSectionHeaders(outcome.optimized)),
      );
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

  function renderError(error, request) {
    stateLabel.textContent = "优化失败";
    body.replaceChildren();
    body.appendChild(sourceChips(request));
    const result = el("div", "opt-result");
    result.textContent = `优化失败：${safeError(error)}`;
    body.appendChild(result);
    actions.replaceChildren();
    const retryBtn = el("button", "opt-btn primary", "重试");
    retryBtn.addEventListener("click", run);
    actions.appendChild(retryBtn);
    requestAnimationFrame(() => close.reposition?.());
  }

  function sourceChips(request, outcome = null) {
    const chips = el("div", "opt-source-chips");
    for (const label of optimizationSources(request, outcome)) {
      chips.appendChild(el("span", "opt-source-chip", label));
    }
    return chips;
  }

  function optimizationSources(request, outcome = null) {
    const labels = [optimizationModeLabel(outcome?.optimization_mode), "影视结构"].filter(Boolean);
    if (request.style) labels.push("项目风格");
    if (request.director_setup) labels.push("导演台布置");
    if (request.asset_refs?.length) labels.push("角色/场景设定");
    return labels;
  }

  function optimizationModeLabel(mode) {
    if (mode === "t2i") return "文生图扩写";
    if (mode === "i2i") return "图生图编辑";
    if (mode === "text") return "文本结构化";
    return "";
  }

  function contextBundleView(bundle) {
    if (!bundle) return null;
    const wrap = el("div", "opt-context-assets");
    const included = Array.isArray(bundle.included_assets) ? bundle.included_assets : [];
    const available = Array.isArray(bundle.available_project_assets) ? bundle.available_project_assets : [];
    const warnings = Array.isArray(bundle.warnings) ? bundle.warnings : [];
    const availableForPanel = available.filter((asset) => !asset.injected).slice(0, 6);
    if (!included.length && !availableForPanel.length && !warnings.length) return null;
    const title = el("div", "opt-section-label", "项目资产引用");
    const chips = el("div", "opt-source-chips");
    for (const item of included) {
      const suffix = item.connected ? "已连线" : "未连线";
      chips.appendChild(el("span", `opt-source-chip${item.connected ? " linked" : " unlinked"}`, `${item.label || item.asset_id} · ${suffix}`));
    }
    for (const item of availableForPanel) {
      chips.appendChild(el("span", "opt-source-chip muted", `${item.label || item.asset_id} · 未引用 · 可连线`));
    }
    wrap.append(title, chips);
    renderConnectionWarnings(wrap, warnings);
    renderLockWarnings(wrap, warnings);
    return wrap;
  }

  function renderConnectionWarnings(wrap, warnings) {
    for (const action of buildAssetReferenceActions({ warnings })) {
      const warning = action.warning || action;
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
    for (const warning of uniqueLockWarnings(warnings)) {
      const row = el("div", "opt-asset-warning");
      row.appendChild(document.createTextNode(humanWarning(warning)));
      const alreadyOverridden = hasOverride(warning);
      const unlockBtn = el("button", "opt-inline-btn", alreadyOverridden ? "本次已解除" : "本次解除");
      unlockBtn.dataset.action = "temporary-unlock";
      unlockBtn.disabled = alreadyOverridden;
      unlockBtn.addEventListener("click", () => {
        addTemporaryLockOverride(warning);
        unlockBtn.textContent = "本次已解除";
        unlockBtn.disabled = true;
      });
      row.appendChild(unlockBtn);
      wrap.appendChild(row);
    }
  }

  function uniqueLockWarnings(warnings) {
    const seen = new Set();
    const result = [];
    for (const warning of warnings.filter((item) => item.warning_id === "best_effort_lock_conflict")) {
      const key = `${warning.asset_id || ""}::${warning.lock_text || ""}`;
      if (seen.has(key)) continue;
      seen.add(key);
      result.push(warning);
    }
    return result;
  }

  function hasOverride(warning) {
    const overrides = store.get().nodes[nodeId]?.params?.temporaryLockOverrides || [];
    return overrides.some((item) => item.asset_id === warning.asset_id && item.lock_text === warning.lock_text);
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

  function applyPrompt(text, plainText) {
    store.set((s) => {
      const node = s.nodes[nodeId];
      if (node) {
        node.prompt = text;
        node.params.lastOptimizedPromptPlain = plainText || stripSectionHeaders(text);
      }
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

function stripSectionHeaders(value) {
  return String(value || "")
    .split(/\r?\n/)
    .map((line) => line.replace(/^\s*(意图|人物|人物\/主体|主体|场景|场景\/美术|镜头|镜头\/构图|灯光|运动|运动\/时间推进|连续性|负面|负面约束)\s*[：:]\s*/, "").trim())
    .filter(Boolean)
    .join("\n");
}

function safeError(error) {
  const message = error instanceof Error ? error.message : String(error || "unknown error");
  const clean = message.replace(/Bearer\s+\S+/gi, "Bearer <redacted>");
  if (/provider service not found|remote LLM prompt optimization unavailable|AFS_ALLOW_REMOTE_LLM/i.test(clean)) {
    return "提示词优化服务未就绪，请检查 LLM provider 配置与 Runtime 启动环境后重试。";
  }
  return clean.slice(0, 180);
}
