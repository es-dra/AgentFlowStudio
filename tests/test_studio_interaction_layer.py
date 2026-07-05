from __future__ import annotations

import subprocess
from pathlib import Path

STUDIO_ROOT = Path("apps/studio")


def test_studio_loads_interaction_motion_layer() -> None:
    index = (STUDIO_ROOT / "index.html").read_text(encoding="utf-8")
    source = (STUDIO_ROOT / "src" / "canvas-input.js").read_text(encoding="utf-8")
    connection = (STUDIO_ROOT / "src" / "canvas-connection.js").read_text(encoding="utf-8")

    assert './styles/interaction-motion.css' in index
    for marker in (
        "./interaction/snap-engine.js",
        "./interaction/feedback-layer.js",
        "./interaction/node-resize.js",
        "./interaction/port-magnet.js",
        "./interaction/pointer-kinematics.js",
        "./interaction/auto-pan.js",
        "resolveDragSnap",
        "beginDragFeedback",
        "updateDragFeedback",
        "finishDragFeedback",
        "startNodeResizeSession",
        "moveNodeResizeSession",
        "finishNodeResizeSession",
        "updatePortMagnet",
        "outputPortFromMagnet",
        "animateInertiaPan",
        "applyEdgeAutoPan",
    ):
        assert marker in source
    assert "pulseConnectionSource" in connection
    assert "./interaction/port-geometry.js" in connection
    assert "nodePortWorldPoint" in connection


def test_studio_interaction_modules_remain_small_and_single_purpose() -> None:
    paths = [
        STUDIO_ROOT / "src" / "interaction" / "motion-tokens.js",
        STUDIO_ROOT / "src" / "interaction" / "pointer-kinematics.js",
        STUDIO_ROOT / "src" / "interaction" / "auto-pan.js",
        STUDIO_ROOT / "src" / "interaction" / "snap-engine.js",
        STUDIO_ROOT / "src" / "interaction" / "feedback-layer.js",
        STUDIO_ROOT / "src" / "interaction" / "node-resize.js",
        STUDIO_ROOT / "src" / "interaction" / "port-magnet.js",
        STUDIO_ROOT / "src" / "interaction" / "port-geometry.js",
        STUDIO_ROOT / "styles" / "node-resize.css",
        STUDIO_ROOT / "styles" / "interaction-motion.css",
    ]

    for path in paths:
        assert path.is_file()
        assert len(path.read_text(encoding="utf-8").splitlines()) <= 180


def test_snap_engine_aligns_primary_node_against_existing_geometry() -> None:
    code = r"""
import { resolveDragSnap } from './apps/studio/src/interaction/snap-engine.js';
const state = {
  nodes: {
    a: { id: 'a', x: 98, y: 0, w: 100, h: 80 },
    b: { id: 'b', x: 210, y: 0, w: 100, h: 80 },
  },
};
const session = {
  nodeIds: ['a'],
  primaryId: 'a',
  origins: { a: { x: 98, y: 0 } },
};
const result = resolveDragSnap(state, session, { dx: 10, dy: 0 });
if (result.positions.a.x !== 110) throw new Error(`expected aligned x=110, got ${result.positions.a.x}`);
if (!result.guides.some((guide) => guide.axis === 'x')) throw new Error('expected x guide');
if (result.kind !== 'align') throw new Error(`expected align kind, got ${result.kind}`);
"""
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", code],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_canvas_nodes_have_persistent_resize_affordance() -> None:
    index = (STUDIO_ROOT / "index.html").read_text(encoding="utf-8")
    canvas_view = (STUDIO_ROOT / "src" / "canvas-view.js").read_text(encoding="utf-8")
    canvas_input = (STUDIO_ROOT / "src" / "canvas-input.js").read_text(encoding="utf-8")
    resize_module = (STUDIO_ROOT / "src" / "interaction" / "node-resize.js").read_text(encoding="utf-8")
    styles = (STUDIO_ROOT / "styles" / "node-resize.css").read_text(encoding="utf-8")

    assert index.index('./styles/node-resize.css') > index.index('./styles/studio-media-experience.css')
    assert "nodeResizeHandle()" in canvas_view
    assert 'className = "node-resize-handle"' in canvas_view
    assert 'dataset.resizeHandle = "node"' in canvas_view
    assert "boundedNodeFrame(node)" in canvas_view
    assert 'classList.toggle("empty-tool-node", isEmptyToolNode(node, def))' in canvas_view
    assert 'classList.toggle("compact-node", !node.collapsed && frame.h < 330)' in canvas_view
    assert 'classList.toggle("roomy-node", !node.collapsed && frame.w >= 420)' in canvas_view
    assert "node.collapsed ? effectiveHeight(node) : frame.h" in canvas_view
    assert "startNodeResizeSession(store, nodeEl.dataset.nodeId, e)" in canvas_input
    assert 'session.kind === "resize-node"' in canvas_input
    assert "NODE_RESIZE_SCALE_LIMITS" in resize_module
    assert "boundedNodeFrame(node)" in resize_module
    assert "nodeContentScale" not in resize_module
    assert "node.w = frame.w" in resize_module
    assert "node.h = frame.h" in resize_module
    for marker in (
        ".node-resize-handle",
        ".node.empty-tool-node.compact-node .node-intent",
        "min-height: 24px",
        ".node.empty-tool-node.roomy-node .node-intents",
        "grid-template-columns: repeat(2, minmax(0, 1fr))",
        "max-height: none",
        "cursor: nwse-resize",
        "touch-action: none",
        ".node.collapsed .node-resize-handle",
    ):
        assert marker in styles
    assert "--node-content-scale" not in styles
    assert "calc(13px *" not in styles


def test_node_resize_session_updates_node_dimensions_in_world_space() -> None:
    code = r"""
import { moveNodeResizeSession, resizedNodeFrame, startNodeResizeSession } from './apps/studio/src/interaction/node-resize.js';

const state = {
  viewport: { x: 10, y: 20, scale: 2 },
  nodes: { node_1: { id: 'node_1', w: 280, h: 240 } },
  selection: { nodeIds: [], edgeId: 'edge_a' },
};
const calls = [];
const classSet = new Set();
globalThis.document = {
  querySelector(selector) {
    if (selector !== '[data-node-id="node_1"]') return null;
    return { classList: { add(name) { classSet.add(name); }, remove(name) { classSet.delete(name); } } };
  },
};
const store = {
  get() { return state; },
  set(mutator, options) {
    calls.push(options);
    mutator(state);
  },
};
const session = startNodeResizeSession(store, 'node_1', { clientX: 570, clientY: 500 });
if (!session || session.kind !== 'resize-node') throw new Error('expected resize session');
if (!classSet.has('resizing')) throw new Error('expected resizing class');
if (state.selection.nodeIds[0] !== 'node_1' || state.selection.edgeId !== null) throw new Error('expected node selection');
moveNodeResizeSession(store, session, { clientX: 690, clientY: 620, shiftKey: false });
if (state.nodes.node_1.w !== 336 || state.nodes.node_1.h !== 336) {
  throw new Error(`unexpected resized node ${JSON.stringify(state.nodes.node_1)}`);
}
if (!calls.some((item) => item?.history === false && item?.persist === false)) throw new Error('expected selection to avoid persistence');
if (!calls.some((item) => item?.history === false && item?.persist !== false)) throw new Error('expected resize to persist without history spam');

const clamped = resizedNodeFrame(
  { type: 'text', startWorld: { x: 0, y: 0 }, origin: { w: 280, h: 280 }, base: { w: 280, h: 280 } },
  { x: -500, y: -500 },
);
if (clamped.w !== 280 || clamped.h !== 280) throw new Error(`unexpected clamp ${JSON.stringify(clamped)}`);
"""
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", code],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_text_node_resize_ui_keeps_all_intent_options_visible() -> None:
    nodes = (STUDIO_ROOT / "src" / "nodes.js").read_text(encoding="utf-8")
    styles = (STUDIO_ROOT / "styles" / "node-resize.css").read_text(encoding="utf-8")

    assert "文字生音乐" in nodes or "鏂囧瓧鐢熼煶涔" in nodes
    assert "overflow: visible" not in styles
    assert ".node.empty-tool-node .node-intents" in styles
    assert ".node.empty-tool-node.compact-node .node-intent" in styles
    assert "min-height: 24px" in styles
    assert ".node.empty-tool-node.roomy-node .node-intents" in styles
    assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in styles
    assert "max-height: none" in styles
    assert "white-space: nowrap" in styles
    assert "--node-content-scale" not in styles
    assert "calc(13px *" not in styles


def test_interaction_motion_styles_have_reduced_motion_and_tactile_states() -> None:
    styles = (STUDIO_ROOT / "styles" / "interaction-motion.css").read_text(encoding="utf-8")

    for marker in (
        "#interaction-feedback-layer",
        ".if-guide-x",
        ".if-guide-y",
        ".if-snap-chip",
        ".node.drag-moving",
        ".node.resizing",
        ".node.connection-source",
        ".node.drop-target .node-port.in",
        ".drag-incident-edge",
        ".node.port-magnet-right .node-port.out",
        "@media (prefers-reduced-motion: reduce)",
    ):
        assert marker in styles
    incident_rule = styles.split("#edge-layer [data-edge-id].drag-incident-edge", 1)[1].split("}", 1)[0]
    assert "opacity: 0" not in incident_rule
    assert "opacity: 1" in incident_rule
    assert "node-land" not in styles
    assert "scale: 1.012" not in styles


def test_generating_text_shimmer_is_loaded_and_motion_safe() -> None:
    index = (STUDIO_ROOT / "index.html").read_text(encoding="utf-8")
    styles = (STUDIO_ROOT / "styles" / "generation-feedback.css").read_text(encoding="utf-8")

    assert './styles/generation-feedback.css' in index
    assert len(styles.splitlines()) <= 90
    for marker in (
        ".node.is-generating .node-state-strip span:not(.dot)",
        ".generation-progress-copy strong",
        ".optimizer-pop .opt-state",
        ".optimizer-pop .opt-loading span:not(.spinner)",
        ".job-center-card.generating .job-state",
        "@keyframes generating-text-shimmer",
        "@media (prefers-reduced-motion: reduce)",
    ):
        assert marker in styles
    shimmer_rule = styles.split(".node.is-generating .node-state-strip span:not(.dot)", 1)[1].split("}", 1)[0]
    assert "generating-text-shimmer 4.4s" in shimmer_rule
    reduced_rule = styles.split("@media (prefers-reduced-motion: reduce)", 1)[1].split("}", 1)[0]
    assert "animation: none" in reduced_rule
    assert "-webkit-text-fill-color: currentColor" in reduced_rule


def test_default_canvas_edges_use_solid_frame_connection() -> None:
    index = (STUDIO_ROOT / "index.html").read_text(encoding="utf-8")
    styles = (STUDIO_ROOT / "styles" / "canvas-edges.css").read_text(encoding="utf-8")
    canvas_edges = (STUDIO_ROOT / "src" / "canvas-edges.js").read_text(encoding="utf-8")
    edge_rule = styles.split("#edge-layer path.edge-flow", 1)[1].split("}", 1)[0]
    base_rule = styles.split("#edge-layer path", 1)[1].split("}", 1)[0]

    assert './styles/canvas-edges.css' in index
    assert "stroke-linecap: round" in base_rule
    assert "stroke-width: 1.15" in base_rule
    assert "stroke-dasharray" not in edge_rule
    assert "animation:" not in edge_rule
    assert "edge-spark" in canvas_edges
    assert "syncEdgeSpark" in canvas_edges
    assert "selected.has(edge.from) || selected.has(edge.to)" in canvas_edges
    assert "#edge-layer path.edge-spark" in styles
    assert "animation: edge-spark-forward 3.9s linear infinite" in styles
    assert "@keyframes edge-spark-forward" in styles
    assert "@keyframes edge-spark-reverse" in styles
    assert "animation-name: edge-spark-reverse" in styles


def test_canvas_edges_support_lightweight_disconnect_affordance() -> None:
    index = (STUDIO_ROOT / "index.html").read_text(encoding="utf-8")
    canvas_view = (STUDIO_ROOT / "src" / "canvas-view.js").read_text(encoding="utf-8")
    canvas_edges = (STUDIO_ROOT / "src" / "canvas-edges.js").read_text(encoding="utf-8")
    edge_actions = (STUDIO_ROOT / "src" / "canvas-edge-actions.js").read_text(encoding="utf-8")
    keyboard = (STUDIO_ROOT / "src" / "studio-keyboard.js").read_text(encoding="utf-8")
    nodes = (STUDIO_ROOT / "src" / "nodes.js").read_text(encoding="utf-8")
    styles = (STUDIO_ROOT / "styles" / "canvas-edge-actions.css").read_text(encoding="utf-8")

    assert './styles/canvas-edge-actions.css' in index
    assert "renderEdges(state, relations, store)" in canvas_view
    assert "syncEdgeActionButton" in canvas_edges
    assert "edge-disconnect-button" in canvas_edges
    assert "bindEdgeActionButton" in edge_actions
    assert "selectEdge(store, edgeId)" in edge_actions
    assert "disconnectEdge(store, edgeId)" in edge_actions
    assert "removeEdge(store, edgeId)" in nodes
    assert "handleSelectedEdgeDelete(e, store)" in keyboard
    assert "store.get().selection.edgeId" in keyboard
    for marker in (
        ".edge-disconnect-button",
        "#edge-layer [data-edge-id]:hover .edge-disconnect-button",
        "#edge-layer [data-edge-selected=\"true\"] .edge-disconnect-button",
        "opacity: 0",
        "pointer-events: none",
        "pointer-events: auto",
    ):
        assert marker in styles
    assert len(edge_actions.splitlines()) <= 120
    assert len(styles.splitlines()) <= 120


def test_port_magnet_module_finds_side_ports_without_exact_button_hit() -> None:
    code = r"""
import { outputPortFromMagnet, updatePortMagnet, clearPortMagnet } from './apps/studio/src/interaction/port-magnet.js';

globalThis.document = {
  nodes: [],
  querySelectorAll(selector) {
    return selector === '.node' ? this.nodes : [];
  },
};
const outPort = { className: 'node-port out' };
const classSet = new Set();
const nodeEl = {
  dataset: { nodeId: 'node_1' },
  style: {
    values: {},
    setProperty(name, value) { this.values[name] = value; },
    removeProperty(name) { delete this.values[name]; },
  },
  classList: {
    add(...names) { names.forEach((name) => classSet.add(name)); },
    remove(...names) { names.forEach((name) => classSet.delete(name)); },
    toggle(name, value) { value ? classSet.add(name) : classSet.delete(name); },
  },
  getBoundingClientRect() {
    return { left: 100, right: 380, top: 80, bottom: 320, height: 240 };
  },
  querySelector(selector) {
    return selector === '.node-port.out' ? outPort : null;
  },
};
document.nodes = [nodeEl];

const hover = updatePortMagnet({ clientX: 408, clientY: 210 });
if (hover.nodeId !== 'node_1' || hover.side !== 'right') throw new Error('expected right-side magnet');
if (!classSet.has('port-magnet-right')) throw new Error('expected visual magnet state');
if (outputPortFromMagnet({ clientX: 408, clientY: 210 }) !== outPort) throw new Error('expected output port');
if (updatePortMagnet({ clientX: 408, clientY: 300 }) !== null) throw new Error('expected no far vertical magnet');
updatePortMagnet({ clientX: 408, clientY: 225 });
if (nodeEl.style.values['--port-magnet-y'] !== '12px') throw new Error('expected bounded vertical follow');
clearPortMagnet();
if (classSet.has('port-magnet-right')) throw new Error('expected cleared magnet state');
"""
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", code],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_port_geometry_anchors_edges_to_visible_button_center() -> None:
    code = r"""
import { nodePortWorldPoint } from './apps/studio/src/interaction/port-geometry.js';

const port = {
  getBoundingClientRect() {
    return { left: 390, top: 210, width: 22, height: 22 };
  },
};
globalThis.document = {
  querySelectorAll(selector) {
    if (selector !== '.node') return [];
    return [{
      dataset: { nodeId: 'node_1' },
      querySelector(inner) {
        return inner === '.node-port.out' ? port : null;
      },
    }];
  },
};
const point = nodePortWorldPoint(
  { id: 'node_1', x: 100, y: 120, w: 280, h: 240 },
  'out',
  { x: 10, y: 20, scale: 2 },
);
if (point.x !== 195.5 || point.y !== 100.5) throw new Error(`unexpected point ${JSON.stringify(point)}`);
"""
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", code],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_port_geometry_anchors_persistent_edges_to_node_frame_boundary() -> None:
    code = r"""
import { nodeFramePortWorldPoint } from './apps/studio/src/interaction/port-geometry.js';

const port = {
  getBoundingClientRect() {
    return { left: 390, top: 210, width: 22, height: 22 };
  },
};
globalThis.document = {
  querySelectorAll(selector) {
    if (selector !== '.node') return [];
    return [{
      dataset: { nodeId: 'node_1' },
      querySelector(inner) {
        return inner === '.node-port.out' ? port : null;
      },
    }];
  },
};
const point = nodeFramePortWorldPoint(
  { id: 'node_1', x: 100, y: 120, w: 280, h: 240 },
  'out',
  { x: 10, y: 20, scale: 2 },
);
if (point.x !== 380 || point.y !== 100.5) throw new Error(`unexpected point ${JSON.stringify(point)}`);
"""
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", code],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_add_node_menu_defaults_to_compact_collapsed_registry() -> None:
    source = (STUDIO_ROOT / "src" / "panels" / "add-node-menu.js").read_text(encoding="utf-8")
    styles = (STUDIO_ROOT / "styles" / "studio-interactions.css").read_text(encoding="utf-8")
    overlay = (STUDIO_ROOT / "src" / "overlay.js").read_text(encoding="utf-8")

    assert 'const QUICK_ACTION_IDS = ["node_text", "node_image", "node_video", "node_director"]' in source
    assert '"compact-create-menu"' in source
    assert '"advanced-create-list"' in source
    assert '"advanced-create-content"' in source
    assert "bindDynamicMenuPosition" in source
    assert ".compact-create-menu" in styles
    assert "max-height: min(560px, calc(100vh - 32px))" in styles
    assert "window.innerHeight - height - 8" in overlay


def test_media_preview_has_bounded_fill_contract() -> None:
    result_styles = (STUDIO_ROOT / "styles" / "node-result.css").read_text(encoding="utf-8")
    canvas_styles = (STUDIO_ROOT / "styles" / "canvas.css").read_text(encoding="utf-8")
    prompt_position = (STUDIO_ROOT / "src" / "prompt-bar-position.js").read_text(encoding="utf-8")

    for marker in (
        ".node.has-media-result .node-body",
        "min-height: 168px",
        "object-fit: cover",
    ):
        assert marker in result_styles
    assert ".node.type-image.has-media-result .node-body" in canvas_styles
    assert "padding: 0" in canvas_styles
    assert ".node.type-image.has-media-result .node-status.success" in canvas_styles
    assert "overlapWithNode" in prompt_position
    assert "chooseNonOverlappingY" in prompt_position
