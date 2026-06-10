import { button, el } from "./dom.js";
import { PROCESS_NODES, PROJECT_SHOWCASES } from "./project-showcase-data.js";

export function renderShowcaseDetail(state = {}) {
  const item = selectedShowcase(state);
  return el("section", { className: `project-portal showcase-detail showcase-${item.palette}` }, [
    renderDetailTopbar(item),
    el("div", { className: "showcase-stage" }, [
      el("div", { className: "showcase-film-frame", attrs: { "aria-hidden": "true" } }, [
        el("span"),
        el("span"),
        el("span"),
      ]),
      el("div", { className: "showcase-action-dock" }, [
        button("立即观看", "noop", "primary"),
        el("button", {
          className: "btn secondary",
          text: "查看制作过程",
          dataset: { showcaseProcess: "open" },
          attrs: { type: "button" },
        }),
        el("button", { className: "showcase-icon", text: "♡", attrs: { type: "button", "aria-label": "收藏" } }),
        el("button", { className: "showcase-icon", text: "↗", attrs: { type: "button", "aria-label": "分享" } }),
      ]),
    ]),
    renderDetailCarousel(item.id),
    state.showcaseProcessOpen ? renderProcessDialog(item, state) : null,
  ]);
}

function renderDetailTopbar(item) {
  return el("header", { className: "showcase-detail-topbar" }, [
    el("button", {
      className: "portal-back",
      text: "‹ 返回",
      dataset: { projectPortal: "home" },
      attrs: { type: "button" },
    }),
    el("span", { className: "showcase-avatar", text: "AF" }),
    el("strong", { text: item.author }),
    el("span", { text: "|" }),
    el("span", { className: "showcase-title-line", text: item.title }),
    el("span", { className: "showcase-updated", text: item.updatedAt }),
  ]);
}

function renderDetailCarousel(activeId) {
  return el("div", { className: "showcase-carousel" }, PROJECT_SHOWCASES.map((item) =>
    el("button", {
      className: `showcase-thumb showcase-thumb-${item.palette}${item.id === activeId ? " selected" : ""}`,
      dataset: { showcaseId: item.id, projectPortal: "showcase-detail" },
      attrs: { type: "button" },
    }, [
      el("span", { text: item.tag }),
      el("strong", { text: item.title }),
    ]),
  ));
}

function renderProcessDialog(item, state) {
  const selectedNodeId = state.showcaseProcessNode || "shot-1";
  return el("div", { className: "process-overlay" }, [
    el("section", { className: "process-dialog", attrs: { role: "dialog", "aria-label": "制作过程" } }, [
      el("header", { className: "process-head" }, [
        el("strong", { text: item.title }),
        el("span", { text: "只读模式，如需创建请复制到当前项目" }),
        el("button", {
          className: "process-copy",
          text: "复制到项目",
          dataset: { showcaseProcess: "copy" },
          attrs: { type: "button" },
        }),
        el("button", {
          className: "process-close",
          text: "×",
          dataset: { showcaseProcess: "close" },
          attrs: { type: "button", "aria-label": "关闭" },
        }),
      ]),
      el("div", { className: "process-canvas" }, [
        edge("part-1", "shot-1", 16, 14, 16, 30),
        edge("part-2", "shot-2", 35, 14, 37, 30),
        edge("part-3", "shot-4", 54, 14, 79, 30),
        edge("shot-1", "shot-5", 16, 42, 28, 58),
        edge("shot-2", "shot-6", 37, 42, 49, 58),
        edge("shot-3", "shot-7", 58, 42, 70, 58),
        ...PROCESS_NODES.map((node) => renderProcessNode(node, selectedNodeId)),
      ]),
      renderProcessNodeDetail(selectedNodeId),
      el("footer", { className: "process-foot" }, [
        el("span", { text: "15%" }),
        el("button", { text: "切换小地图", attrs: { type: "button" } }),
      ]),
    ]),
  ]);
}

function renderProcessNode(node, selectedNodeId) {
  const selected = node.id === selectedNodeId;
  return el("button", {
    className: `process-node${selected ? " selected" : ""}`,
    dataset: { processNode: node.id },
    attrs: { type: "button", style: `left:${node.x}%;top:${node.y}%;` },
  }, [
    el("span", { text: node.type }),
    el("strong", { text: node.label }),
  ]);
}

function renderProcessNodeDetail(selectedNodeId) {
  const node = PROCESS_NODES.find((item) => item.id === selectedNodeId) || PROCESS_NODES[3];
  return el("aside", { className: "process-node-detail" }, [
    el("span", { text: node.type }),
    el("strong", { text: node.label }),
    el("p", { text: "安全摘要：使用已确认的脚本、参考帧和镜头意图生成候选，不展示本地素材路径或 provider 原始响应。" }),
    el("pre", { text: '{ "duration": 15, "aspect": "1.85:1", "gate": "provider 默认关闭" }' }),
  ]);
}

function selectedShowcase(state) {
  return PROJECT_SHOWCASES.find((item) => item.id === state.selectedShowcaseId) || PROJECT_SHOWCASES[0];
}

function edge(from, to, x1, y1, x2, y2) {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const length = Math.hypot(dx, dy);
  const angle = Math.atan2(dy, dx);
  return el("i", {
    className: "process-edge",
    attrs: {
      "data-from": from,
      "data-to": to,
      style: `left:${x1}%;top:${y1}%;width:${length}%;transform:rotate(${angle}rad);`,
    },
  });
}
