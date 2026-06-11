import { allEdges } from "./studio-workflow-graph.js";

export function canvasRelationFocus(state, selectedId, nodes = []) {
  const nodeIds = new Set(nodes.map((node) => node[0]));
  const selected = new Set(Array.isArray(state.selectedNodeIds) ? state.selectedNodeIds.filter((id) => nodeIds.has(id)) : []);
  if (selectedId && nodeIds.has(selectedId)) selected.add(selectedId);
  const edges = allEdges(state).filter((edge) => nodeIds.has(edge.from) && nodeIds.has(edge.to));
  const directUpstream = new Set(edges.filter((edge) => selected.has(edge.to)).map((edge) => edge.from));
  const directDownstream = new Set(edges.filter((edge) => selected.has(edge.from)).map((edge) => edge.to));
  const upstream = collectReachable(selected, edges, "upstream");
  const downstream = collectReachable(selected, edges, "downstream");
  return {
    active: selected.size > 0,
    selected,
    upstream,
    downstream,
    directUpstream,
    directDownstream,
  };
}

export function nodeRelationClasses(focus, id) {
  if (!focus?.active) return "";
  if (focus.selected.has(id)) return " selected relation-selected";
  const upstream = focus.upstream.has(id);
  const downstream = focus.downstream.has(id);
  if (upstream && downstream) return " is-linked relation-bridge";
  if (upstream) return ` is-linked relation-upstream${focus.directUpstream.has(id) ? " relation-direct" : ""}`;
  if (downstream) return ` is-linked relation-downstream${focus.directDownstream.has(id) ? " relation-direct" : ""}`;
  return " is-dimmed";
}

export function edgeRelationClasses(focus, from, to) {
  if (!focus?.active) return "";
  if (focus.selected.has(from) && focus.downstream.has(to)) return " active edge-downstream";
  if (focus.upstream.has(from) && focus.selected.has(to)) return " active edge-upstream";
  if (focus.upstream.has(from) && (focus.upstream.has(to) || focus.selected.has(to))) return " active edge-upstream edge-chain";
  if ((focus.selected.has(from) || focus.downstream.has(from)) && focus.downstream.has(to)) return " active edge-downstream edge-chain";
  return " edge-dimmed";
}

export function collectReachable(startIds, edges, direction) {
  const seen = new Set();
  const queue = [...startIds];
  while (queue.length) {
    const current = queue.shift();
    edges.forEach((edge) => {
      const next = direction === "upstream" && edge.to === current ? edge.from : direction === "downstream" && edge.from === current ? edge.to : "";
      if (!next || startIds.has(next) || seen.has(next)) return;
      seen.add(next);
      queue.push(next);
    });
  }
  return seen;
}
