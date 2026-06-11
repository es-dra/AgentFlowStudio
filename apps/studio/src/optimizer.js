import { buildOptimizationRequest, normalizeOptimization, buildLocalOptimization } from "./optimizer-contract.js";
import { showPopover, el } from "./overlay.js";
import { icon } from "./icons.js";

// Prompt optimization stays anchored to the node input and hides internal assembly details.

export function openOptimizer(store, runtime, nodeId, anchorEl, textarea) {
  const pop = el("div", "optimizer-pop");

  const head = el("div", "opt-head");
  const title = el("span", "opt-title");
  title.innerHTML = `${icon("sparkles", 14)} 优化提示词`;
  head.appendChild(title);
  const stateLabel = el("span", "opt-state", "优化中…");
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
    stateLabel.textContent = "优化中…";
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
    replaceBtn.addEventListener("click", () => { applyPrompt(outcome.optimized); close(); });
    const appendBtn = el("button", "opt-btn", "追加");
    appendBtn.addEventListener("click", () => {
      const current = store.get().nodes[nodeId]?.prompt || "";
      applyPrompt(current ? `${current}\n${outcome.optimized}` : outcome.optimized);
      close();
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

  function applyPrompt(text) {
    store.set((s) => {
      const node = s.nodes[nodeId];
      if (node) node.prompt = text;
    });
    if (textarea) textarea.value = text;
  }

  function loadingView() {
    const wrap = el("div", "opt-loading");
    wrap.innerHTML = '<span class="spinner"></span><span>正在结合专业知识与项目上下文优化…</span>';
    return wrap;
  }
}
