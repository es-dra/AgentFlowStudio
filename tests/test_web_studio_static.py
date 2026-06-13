from __future__ import annotations

from pathlib import Path


STUDIO_ROOT = Path("apps/studio")


def _source() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in STUDIO_ROOT.rglob("*.js"))


def _styles() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in STUDIO_ROOT.rglob("*.css"))


def test_studio_static_entrypoint_is_the_only_user_frontend() -> None:
    assert STUDIO_ROOT.exists()
    assert not Path("apps/workbench").exists()
    assert not Path("apps/web").exists()

    index = (STUDIO_ROOT / "index.html").read_text(encoding="utf-8")
    assert './src/main.js' in index
    assert './styles/director.css' in index
    assert "/workbench" not in index


def test_studio_disallows_native_blocking_dialogs_and_global_canvas_fallback() -> None:
    source = _source()
    store_source = (STUDIO_ROOT / "src" / "store.js").read_text(encoding="utf-8")
    env_example = Path(".env.example").read_text(encoding="utf-8")

    for forbidden in ("window.prompt(", "window.confirm(", "window.alert("):
        assert forbidden not in source
    assert '|| localStorage.getItem(STORAGE_KEY)' not in store_source
    assert '|| localStorage.getItem(LEGACY_STORAGE_KEY)' not in store_source
    assert "migrateLegacyCanvasStorage" in store_source
    assert "localStorage.removeItem(STORAGE_KEY)" in store_source
    assert "localStorage.removeItem(LEGACY_STORAGE_KEY)" in store_source
    assert 'return { source: "stale", projectId: targetProjectId }' in store_source
    assert "hasStudioMeta(remoteState)" in store_source
    assert 'next.type === "video" && next.params.lastVideoPreviewUrl' in store_source
    assert '!String(next.previewUrl).includes("/video-generations/")' in store_source
    main_source = (STUDIO_ROOT / "src" / "main.js").read_text(encoding="utf-8")
    assert "syncCurrentProjectMetaFromSummaries" in main_source
    assert "const currentId = runtime.projectId || state.meta.projectId;" in main_source
    assert 'input.type = "text";' in main_source
    drawer_source = (STUDIO_ROOT / "src" / "panels" / "drawer.js").read_text(encoding="utf-8")
    assert "state.meta.projectId, state.meta.projectName, state.meta.canvasName" in drawer_source
    canvas_source = (STUDIO_ROOT / "src" / "canvas-view.js").read_text(encoding="utf-8")
    assert '!["image", "video"].includes(node.type)' in canvas_source
    prompt_bar_source = (STUDIO_ROOT / "src" / "prompt-bar.js").read_text(encoding="utf-8")
    assert 'node.type === "video" || node.type === "script"' in prompt_bar_source
    assert "AFS_ALLOW_REMOTE_IMAGE" in env_example


def test_studio_user_surface_does_not_reintroduce_old_workbench_terms() -> None:
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for suffix in ("*.html", "*.css", "*.js")
        for path in STUDIO_ROOT.rglob(suffix)
    )
    for term in ("/workbench", "LibTV", "memory-workbench", "provider raw"):
        assert term not in combined


def test_studio_keeps_flow_native_canvas_controls() -> None:
    source = _source()

    for marker in (
        "openAddNodeMenu",
        "openOptimizer",
        "director",
        "prompt-optimizations",
        "keyframe-generations",
        "image-assets",
        "uploadNodeImage",
        "collectConnectedImageAssetRefs",
        "connected_reference_nodes",
        "candidate_previews",
        "reusable_image_assets",
        "mergeImageAssets",
        "node-preview-img",
        "node-preview-video",
        "resizeNodeForImagePreview",
        "previewAspectRatio",
        "has-image-preview",
        "startNodeGeneration",
        "studio-state",
        "loadStudioState",
        "saveStudioState",
        "createNode",
        "undo()",
        "redo()",
    ):
        assert marker in source


def test_studio_asset_context_workflow_is_single_canvas() -> None:
    source = _source()
    styles = _styles()

    for marker in (
        "buildContextSubgraph",
        "context_subgraph",
        "runtime_work_mode",
        "temporary_lock_overrides",
        "visual_asset_ids",
        "promoteVisualAsset",
        "visualAssets",
        "fix-visual-asset",
        "context_bundle",
        "lastContextBundle",
        "connectNamedAssetToTarget",
        "connect-named-asset",
        "temporary-unlock",
        "temporaryLockOverrides",
        "uniqueLockWarnings",
        "visual-asset-panel",
    ):
        assert marker in source
    for marker in ("opt-context-assets", "opt-inline-btn", "context-bundle-summary", "visual-asset-panel"):
        assert marker in styles
    assert "mode-tab asset_capture" not in source
    assert "mode-tab context_generate" not in source


def test_image_node_prompt_bar_keeps_only_model_optimize_and_generate_controls() -> None:
    prompt_bar = (STUDIO_ROOT / "src" / "prompt-bar.js").read_text(encoding="utf-8")
    node_menu = (STUDIO_ROOT / "src" / "panels" / "node-menu.js").read_text(encoding="utf-8")
    node_actions = (STUDIO_ROOT / "src" / "node-actions.js").read_text(encoding="utf-8")

    assert "openModelPopover" in prompt_bar
    assert "openOptimizer" in prompt_bar
    assert "startNodeGeneration" in prompt_bar
    for removed in (
        "openImageSpecPopover",
        "openCameraPopover",
        "IMAGE_COUNTS",
        "IMAGE_QUALITY",
        "IMAGE_RESOLUTION",
        "IMAGE_RATIOS",
    ):
        assert removed not in prompt_bar
    assert "isRemoteVideoModel" in prompt_bar
    assert "pollNodeVideoGeneration" in prompt_bar
    assert "runPromptBarGeneration" in prompt_bar
    assert "声音" not in prompt_bar
    assert 'send.title = "继续轮询"' in prompt_bar
    assert "isPromptTextEditing" in prompt_bar
    assert '["TEXTAREA", "INPUT"].includes' in prompt_bar
    canvas_view = (STUDIO_ROOT / "src" / "canvas-view.js").read_text(encoding="utf-8")
    assert '!["image", "video"].includes(node.type)' in canvas_view
    assert "bar-cost" not in prompt_bar
    assert "当前版本仅图片节点支持真实生成" in prompt_bar
    assert "uploadNodeImage" in node_menu
    assert "setNodeVideoFrame" in node_menu
    assert "pollNodeVideoGeneration" in node_menu
    assert "openPositionNear" in (STUDIO_ROOT / "src" / "panels" / "add-node-menu.js").read_text(encoding="utf-8")
    assert "syncRunAction" in canvas_view
    assert 'dataset.action = "video-poll"' in canvas_view
    assert "pollNodeVideoGeneration" in (STUDIO_ROOT / "src" / "canvas-input.js").read_text(encoding="utf-8")
    assert node_actions.count("restoreCancelledGeneration(store, node.id, previousNodeState);") == 2
    assert node_actions.count("await store.flushRuntimeSave?.();\n      return;") >= 2
    drawer_source = (STUDIO_ROOT / "src" / "panels" / "drawer.js").read_text(encoding="utf-8")
    assert 'asset.kind === "visual_asset" && asset.asset_type === "character"' in drawer_source
    assert 'asset.kind === "character_asset"' in drawer_source
    assert 'character_asset: "人物资产"' in drawer_source
    assert "asset.preview_url" in drawer_source
    assert "node.params.visualAssets" in drawer_source
    assert "visualAssetRef" in drawer_source
    assert "setVideoFrameFromAsset" in drawer_source
    assert "firstFrameImageAssetId" in drawer_source
    assert "设为首帧" in drawer_source
    assert "retireVisualAsset" in drawer_source
    assert "applyRetiredAsset" in drawer_source
    assert "确认退役" in drawer_source
    assert "asset.runtime_status" in drawer_source
    assert "上传/替换参考图" in node_menu
    assert "VIDEO_MODES" not in prompt_bar
    assert "VIDEO_COUNTS" not in prompt_bar
    assert "mode-tabs" not in prompt_bar


def test_studio_hardening_static_contract_markers() -> None:
    source = _source()
    prompt_bar = (STUDIO_ROOT / "src" / "prompt-bar.js").read_text(encoding="utf-8")
    optimizer_contract = (STUDIO_ROOT / "src" / "optimizer-contract.js").read_text(encoding="utf-8")
    optimizer = (STUDIO_ROOT / "src" / "optimizer.js").read_text(encoding="utf-8")
    visual_asset_panel = (STUDIO_ROOT / "src" / "panels" / "visual-asset-panel.js").read_text(encoding="utf-8")
    shortcuts = (STUDIO_ROOT / "src" / "panels" / "shortcuts-panel.js").read_text(encoding="utf-8")

    assert "lastOptimizedPromptPlain" in source
    assert "user_prompt_plain" in optimizer_contract
    assert "referenceDepth" in optimizer_contract
    assert "costHop" in optimizer_contract
    assert "degraded_to_signature_over_limit" in source
    assert "superseded_by_newer_label_version" in source
    assert "不采用" in visual_asset_panel
    assert "asset_fix" not in visual_asset_panel
    assert "fix visual asset" not in source
    assert "未引用 · 可连线" in optimizer
    assert '["Ctrl", "L"]' in shortcuts
    assert '["Ctrl", "D"]' in shortcuts
    assert "?" in shortcuts
    assert "send.disabled" in prompt_bar


def test_visual_asset_panel_prefills_feature_card_from_node_context() -> None:
    panel = (STUDIO_ROOT / "src" / "panels" / "visual-asset-panel.js").read_text(encoding="utf-8")
    defaults = (STUDIO_ROOT / "src" / "panels" / "visual-asset-defaults.js").read_text(encoding="utf-8")
    assert "sectionText" in defaults
    assert "inferIdentity" in defaults
    assert "inferFace" in defaults
    assert "uniqueTextParts" in defaults

    assert "visualAssetDefaults" in panel
    assert "data-card" in panel
    assert "短发" in defaults
    assert "保持参考图人物身份和脸部辨识度" in defaults


def test_asset_drawer_does_not_seed_placeholder_assets_or_duplicate_runtime_assets() -> None:
    store = (STUDIO_ROOT / "src" / "store.js").read_text(encoding="utf-8")
    main = (STUDIO_ROOT / "src" / "main.js").read_text(encoding="utf-8")

    assert "seedAssets()" not in store
    for placeholder in ("asset_director_seed", "asset_character_seed", "asset_keyframe_seed"):
        assert placeholder not in store
    assert "assetStableKey" in main
    assert "mergeAsset" in main
    assert "visual_asset_id: asset.asset_id" in main
    assert "visualAssetPreviewUrl" in main
    assert "image_asset_refs" in main
    assert "uploaded_images" in (STUDIO_ROOT / "src" / "optimizer-contract.js").read_text(encoding="utf-8")


def test_studio_model_picker_only_exposes_current_mvp_models() -> None:
    source = (STUDIO_ROOT / "src" / "presets" / "models.js").read_text(encoding="utf-8")

    assert "提示词优化" in source
    assert "MiniMax image-01" in source
    assert 'return Boolean(findModel("image", modelId).providerServiceId);' in source
    assert 'return Boolean(findModel("video", modelId).providerServiceId);' in source
    assert "local-creative-agent" not in source
    assert "remote_optimizer_required" in _source()
    assert 'providerServiceId: "minimax_image"' in source
    for retired in ("Midjourney", "Seedream", "Seedance", "Qwen 3", "Lib Video", "Lib Image"):
        assert retired not in source


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


def test_director_shell_uses_active_ids_and_confirmed_append_only() -> None:
    director_data = (STUDIO_ROOT / "src" / "director-data.js").read_text(encoding="utf-8")
    director_shell = (STUDIO_ROOT / "src" / "panels" / "director-shell.js").read_text(encoding="utf-8")
    director_fields = (STUDIO_ROOT / "src" / "panels" / "director-fields.js").read_text(encoding="utf-8")

    assert "activeCameraId" in director_data
    assert "activeSubjectIds" in director_data
    assert "visual_asset_id" in director_data
    assert "Array.isArray(value) ? clone(value) : clone(fallback)" in director_data
    assert "confirmDirectorPromptAppend" in director_shell
    assert "window.confirm" not in director_shell
    assert "current.prompt = prompt" not in director_shell
    assert "join(\"\\n\\n\")" in director_shell
    assert "directorVisualAssetIds" in director_shell
    assert "绑定人物资产 ID" in director_fields


def test_prompt_optimizer_sources_stay_product_facing() -> None:
    source = _source()

    for label in ("影视结构", "项目风格", "角色/场景设定", "导演台布置"):
        assert label in source
    for forbidden in ("权重", "知识库", "provider raw", "候选记忆"):
        assert forbidden not in source
