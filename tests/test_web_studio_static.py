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
    assert node_actions.count("restoreCancelledGeneration(store, node.id, previousNodeState);") == 3
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


def test_loop003_qal003_001_fixed_asset_submit_interlock_has_regression_markers() -> None:
    node_actions = (STUDIO_ROOT / "src" / "node-actions.js").read_text(encoding="utf-8")
    optimizer_contract = (STUDIO_ROOT / "src" / "optimizer-contract.js").read_text(encoding="utf-8")
    runtime_client = (STUDIO_ROOT / "src" / "runtime-client.js").read_text(encoding="utf-8")

    assert "preflightKeyframe" in runtime_client
    assert "preflightVideo" in runtime_client
    assert "prepareGenerationRequest" in node_actions
    assert "showCarryConfirmModal" in node_actions
    assert "preflight_token" in node_actions
    assert "temporary_asset_exclusions" in node_actions
    assert "temporary_asset_exclusions" in optimizer_contract
    assert "asset_conflicts" in node_actions
    assert "error.status = response.status" in runtime_client
    assert "error.route = route" in runtime_client
    assert "missingPreflightRouteError" in node_actions
    assert "Runtime Service version is stale or not started from this branch" in node_actions
    assert "Restart the 8790 Runtime Service and retry" in node_actions


def test_keyframe_generation_polls_async_runtime_jobs_without_provider_jargon() -> None:
    runtime_client = (STUDIO_ROOT / "src" / "runtime-client.js").read_text(encoding="utf-8")
    node_actions = (STUDIO_ROOT / "src" / "node-actions.js").read_text(encoding="utf-8")

    assert "pollKeyframe(jobId)" in runtime_client
    assert "/keyframe-generations/${encodeURIComponent(jobId)}/poll" in runtime_client
    assert "pollNodeKeyframeGeneration" in node_actions
    assert "pollKeyframeUntilTerminal" in node_actions
    assert "lastKeyframeJobId" in node_actions
    assert "MiniMax keyframe request failed" not in node_actions
    for forbidden in ("Codex", "codex", "handoff", "request.json", "codex_image_job"):
        assert forbidden not in node_actions


def test_video_revision_and_fail_closed_submit_markers() -> None:
    source = _source()
    runtime_client = (STUDIO_ROOT / "src" / "runtime-client.js").read_text(encoding="utf-8")
    node_actions = (STUDIO_ROOT / "src" / "node-actions.js").read_text(encoding="utf-8")
    node_menu = (STUDIO_ROOT / "src" / "panels" / "node-menu.js").read_text(encoding="utf-8")
    inspector = (STUDIO_ROOT / "src" / "asset-reference-inspector.js").read_text(encoding="utf-8")

    assert "preflightVideoRevision" in runtime_client
    assert "generateVideoRevision" in runtime_client
    assert "/video-revisions/preflight" in runtime_client
    assert "/video-revisions" in runtime_client
    assert "staleRuntimeRouteMessage" in runtime_client
    assert "error.status = response.status" in runtime_client
    assert "Restart the 8790 Runtime Service" in runtime_client
    assert "unconnectedLabelMatchedAssets" in node_actions
    assert "label_matched" in inspector
    assert "named_asset_not_connected_fail_closed" in node_actions
    assert "startRemoteVideoRevision" in node_actions
    assert "videoRevision" in node_actions
    assert "AFS_ENABLE_EXPERIMENTAL_VIDEO_REVISION" in node_actions
    assert "enableVideoRevisionDraft" in source
    assert "video-revision-draft" in node_menu


def test_mvp_experience_hardening_carry_chain_and_asset_inspector_markers() -> None:
    summary = (STUDIO_ROOT / "src" / "asset-reference-summary.js")
    inspector = (STUDIO_ROOT / "src" / "asset-reference-inspector.js")
    canvas_view = (STUDIO_ROOT / "src" / "canvas-view.js").read_text(encoding="utf-8")
    result_view = (STUDIO_ROOT / "src" / "node-result-view.js").read_text(encoding="utf-8")
    optimizer = (STUDIO_ROOT / "src" / "optimizer.js").read_text(encoding="utf-8")
    node_actions = (STUDIO_ROOT / "src" / "node-actions.js").read_text(encoding="utf-8")
    styles = _styles()

    assert summary.is_file()
    assert inspector.is_file()
    summary_source = summary.read_text(encoding="utf-8")
    inspector_source = inspector.read_text(encoding="utf-8")
    assert "import { assetsFromNode, carryChainItems" in canvas_view
    assert "import { assetTypeLabel, assetLabel, subjectSuffix" in result_view
    assert "carry-chain-strip" in canvas_view
    assert "carry-chain-chip" in canvas_view
    assert "lastContextBundle" in canvas_view
    assert "visualAssets" in canvas_view
    assert "MAX_CARRY_CHAIN_ITEMS" in summary_source
    assert "function buildAssetReferenceActions" in inspector_source
    assert "buildAssetReferenceActions" in optimizer
    assert "buildAssetReferenceActions" in node_actions
    assert "named_asset_not_connected_fail_closed" in node_actions
    assert "connect-named-asset" in optimizer
    assert "carry-chain-strip" in styles
    assert "carry-chain-chip.invalid" in styles


def test_mvp_experience_hardening_video_status_and_feedback_markers() -> None:
    feedback = STUDIO_ROOT / "src" / "quality-feedback.js"
    node_actions = (STUDIO_ROOT / "src" / "node-actions.js").read_text(encoding="utf-8")
    node_menu = (STUDIO_ROOT / "src" / "panels" / "node-menu.js").read_text(encoding="utf-8")
    runtime_client = (STUDIO_ROOT / "src" / "runtime-client.js").read_text(encoding="utf-8")
    result_view = (STUDIO_ROOT / "src" / "node-result-view.js").read_text(encoding="utf-8")
    main = (STUDIO_ROOT / "src" / "main.js").read_text(encoding="utf-8")
    styles = _styles()

    assert feedback.is_file()
    feedback_source = feedback.read_text(encoding="utf-8")
    assert "studio_quality_feedback" in feedback_source
    assert "identity_similarity" in feedback_source
    assert "wardrobe_consistency" in feedback_source
    assert "scene_continuity" in feedback_source
    assert "text_or_watermark" in feedback_source
    assert "target_change_success" in feedback_source
    assert "drift_notes" in feedback_source
    assert "raw_evidence_not_memory" in feedback_source
    assert "safe_preview_ref" in feedback_source
    assert "sanitizeFeedbackText" in feedback_source
    assert "prompt_text" not in feedback_source
    assert "node?.previewUrl" in feedback_source
    assert "preview_url" not in feedback_source
    assert "recordFeedback(feedback)" in runtime_client
    assert 'return requestJson("/feedback"' in runtime_client
    assert "afs:studio-quality-feedback" in result_view
    assert "qualityFeedbackView" in result_view
    assert "handleQualityFeedback" in main
    assert "runtime.recordFeedback" in main
    assert "cancelNodeVideoGeneration" in node_actions
    assert "cancelVideo(jobId)" in node_actions
    assert "cancelled_local_only" in node_actions
    assert "厂商侧任务" in node_actions
    assert "停止计费" in node_actions
    assert "本地取消轮询" in node_menu
    assert "node-status cancelled" in node_actions or "node-status cancelled" in (STUDIO_ROOT / "src" / "canvas-view.js").read_text(encoding="utf-8")
    assert "quality-feedback" in styles
    assert "node-status.cancelled" in styles


def test_runtime_client_uses_runtime_port_when_studio_is_served_from_dev_port() -> None:
    runtime_client = (STUDIO_ROOT / "src" / "runtime-client.js").read_text(encoding="utf-8")

    assert 'const FALLBACK_BASE_URL = "http://127.0.0.1:8790"' in runtime_client
    assert 'const RUNTIME_BASE_STORAGE_KEY = "afs_runtime_base_url"' in runtime_client
    assert 'current.port !== "8790"' in runtime_client
    assert "return FALLBACK_BASE_URL;" in runtime_client
    assert "explicitRuntimeBaseUrl" in runtime_client
    assert "normalizeRuntimeBaseUrl" in runtime_client
    assert "isLocalHost(url.hostname)" in runtime_client


def test_loop003_qal003_002_generated_image_promotion_entries_have_regression_markers() -> None:
    canvas_view = (STUDIO_ROOT / "src" / "canvas-view.js").read_text(encoding="utf-8")
    drawer = (STUDIO_ROOT / "src" / "panels" / "drawer.js").read_text(encoding="utf-8")
    node_actions = (STUDIO_ROOT / "src" / "node-actions.js").read_text(encoding="utf-8")
    visual_asset_panel = (STUDIO_ROOT / "src" / "panels" / "visual-asset-panel.js").read_text(encoding="utf-8")

    assert 'data-action="fix-visual-asset"' in canvas_view
    assert "fixNodeVisualAsset" in node_actions
    assert "candidate_previews" in node_actions
    assert "reusable_image_assets" in node_actions
    assert 'initialAssetType: assetType' in drawer
    assert 'initialAssetType = "character"' in visual_asset_panel


def test_loop003_qal003_003_asset_detail_reads_runtime_and_exposes_node_actions() -> None:
    runtime_client = (STUDIO_ROOT / "src" / "runtime-client.js").read_text(encoding="utf-8")
    asset_detail = (STUDIO_ROOT / "src" / "panels" / "asset-detail-popover.js").read_text(encoding="utf-8")
    canvas_input = (STUDIO_ROOT / "src" / "canvas-input.js").read_text(encoding="utf-8")
    drawer = (STUDIO_ROOT / "src" / "panels" / "drawer.js").read_text(encoding="utf-8")

    assert "getVisualAsset(assetId)" in runtime_client
    assert "runtime.getVisualAsset(assetId)" in asset_detail
    assert "removeAssetFromSelectedNode" in asset_detail
    assert "excludeAssetForNextRun" in asset_detail
    assert "temporaryAssetExclusions" in asset_detail
    assert "openAssetDetailPopover(store, runtime" in canvas_input
    assert "openAssetDetailPopover(store, runtime" in drawer


def test_loop003_qal003_004_recent_or_current_projects_are_not_hidden_by_filter() -> None:
    main = (STUDIO_ROOT / "src" / "main.js").read_text(encoding="utf-8")

    assert "RECENT_PROJECTS_KEY" in main
    assert "rememberProject" in main
    assert "recentProjectIds" in main
    assert "item.project_id === currentId || recent.includes(item.project_id)" in main
    assert "hiddenProjectCount" in main


def test_loop003_qal003_005_kling_sound_control_stays_hidden_without_descriptor_support() -> None:
    prompt_bar = (STUDIO_ROOT / "src" / "prompt-bar.js").read_text(encoding="utf-8")
    specs = (STUDIO_ROOT / "src" / "presets" / "specs.js").read_text(encoding="utf-8")

    assert "VIDEO_SOUND" not in prompt_bar
    assert "VIDEO_SOUND" not in specs
    assert "videoSpecLabel" in specs
    assert "spec.sound" not in specs


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
