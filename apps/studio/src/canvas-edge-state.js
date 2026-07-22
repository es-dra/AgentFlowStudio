export function relationLabel(relation) {
  return {
    director: "导演",
    reference: "参考",
    fork: "分支",
    sequence: "顺序",
    proposed: "待确认",
  }[relation] || "";
}

export function edgeAccessibleLabel(edge, from, to, relation) {
  const relationText = relationLabel(relation) || "生成";
  return `${from?.title || edge.from} 到 ${to?.title || edge.to}，${relationText}关系`;
}

export function edgeRelatedToFocus(edge, relations) {
  if (!relations?.focus) return false;
  if (edge.from === relations.focus || edge.to === relations.focus) return true;
  const upstreamPair = relations.upstream.has(edge.from) && relations.upstream.has(edge.to);
  const downstreamPair = relations.downstream.has(edge.from) && relations.downstream.has(edge.to);
  return upstreamPair || downstreamPair;
}

export function syncEdgeStateClass(path, item, edge, state) {
  const lifecycle = edgeLifecycleState(edge, state);
  item.dataset.edgeLifecycle = lifecycle;
  path.classList.remove("edge-running", "edge-pending", "edge-recovery", "edge-failed", "edge-paused");
  if (["running", "pending", "recovery", "failed", "paused"].includes(lifecycle)) {
    path.classList.add(`edge-${lifecycle}`);
  }
}

export function edgeLifecycleState(edge, state) {
  const raw = String(edge.status || edge.lifecycle_state || edge.lifecycle || "").toLowerCase();
  if (["running", "pending", "recovery", "failed", "paused"].includes(raw)) return raw;
  if (state.ui?.lastConnectedEdgeId === edge.id) return "pending";
  return "idle";
}

export function syncEdgeRelationClass(path, edge, relations) {
  if (!relations) return;
  const upSide = (relations.upstream.has(edge.from) || edge.from === relations.focus)
    && (relations.upstream.has(edge.to) || edge.to === relations.focus);
  const downSide = (relations.downstream.has(edge.to) || edge.to === relations.focus)
    && (relations.downstream.has(edge.from) || edge.from === relations.focus);
  if (edge.to === relations.focus || (upSide && relations.upstream.has(edge.from))) {
    path.classList.add("rel-up-edge");
  } else if (edge.from === relations.focus || (downSide && relations.downstream.has(edge.to))) {
    path.classList.add("rel-down-edge");
  } else {
    path.classList.add("rel-dim-edge");
  }
}
