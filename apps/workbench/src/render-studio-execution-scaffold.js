import { el } from "./dom.js";
import { displayText } from "./display-labels.js";

export function renderExecutionScaffold(cards, selectedCardId, state = {}) {
  if (!Array.isArray(cards) || !cards.length) return null;
  const selected = cards.find((card) => card.card_id === selectedCardId) || cards[0];
  const activeIntent = state.studioExecutionIntent || "";
  return el("aside", { className: "libtv-execution-scaffold" }, [
    el("header", {}, [
      el("div", {}, [
        el("strong", { text: "节点连接" }),
        el("small", { text: `${cards.length} 个画布对象` }),
      ]),
      el("span", { text: "本地骨架" }),
    ]),
    renderExecutionEdges(cards),
    renderParameterDrawer(selected),
    renderActionQueue(selected, activeIntent),
    renderExecutionStatus(selected, activeIntent),
    renderIntentFlow(activeIntent),
  ]);
}

function renderExecutionEdges(cards) {
  const pairs = cards.slice(0, 5).map((card, index) => [card, cards[index + 1]]).filter(([, to]) => to);
  const items = pairs.length ? pairs : [[cards[0], null]];
  return el("section", { className: "libtv-execution-edges" }, [
    el("h3", { text: "连接关系" }),
    ...items.map(([from, to], index) => renderEdgeRow(from, to, index)),
  ]);
}

function renderEdgeRow(from, to, index) {
  return el("article", { className: "libtv-canvas-edge" }, [
    el("span", { text: String(index + 1).padStart(2, "0") }),
    el("strong", { text: displayText(from.title || from.card_id || "上游节点") }),
    el("em", { text: "→" }),
    el("small", { text: to ? displayText(to.title || to.card_id || "下游节点") : "等待下游节点" }),
  ]);
}

function renderParameterDrawer(card) {
  return el("section", { className: "libtv-parameter-drawer" }, [
    el("h3", { text: "参数抽屉" }),
    el("p", { text: displayText(card.title || "当前节点") }),
    el("div", { className: "libtv-parameter-grid" }, [
      parameter("模型", modelFor(card)),
      parameter("画幅", "16:9"),
      parameter("时长", "5s"),
      parameter("批次", "1"),
      parameter("Seed", "135"),
      parameter("状态", "能力门关闭"),
    ]),
    el("small", { text: "参数只保存为本地执行意图，等待后续能力授权。" }),
  ]);
}

function renderActionQueue(card, activeIntent) {
  const actions = [
    ["preflight", "生成预检", "检查能力门和阻塞项"],
    ["register", "登记执行意图", displayText(card.title || "当前节点")],
    ["wait_gate", "等待能力授权", "不触发真实生成"],
  ];
  return el("section", { className: "libtv-action-queue" }, [
    el("h3", { text: "待执行动作" }),
    ...actions.map(([intent, label, summary]) =>
      el("button", {
        className: activeIntent === intent ? "active" : "",
        attrs: { type: "button", "data-execution-intent": intent, "aria-pressed": activeIntent === intent ? "true" : "false" },
      }, [
        el("strong", { text: label }),
        el("small", { text: summary }),
      ]),
    ),
    el("p", { text: "只登记本地执行意图，不启动真实生成。" }),
  ]);
}

function renderExecutionStatus(card, activeIntent) {
  const receipt = intentReceipt(card, activeIntent);
  return el("section", { className: "libtv-execution-status" }, [
    el("h3", { text: "执行回执" }),
    el("strong", { text: activeIntent ? "本地意图已登记" : "等待动作选择" }),
    el("p", { text: receipt }),
    el("small", { text: "未创建真实任务 · 未启动 provider" }),
  ]);
}

function renderIntentFlow(activeIntent) {
  const engaged = Boolean(activeIntent);
  const steps = [
    ["意图登记", engaged ? "done" : "pending", engaged ? "已写入当前 Workbench 状态" : "等待动作"],
    ["能力门检查", engaged ? "active" : "pending", "等待能力门授权"],
    ["真实生成", "locked", "未创建真实任务"],
  ];
  return el("ol", { className: "libtv-intent-flow" }, steps.map(([label, status, summary]) =>
    el("li", { className: `status-${status}` }, [
      el("span", { text: label }),
      el("small", { text: summary }),
    ]),
  ));
}

function intentReceipt(card, activeIntent) {
  const target = displayText(card.title || "当前节点");
  const labels = {
    preflight: `准备对「${target}」做本地预检；等待能力门授权。`,
    register: `已登记「${target}」的执行意图；等待能力门授权。`,
    wait_gate: `「${target}」继续保持等待；能力门授权前不触发真实生成。`,
  };
  return labels[activeIntent] || "选择一个待执行动作后，只会更新本地状态。";
}

function parameter(label, value) {
  return el("article", {}, [
    el("span", { text: label }),
    el("strong", { text: value }),
  ]);
}

function modelFor(card) {
  const kind = String(card.kind || "").toLowerCase();
  if (kind.includes("scene") || kind.includes("video")) return "Seedance 2.0";
  if (kind.includes("image")) return "Lib Image";
  if (kind.includes("script") || kind.includes("text")) return "GVLM 3.1";
  return "AFS Runtime";
}
