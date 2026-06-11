from __future__ import annotations

from pathlib import Path


WORKBENCH_ROOT = Path("apps/workbench")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_libtv_canvas_header_is_folded_into_product_canvas() -> None:
    state = _read(WORKBENCH_ROOT / "src" / "state.js")
    workspace = _read(WORKBENCH_ROOT / "src" / "render-studio-workspace.js")
    css = _read(WORKBENCH_ROOT / "styles-libtv-shell.css")

    for marker in [
        'studioProjectTitle: ""',
        'studioActiveCanvasId: "canvas-1"',
        "renderCanvasTopbar(state)",
        "canvas-topbar",
        "创作画布",
        "剧本到视频工作流",
        'dataset: { canvasAction: "zoom-out" }',
        'dataset: { canvasAction: "zoom-reset" }',
        'dataset: { canvasAction: "zoom-in" }',
        'dataset: { view: "Assets" }',
    ]:
        assert marker in state + workspace

    for marker in [".canvas-topbar", ".canvas-title", ".canvas-top-actions", ".zoom-chip"]:
        assert marker in css

    assert "render-studio-canvas-header.js" not in workspace


def test_libtv_canvas_supports_real_interaction_contracts() -> None:
    state = _read(WORKBENCH_ROOT / "src" / "state.js")
    workspace = _read(WORKBENCH_ROOT / "src" / "render-studio-workspace.js")
    graph = _read(WORKBENCH_ROOT / "src" / "studio-workflow-graph.js")
    node_actions = _read(WORKBENCH_ROOT / "src" / "studio-node-actions.js")
    node_context = _read(WORKBENCH_ROOT / "src" / "render-studio-node-context.js")
    selection_actions = _read(WORKBENCH_ROOT / "src" / "canvas-selection-actions.js")
    relation_focus = _read(WORKBENCH_ROOT / "src" / "canvas-relation-focus.js")
    viewport_actions = _read(WORKBENCH_ROOT / "src" / "canvas-viewport-actions.js")
    interactions = _read(WORKBENCH_ROOT / "src" / "canvas-interactions.js")
    geometry = _read(WORKBENCH_ROOT / "src" / "canvas-interaction-geometry.js")
    node_drag = _read(WORKBENCH_ROOT / "src" / "canvas-node-drag.js")
    node_prompt = _read(WORKBENCH_ROOT / "src" / "render-node-prompt.js")
    node_control = _read(WORKBENCH_ROOT / "src" / "studio-node-control-state.js")
    actions = _read(WORKBENCH_ROOT / "src" / "app-actions.js")
    app = _read(WORKBENCH_ROOT / "src" / "app.js")
    panels = _read(WORKBENCH_ROOT / "src" / "render-studio-panels.js")
    topbar = _read(WORKBENCH_ROOT / "src" / "render-studio-canvas-topbar.js")
    css = _read(WORKBENCH_ROOT / "styles-libtv-shell.css") + _read(WORKBENCH_ROOT / "styles-studio-canvas-interactions.css") + _read(WORKBENCH_ROOT / "styles-studio-edge-toolbar.css") + _read(WORKBENCH_ROOT / "styles-studio-node-ports.css") + _read(WORKBENCH_ROOT / "styles-studio-node-transitions.css") + _read(WORKBENCH_ROOT / "styles-studio-mobile-node-workspace.css") + _read(WORKBENCH_ROOT / "styles-prompt-optimizer.css")
    canvas_source = workspace + graph

    for marker in [
        "canvasNodePositions",
        "canvasCustomNodes",
        "canvasEdges",
        "pendingNodePosition",
        "selectedNodeIds",
        "openedCanvasNodeId",
        "nodeOpenTransition",
        "connectionDraft",
        "selectedEdgeKey",
        "nodeGenerationStatus",
        "pendingNodeGenerationSurface",
        "nodeControlSelections",
    ]:
        assert marker in state

    for marker in [
        "selectedNodeControl",
        "selectNodeControl",
        "nodeControlButton",
        "nodeControlSelect",
        "nodeControlToggle",
        "data-node-control-group",
        "nodeControlValue",
    ]:
        assert marker in node_control

    for marker in [
        "DEFAULT_NODE_POSITIONS",
        "NODE_KIND_META",
        "WORKFLOW_NODE_KIND",
        "nodeKindForCanvasNode",
        "edgePathBetween",
        "nodePort",
        "data-node-id",
        "data-node-x",
        "data-node-y",
        "canvas-node-port",
        "input-port",
        "output-port",
        "data-port-kind",
        "data-open-node-id",
        "data-open-node-kind",
        "studio-canvas-edge pending",
        "data-linked-node-id",
        "data-edge-default",
        "canvas-edge-toolbar",
        "data-selected-edge-key",
        "data-canvas-edge-action",
        "edge-selected",
        "edgeRecords",
    ]:
        assert marker in canvas_source

    for marker in [
        "openCanvasNode",
        "createCanvasNode",
        "studioAddedNodeKind",
        "openedCanvasNodeId",
        "nodeOpenTransition",
        "nodeOpenTransitionForCanvas",
        '"chain"',
        '"enter"',
    ]:
        assert marker in node_actions

    assert '"return"' in app and "nodeOpenTransition" in app
    assert "data-node-open-transition" in workspace

    for marker in [
        "renderNodeOpenContext",
        "node-open-context-bar",
        "context-chain",
        "context-upstream",
        "context-downstream",
        "data-node-open-context",
        "data-context-nav-node",
        "data-open-node-kind",
        "renderContextChip",
        "allEdges",
    ]:
        assert marker in node_context

    for marker in [
        "applyCanvasSelectionAction",
        "duplicateSelectedNodes",
        "alignSelectedNodes",
        "deleteCustomSelectedNodes",
        "clearCanvasSelection",
        "applyCanvasEdgeAction",
        "disconnectSelectedCustomEdge",
        "centerCanvasOnSelectedEdge",
    ]:
        assert marker in selection_actions

    for marker in [
        "canvasRelationFocus",
        "nodeRelationClasses",
        "edgeRelationClasses",
        "collectReachable",
        "relation-upstream",
        "relation-downstream",
        "edge-upstream",
        "edge-downstream",
        "edge-dimmed",
    ]:
        assert marker in relation_focus

    for marker in [
        "fitCanvasToNodes",
        "centerCanvasOnNode",
        "centerCanvasOnSelection",
        "canvasNavigatorMetrics",
        "viewportRect",
        "canvasBounds",
    ]:
        assert marker in viewport_actions

    for marker in [
        'stage.addEventListener("dblclick"',
        "beginCanvasPointer",
        "beginNodeDrag",
        "beginConnection",
        "targetNodeId",
        "selectedNodesInMarquee",
        "canvas-marquee",
        "pointerToWorld",
        "snapToGrid",
        "fit-view",
        "center-selection",
    ]:
        assert marker in interactions

    for marker in [
        "selectedDragIdsForNode",
        "nodeDragBases",
        "connectionTargetAt",
        "nodeInputPointFromDom",
        "nodeOutputPointFromDom",
        "edgePathBetween",
    ]:
        assert marker in geometry

    for marker in [
        "groupNodes",
        "isNodeDragging",
        "moveNodeDrag",
        "endNodeDrag",
    ]:
        assert marker in node_drag

    for marker in [
        "runNodeGenerationPreview",
        "safe_node_generation_preview",
        "node_preview_ready",
    ]:
        assert marker in actions

    for marker in [
        "data-node-generation-status",
        "run-node-generation-preview",
        "nodeGenerateSurface",
        "node-prompt-status",
        "node-prompt-progress",
        "is-generating",
        "is-complete",
    ]:
        assert marker in node_prompt + css

    assert "canvas-anchored-add-menu" in panels
    assert "返回画布" in topbar
    assert 'studioStarter: "close"' in topbar
    for marker in [
        "canvas-selection-frame",
        "canvas-selection-toolbar",
        "data-canvas-selection-action",
        "data-selection-count",
    ]:
        assert marker in workspace

    for marker in [
        "renderCanvasNavigator",
        "canvas-navigator-panel",
        "data-canvas-action",
        "fit-view",
        "center-selection",
    ]:
        assert marker in panels

    for marker in [".workflow-node", ".canvas-marquee", ".studio-canvas-edge.pending", ".studio-canvas-edge.edge-selected", ".canvas-edge-toolbar", ".canvas-connection-target", ".canvas-selection-frame", ".canvas-selection-toolbar", ".canvas-anchored-add-menu", ".workflow-node.relation-upstream", ".workflow-node.relation-downstream", ".studio-canvas-edge.edge-upstream", ".studio-canvas-edge.edge-downstream", ".studio-canvas-edge.edge-dimmed", ".canvas-navigator-panel", ".canvas-mini-map", ".canvas-mini-viewport", ".node-open-context-bar", ".context-node-chip", ".node-flow-shell", ".canvas-node-port", ".input-port", ".output-port", ".connection-success-ripple", "@keyframes node-open-rise", "@keyframes edge-idle-flow", "node-enter-from-canvas", "node-chain-swap", "canvas-node-return", "context-flow-sheen"]:
        assert marker in css

    for marker in [
        "z-index: 14",
        "z-index: 16",
        "min-height: 2400px",
        "padding-bottom: 160px",
    ]:
        assert marker in css

    for marker in [
        "@media (max-width: 920px)",
        "overflow-y: auto",
        "grid-template-columns: repeat(12, minmax(0, 1fr))",
        "width: calc(100vw - 24px) !important",
        "styles-studio-mobile-node-workspace.css",
    ]:
        assert marker in css + _read(WORKBENCH_ROOT / "index.html")
