from __future__ import annotations

from studio_static_helpers import STUDIO_ROOT, _source, _styles

def test_studio_v02_flow_native_surface_is_visible() -> None:
    source = _source()
    styles = _styles()

    for marker in (
        "STARTERS",
        "starter-card",
        "NODE_MENU_ORDER",
        "RESOURCE_ENTRIES",
        "drawer-tab",
        "asset-card",
        "asset-thumb",
        "asset-action",
    ):
        assert marker in source or marker in styles


def test_studio_mature_shell_exposes_algorithm_console_and_quick_start_rail() -> None:
    source = _source()
    styles = _styles()
    index = (STUDIO_ROOT / "index.html").read_text(encoding="utf-8")
    canvas_view = (STUDIO_ROOT / "src" / "canvas-view.js").read_text(encoding="utf-8")
    starter_rail = (STUDIO_ROOT / "src" / "canvas-starter-rail.js").read_text(encoding="utf-8")
    inspector = (STUDIO_ROOT / "src" / "panels" / "inspector-panel.js").read_text(encoding="utf-8")

    assert './styles/studio-mature-shell.css' in index
    assert './styles/studio-inspector-declutter.css' in index
    assert "algorithm-context-panel.js" in inspector
    assert "inspector-context-summary.js" in inspector
    assert "projectPipelineSection(state)" in inspector
    assert "algorithmConsoleSection(node)" in inspector
    assert "nodeContextSummaryText(node)" in inspector
    assert "projectReferenceSummaryText(state)" in (STUDIO_ROOT / "src" / "panels" / "inspector-context-summary.js").read_text(encoding="utf-8")
    assert "warningText(item)" in (STUDIO_ROOT / "src" / "panels" / "inspector-context-summary.js").read_text(encoding="utf-8")
    assert 'item.reason || item.warning_id || item.label || item.attribute' in (STUDIO_ROOT / "src" / "panels" / "inspector-context-summary.js").read_text(encoding="utf-8")
    assert "创作助手" in inspector
    assert 'panelHead("panel", "创作助手", "下一步")' in inspector
    assert "下一步行动" in inspector
    assert "本次参考摘要" in inspector
    assert "资产确认状态" in inspector
    assert "drawerLinks(store)" in inspector
    assert 'detailsSection("资产确认状态"' in inspector
    assert "detailsSection(\"输出记录\"" in inspector
    assert "nodeActionBrief(node)" in inspector
    assert "starterRailState(state)" in canvas_view
    assert 'starterRow.dataset.mode = rail.mode;' in canvas_view
    assert "shouldShowStarterRail" in starter_rail
    assert 'mode: empty ? "empty" : "quick-start"' in starter_rail
    for marker in (
        "CORE_ALGORITHMS",
        "上下文调度",
        "提示词优化",
        "请求投影",
        "视觉识别",
        "资产记忆",
        "漂移控制",
        "safeManifest",
    ):
        assert marker in source
    algorithm_panel = (STUDIO_ROOT / "src" / "panels" / "algorithm-context-panel.js").read_text(encoding="utf-8")
    assert 'title: "系统参考"' in algorithm_panel
    assert 'tag: "查看制作依据"' in algorithm_panel
    assert "生成时自动记录上下文、资产和证据" in algorithm_panel
    for marker in (
        ".algorithm-console",
        ".algorithm-disclosure",
        ".inspector-disclosure",
        ".inspector-drawer-links",
        ".algorithm-step-track",
        ".algorithm-call-summary",
        '#starter-row[data-mode="quick-start"]',
        "backdrop-filter: blur(18px)",
    ):
        assert marker in styles


def test_studio_asset_lifecycle_filter_separates_fixed_candidate_and_retired_assets() -> None:
    lifecycle = (STUDIO_ROOT / "src" / "asset-lifecycle.js").read_text(encoding="utf-8")
    drawer_assets = (STUDIO_ROOT / "src" / "panels" / "drawer-assets.js").read_text(encoding="utf-8")
    drawer = (STUDIO_ROOT / "src" / "panels" / "drawer.js").read_text(encoding="utf-8")
    store_state = (STUDIO_ROOT / "src" / "store-state.js").read_text(encoding="utf-8")
    styles = _styles()

    assert "ASSET_LIFECYCLE_FILTERS" in lifecycle
    assert "assetLifecycleState(asset)" in lifecycle
    assert "matchesAssetLifecycleFilter(asset, filter)" in lifecycle
    assert "assetLifecycleFilter(state, store)" in drawer_assets
    assert "state.ui.assetLifecycleFilter" in drawer_assets
    assert "state.ui.drawerSearch, state.ui.assetLifecycleFilter" in drawer
    assert 'assetLifecycleFilter: "all"' in store_state
    for label in ("全部", "已确认", "候选", "停用"):
        assert label in lifecycle
    for marker in (
        "asset-lifecycle-filter",
        "asset-lifecycle-badge",
        "lifecycle-fixed",
        "lifecycle-draft",
    ):
        assert marker in styles + drawer_assets


def test_studio_mature_shell_prevents_scroll_and_overlap_regressions() -> None:
    styles = _styles()
    inspector_shell = (STUDIO_ROOT / "styles" / "studio-inspector-declutter.css").read_text(encoding="utf-8")
    workbench = (STUDIO_ROOT / "styles" / "studio-workbench.css").read_text(encoding="utf-8")

    assert "#inspector" in inspector_shell
    assert "display: block;" in inspector_shell
    assert ".inspector-section" in inspector_shell
    assert "flex: none;" in inspector_shell
    assert ".project-hub" in workbench
    assert ".project-menu" in workbench
    assert "width: min(520px, calc(100vw - 56px));" in workbench
    assert "overflow-y: auto;" in workbench
    assert "scrollbar-width: thin;" in workbench
    assert ".modal {" in styles
    assert "overflow: hidden;" in styles


def test_studio_starter_row_uses_adaptive_grid_without_horizontal_scrollbar() -> None:
    shell = (STUDIO_ROOT / "styles" / "shell.css").read_text(encoding="utf-8")
    interactions = (STUDIO_ROOT / "styles" / "studio-interactions.css").read_text(encoding="utf-8")
    mature = (STUDIO_ROOT / "styles" / "studio-mature-shell.css").read_text(encoding="utf-8")
    combined = "\n".join((shell, interactions, mature))
    shell_starter_block = shell[shell.index("#starter-row {"):shell.index(".starter-card {")]
    interactions_starter_block = interactions[interactions.index("#starter-row {"):interactions.index(".starter-card {")]

    assert "grid-template-columns: repeat(5, minmax(0, 1fr));" in combined
    assert "#starter-row {\n  position: absolute;" in shell
    assert "overflow: hidden;" in shell
    assert "overflow: hidden;" in interactions
    assert "grid-template-columns: 1fr;" in shell
    assert "#starter-row[data-mode=\"quick-start\"]" in mature
    assert "width: auto;" in mature
    assert "overflow-x: auto;" not in shell_starter_block
    assert "overflow-x: auto;" not in interactions_starter_block
    assert "scrollbar-width:" not in interactions_starter_block


def test_studio_shell_supports_resizable_drawer_collapsible_inspector_and_no_select_chrome() -> None:
    index = (STUDIO_ROOT / "index.html").read_text(encoding="utf-8")
    base = (STUDIO_ROOT / "styles" / "base.css").read_text(encoding="utf-8")
    resize_css = (STUDIO_ROOT / "styles" / "drawer-resize.css").read_text(encoding="utf-8")
    collapse_css = (STUDIO_ROOT / "styles" / "inspector-collapse.css").read_text(encoding="utf-8")
    inspector_css = (STUDIO_ROOT / "styles" / "studio-inspector-declutter.css").read_text(encoding="utf-8")
    drawer = (STUDIO_ROOT / "src" / "panels" / "drawer.js").read_text(encoding="utf-8")
    inspector = (STUDIO_ROOT / "src" / "panels" / "inspector-panel.js").read_text(encoding="utf-8")
    state = (STUDIO_ROOT / "src" / "store-state.js").read_text(encoding="utf-8")

    assert './styles/drawer-resize.css' in index
    assert './styles/inspector-collapse.css' in index
    assert "drawerWidth" in state
    assert "bindDrawerResize" in drawer
    assert "drawer-resize-handle" in drawer
    assert "setProperty(\"--drawer-w\"" in drawer
    assert "stored || state.ui.drawerWidth || 196" in drawer
    assert ".drawer-resize-handle" in resize_css
    assert "cursor: ew-resize" in resize_css
    assert "inspectorOpen" in state
    assert "inspector-collapse-toggle" in inspector
    assert "s.ui.inspectorOpen = s.ui.inspectorOpen === false" in inspector
    assert "#inspector.is-collapsed" in collapse_css
    assert "right: 16px;" in inspector_css
    assert "user-select: none;" in base
    assert "input, textarea, select, [contenteditable=\"true\"], .selectable-text" in base
    assert "user-select: text;" in base


def test_studio_ports_support_upstream_and_downstream_node_creation() -> None:
    canvas_connection = (STUDIO_ROOT / "src" / "canvas-connection.js").read_text(encoding="utf-8")
    canvas_input = (STUDIO_ROOT / "src" / "canvas-input.js").read_text(encoding="utf-8")
    add_menu = (STUDIO_ROOT / "src" / "panels" / "add-node-menu.js").read_text(encoding="utf-8")

    assert "findPortAtPoint" in canvas_connection
    assert "startConnectSession(store, nodeEl.dataset.nodeId, portBtn.dataset.port, e)" in canvas_input
    assert 'session.direction === "upstream"' in canvas_connection
    assert "openReferenceMenu(store, runtime, node, portEl, { direction: session.direction })" in canvas_connection
    assert 'direction === "upstream"' in add_menu


def test_studio_frontend_structure_splits_entrypoint_helpers() -> None:
    index = (STUDIO_ROOT / "index.html").read_text(encoding="utf-8")
    main = (STUDIO_ROOT / "src" / "main.js").read_text(encoding="utf-8")
    store = (STUDIO_ROOT / "src" / "store.js").read_text(encoding="utf-8")
    node_actions = (STUDIO_ROOT / "src" / "node-actions.js").read_text(encoding="utf-8")
    keyframe_actions = (STUDIO_ROOT / "src" / "node-keyframe-actions.js").read_text(encoding="utf-8")
    video_actions = (STUDIO_ROOT / "src" / "node-video-actions.js").read_text(encoding="utf-8")

    for path in (
        "src/studio-project-session.js",
        "src/studio-project-controller.js",
        "src/store-state.js",
        "src/store-persistence.js",
        "src/node-generation-restore.js",
        "src/node-keyframe-actions.js",
        "src/node-video-actions.js",
        "src/canvas-edges.js",
        "src/interaction/port-geometry.js",
        "styles/canvas-edges.css",
    ):
        assert (STUDIO_ROOT / path).is_file()

    assert './styles/canvas-edges.css' in index
    assert "from \"./studio-project-session.js\"" in main
    assert "from \"./studio-project-controller.js\"" in main
    assert "from \"./store-persistence.js\"" in store
    assert "from \"./store-state.js\"" in store
    assert "from \"./node-generation-restore.js\"" not in node_actions
    assert "from \"./node-generation-restore.js\"" in keyframe_actions
    assert "from \"./node-generation-restore.js\"" in video_actions
    assert 'from "./canvas-edges.js"' in (STUDIO_ROOT / "src" / "canvas-view.js").read_text(encoding="utf-8")
    assert 'from "./canvas-edges.js"' in (STUDIO_ROOT / "src" / "canvas-connection.js").read_text(encoding="utf-8")
    assert len(store.splitlines()) <= 220
    assert len((STUDIO_ROOT / "src" / "canvas-view.js").read_text(encoding="utf-8").splitlines()) <= 300
    assert len((STUDIO_ROOT / "src" / "canvas-edges.js").read_text(encoding="utf-8").splitlines()) <= 140
    assert len((STUDIO_ROOT / "styles" / "canvas.css").read_text(encoding="utf-8").splitlines()) <= 300
    assert len((STUDIO_ROOT / "styles" / "canvas-edges.css").read_text(encoding="utf-8").splitlines()) <= 140
    assert len((STUDIO_ROOT / "src" / "studio-project-session.js").read_text(encoding="utf-8").splitlines()) <= 90
    assert len((STUDIO_ROOT / "src" / "studio-project-controller.js").read_text(encoding="utf-8").splitlines()) <= 500
    assert len(keyframe_actions.splitlines()) <= 180
    assert len(video_actions.splitlines()) <= 300
    assert len(node_actions.splitlines()) <= 140
    assert len(main.splitlines()) <= 500
    assert len((STUDIO_ROOT / "src" / "node-generation-restore.js").read_text(encoding="utf-8").splitlines()) <= 80


def test_studio_layout_and_director_prompt_link_are_explicit() -> None:
    source = _source()
    styles = _styles()

    for marker in ("drawer-open", "compact-project", "DIRECTOR_OBJECTS", "top_down_2d", "director-board"):
        assert marker in source
    for marker in ("#topbar.drawer-open", "left: var(--drawer-w)", "director-edge", "reference-edge", "edge-label"):
        assert marker in styles
    for marker in ("director_setup", "director_summary", "relation_type"):
        assert marker in source
    assert "max-height: none" in styles


def test_studio_mobile_shell_keeps_topbar_and_starters_inside_canvas() -> None:
    styles = (STUDIO_ROOT / "styles" / "shell.css").read_text(encoding="utf-8")

    assert "--drawer-w: min(156px, 40vw);" in styles
    assert "width: clamp(88px, calc(100vw - var(--drawer-w) - 88px), 146px);" in styles
    assert "#topbar.drawer-open .topbar-right { display: none; }" in styles
    assert "left: calc(var(--drawer-w) + (100vw - var(--drawer-w)) / 2);" in styles
    assert "top: 50%;" in styles
    assert "width: calc(100vw - var(--drawer-w) - 24px);" in styles
    assert "flex-direction: column;" in styles
    assert "overflow-x: visible;" in styles
    assert "max-height: 42vh;" in styles


def test_director_shell_uses_active_ids_and_confirmed_append_only() -> None:
    director_data = (STUDIO_ROOT / "src" / "director-data.js").read_text(encoding="utf-8")
    director_shell = (STUDIO_ROOT / "src" / "panels" / "director-shell.js").read_text(encoding="utf-8")
    director_render = (STUDIO_ROOT / "src" / "panels" / "director-shell-render.js").read_text(encoding="utf-8")
    director_fields = (STUDIO_ROOT / "src" / "panels" / "director-fields.js").read_text(encoding="utf-8")

    assert "activeCameraId" in director_data
    assert "activeSubjectIds" in director_data
    assert "visual_asset_id" in director_data
    assert "directorProductionPlan" in director_data
    assert "镜头目标" in director_data
    assert "主体调度" in director_data
    assert "Array.isArray(value) ? clone(value) : clone(fallback)" in director_data
    assert 'from "./director-shell-render.js"' in director_shell
    assert "createDirectorShellFrame" in director_render
    assert "renderDirectorObjectList" in director_render
    assert "renderDirectorBoard" in director_render
    assert "renderDirectorIntentPreview" in director_render
    assert "director-production-plan" in director_render
    assert "生产包" in director_render
    assert "confirmDirectorPromptAppend" in director_shell
    assert "window.confirm" not in director_shell
    assert "current.prompt = prompt" not in director_shell
    assert "join(\"\\n\\n\")" in director_shell
    assert "directorVisualAssetIds" in director_shell
    assert "绑定角色资产 ID" in director_fields
    assert len(director_shell.splitlines()) <= 300
    assert len(director_render.splitlines()) <= 180


def test_prompt_optimizer_sources_stay_product_facing() -> None:
    source = _source()

    for label in ("影视结构", "项目风格", "角色/场景设定", "导演台布置"):
        assert label in source
    for forbidden in ("权重", "知识库", "provider raw", "候选记忆"):
        assert forbidden not in source
