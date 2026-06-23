from __future__ import annotations

from pathlib import Path

from studio_static_helpers import STUDIO_ROOT, _source, _styles

def test_studio_hardening_static_contract_markers() -> None:
    source = _source()
    prompt_bar = (STUDIO_ROOT / "src" / "prompt-bar.js").read_text(encoding="utf-8")
    optimizer_contract = (STUDIO_ROOT / "src" / "optimizer-contract.js").read_text(encoding="utf-8")
    optimizer = (STUDIO_ROOT / "src" / "optimizer.js").read_text(encoding="utf-8")
    visual_asset_panel = (STUDIO_ROOT / "src" / "panels" / "visual-asset-panel.js").read_text(encoding="utf-8")
    visual_asset_render = (STUDIO_ROOT / "src" / "panels" / "visual-asset-panel-render.js").read_text(encoding="utf-8")
    shortcuts = (STUDIO_ROOT / "src" / "panels" / "shortcuts-panel.js").read_text(encoding="utf-8")

    assert "lastOptimizedPromptPlain" in source
    assert "user_prompt_plain" in optimizer_contract
    assert "referenceDepth" in optimizer_contract
    assert "costHop" in optimizer_contract
    assert "degraded_to_signature_over_limit" in source
    assert "superseded_by_newer_label_version" in source
    assert "不采用" in visual_asset_render
    assert "asset_fix" not in visual_asset_panel
    assert "fix visual asset" not in source
    assert "未引用 · 可连线" in optimizer
    assert '["Ctrl", "L"]' in shortcuts
    assert '["Ctrl", "D"]' in shortcuts
    assert "?" in shortcuts
    assert "send.disabled" in prompt_bar


def test_visual_asset_panel_prefills_feature_card_from_node_context() -> None:
    panel = (STUDIO_ROOT / "src" / "panels" / "visual-asset-panel.js").read_text(encoding="utf-8")
    render = (STUDIO_ROOT / "src" / "panels" / "visual-asset-panel-render.js").read_text(encoding="utf-8")
    defaults = (STUDIO_ROOT / "src" / "panels" / "visual-asset-defaults.js").read_text(encoding="utf-8")
    assert "sectionText" in defaults
    assert "inferIdentity" in defaults
    assert "inferFace" in defaults
    assert "uniqueTextParts" in defaults

    assert "visualAssetDefaults" in panel
    assert 'from "./visual-asset-panel-render.js"' in panel
    assert "renderVisualAssetPanel" in render
    assert "lockChipsForAssetType" in render
    assert "data-card" in render
    assert len(panel.splitlines()) <= 300
    assert len(render.splitlines()) <= 220
    assert "角色资产" in defaults
    assert "动物主体" in defaults
    assert "拟人化或服装需由用户明确指定" in defaults
    assert "人物/主体" in defaults


def test_asset_drawer_does_not_seed_placeholder_assets_or_duplicate_runtime_assets() -> None:
    store = (STUDIO_ROOT / "src" / "store.js").read_text(encoding="utf-8")
    main = (STUDIO_ROOT / "src" / "main.js").read_text(encoding="utf-8")
    runtime_asset_sync = (STUDIO_ROOT / "src" / "runtime-asset-sync.js").read_text(encoding="utf-8")

    assert "seedAssets()" not in store
    for placeholder in ("asset_director_seed", "asset_character_seed", "asset_keyframe_seed"):
        assert placeholder not in store
    assert 'from "./runtime-asset-sync.js"' in main
    assert "assetStableKey" in runtime_asset_sync
    assert "mergeAsset" in runtime_asset_sync
    assert "visual_asset_id: asset.asset_id" in runtime_asset_sync
    assert "visualAssetPreviewUrl" in runtime_asset_sync
    assert "image_asset_refs" in runtime_asset_sync
    assert "uploaded_images" in (STUDIO_ROOT / "src" / "optimizer-contract.js").read_text(encoding="utf-8")


def test_studio_model_picker_only_exposes_current_mvp_models() -> None:
    source = (STUDIO_ROOT / "src" / "presets" / "models.js").read_text(encoding="utf-8")
    optimizer_contract = (STUDIO_ROOT / "src" / "optimizer-contract.js").read_text(encoding="utf-8")
    main = (STUDIO_ROOT / "src" / "main.js").read_text(encoding="utf-8")
    visual_asset_panel = (STUDIO_ROOT / "src" / "panels" / "visual-asset-panel.js").read_text(encoding="utf-8")

    assert "提示词优化" in source
    assert "Image2" in source
    assert 'return Boolean(findModel("image", modelId).providerServiceId);' in source
    assert 'return Boolean(findModel("video", modelId).providerServiceId);' in source
    assert "local-creative-agent" not in source
    assert "remote_optimizer_required" in _source()
    assert 'providerServiceId: "codex_image"' in source
    assert 'llmProvider: "prompt_optimizer"' in source
    assert 'llm_provider: "prompt_optimizer"' in optimizer_contract
    assert 'provider_service_id: "vision_image"' in visual_asset_panel
    assert 'provider_service_id: "vision_video"' in main
    assert "MiniMax image-01" not in source
    assert "minimax_m3" not in optimizer_contract
    assert "fake_vision" not in main + visual_asset_panel
    for retired in ("Midjourney", "Seedream", "Seedance", "Qwen 3", "Lib Video", "Lib Image"):
        assert retired not in source


def test_loop003_qal003_001_fixed_asset_submit_interlock_has_regression_markers() -> None:
    node_actions = (STUDIO_ROOT / "src" / "node-actions.js").read_text(encoding="utf-8")
    keyframe_actions = (STUDIO_ROOT / "src" / "node-keyframe-actions.js").read_text(encoding="utf-8")
    video_actions = (STUDIO_ROOT / "src" / "node-video-actions.js").read_text(encoding="utf-8")
    generation_guards = (STUDIO_ROOT / "src" / "node-generation-guards.js").read_text(encoding="utf-8")
    generation_submit = "\n".join((node_actions, keyframe_actions, video_actions, generation_guards))
    optimizer_contract = (STUDIO_ROOT / "src" / "optimizer-contract.js").read_text(encoding="utf-8")
    runtime_client = (STUDIO_ROOT / "src" / "runtime-client.js").read_text(encoding="utf-8")

    assert "preflightKeyframe" in runtime_client
    assert "preflightVideo" in runtime_client
    assert "prepareGenerationRequest" in keyframe_actions + video_actions
    assert "showCarryConfirmModal" in generation_guards
    assert "preflight_token" in generation_submit
    assert "temporary_asset_exclusions" in generation_submit
    assert "temporary_asset_exclusions" in optimizer_contract
    assert "asset_conflicts" in generation_guards
    assert "error.status = response.status" in runtime_client
    assert "error.route = route" in runtime_client
    assert "missingPreflightRouteError" in generation_guards
    assert "Runtime Service version is stale or not started from this branch" in generation_guards
    assert "Restart the 8790 Runtime Service and retry" in generation_guards


def test_keyframe_generation_polls_async_runtime_jobs_without_provider_jargon() -> None:
    runtime_client = (STUDIO_ROOT / "src" / "runtime-client.js").read_text(encoding="utf-8")
    node_actions = (STUDIO_ROOT / "src" / "node-actions.js").read_text(encoding="utf-8")
    keyframe_actions = (STUDIO_ROOT / "src" / "node-keyframe-actions.js").read_text(encoding="utf-8")
    keyframe_recovery = (STUDIO_ROOT / "src" / "node-keyframe-recovery.js").read_text(encoding="utf-8")

    assert "pollKeyframe(jobId)" in runtime_client
    assert "/keyframe-generations/${encodeURIComponent(jobId)}/poll" in runtime_client
    assert "pollNodeKeyframeGeneration" in node_actions
    assert "pollKeyframeUntilTerminal" not in node_actions
    assert "pollKeyframeUntilTerminal" in keyframe_actions
    assert "lastKeyframeJobId" in keyframe_actions
    assert "recoverTimedOutKeyframeFromAssets" in keyframe_actions
    assert "source_node_id" in keyframe_recovery
    assert "Gateway timeout while waiting for image generation" in runtime_client
    assert "MiniMax keyframe request failed" not in node_actions
    for forbidden in ("Codex", "codex", "handoff", "request.json", "codex_image_job"):
        assert forbidden not in node_actions + keyframe_actions


def test_asset_card_image_generation_uses_asset_prompt_and_asset_labels() -> None:
    optimizer_contract = (STUDIO_ROOT / "src" / "optimizer-contract.js").read_text(encoding="utf-8")
    asset_image_prompts = (STUDIO_ROOT / "src" / "asset-card-image-prompts.js").read_text(encoding="utf-8")
    asset_generation_prompt = (STUDIO_ROOT / "src" / "asset-card-generation-prompt.js").read_text(encoding="utf-8")
    asset_revision_refs = (STUDIO_ROOT / "src" / "asset-revision-references.js").read_text(encoding="utf-8")
    asset_card_drafts = (STUDIO_ROOT / "src" / "asset-card-drafts.js").read_text(encoding="utf-8")
    asset_card_panel = (STUDIO_ROOT / "src" / "panels" / "asset-card-panel.js").read_text(encoding="utf-8")
    runtime_keyframes = Path("apps/api/runtime_keyframes.py").read_text(encoding="utf-8")
    asset_nodes = (STUDIO_ROOT / "src" / "shot-asset-nodes.js").read_text(encoding="utf-8")
    keyframe_actions = (STUDIO_ROOT / "src" / "node-keyframe-actions.js").read_text(encoding="utf-8")
    keyframe_response = (STUDIO_ROOT / "src" / "node-keyframe-response.js").read_text(encoding="utf-8")
    generation_results = (STUDIO_ROOT / "src" / "node-generation-results.js").read_text(encoding="utf-8")
    generation_progress = (STUDIO_ROOT / "src" / "node-generation-progress.js").read_text(encoding="utf-8")
    visual_render = (STUDIO_ROOT / "src" / "panels" / "visual-asset-panel-render.js").read_text(encoding="utf-8")
    visual_defaults = (STUDIO_ROOT / "src" / "panels" / "visual-asset-defaults.js").read_text(encoding="utf-8")

    for marker in ("assetCardPromptText", "safeAssetCardSnapshot", "node_role", "asset_card_draft"):
        assert marker in optimizer_contract
    for marker in ("assetCardRevision", "image_guided_partial_revision", "identity_layout_anchor", "changed_fields"):
        assert marker in asset_revision_refs + asset_card_panel + optimizer_contract
    assert "assetCardRevisionImageRefs(node)" in optimizer_contract
    assert "assetCardRevisionPromptSupplement(node)" in asset_generation_prompt
    assert "image_operation" in runtime_keyframes
    assert "edit_source_image_path" in runtime_keyframes
    assert "image_input_fidelity" in runtime_keyframes
    assert "Revision strength: conservative low-change pass" in asset_revision_refs
    assert "primary visual source of truth" in asset_revision_refs
    assert "only editable delta" in asset_revision_refs
    assert "Wardrobe edit scope: add the requested clothing as an outer garment layer only" in asset_revision_refs
    assert "Plush/fabric material must read as a surface covering on the same existing robot frame" in asset_revision_refs
    assert "Do not turn the subject into a toy, chibi, mascot" in asset_revision_refs
    assert "assetImagePrompt(draft)" in asset_generation_prompt
    assert "assetCardPromptText(node)" in optimizer_contract.split("function primaryPromptText", 1)[1].split("const explicit", 1)[0]
    for marker in ("Character reference sheet", "front half-body close-up", "Environment reference", "Object reference", "Forbidden: software dashboard, app interface, data chart"):
        assert marker in asset_image_prompts
    assert "same rooftop/location" not in asset_image_prompts
    assert "same environment/location" in asset_image_prompts
    assert "雨夜城市街道/街区外景" in asset_card_drafts
    assert "可通行的城市街道/人行道前景" in asset_card_drafts
    assert "雨夜，空气潮湿" in asset_card_drafts
    for marker in ("发型/毛发/颜色", "面部/头部特征", "体态身形", "场景配色", "持握/互动关系", "金箍棒", "山巅石台战场"):
        assert marker in asset_card_drafts
    for marker in ("Facial-mark edit scope", "front half-body close-up", "exactly the requested scar"):
        assert marker in asset_revision_refs
    assert all(polluted not in asset_image_prompts + asset_generation_prompt for polluted in ("多视图角色设定表", "多视角场景设定图", "多视图道具设定表", "设定板排布"))
    for marker in ("场景资产必须是同一空间的多角度环境参考图", "角色资产必须按固定布局输出", "正面半身特写 + 全身正面居中 + 左侧面全身 + 背面全身", "道具资产必须是单一道具的正面"):
        assert marker in asset_generation_prompt
    assert "assetImageRatio(draft.asset_type)" in asset_nodes
    assert "visualAssetDefaultsFromAssetCardDraft" in visual_defaults
    for marker in ("设定视图", "多视角视图组", "道具视图组"):
        assert marker in visual_render
    assert 'nodeGenerationKind(node)' in keyframe_actions
    assert 'nodeRole === "asset_card_draft" ? "asset" : "keyframe"' in keyframe_response
    assert "reusableAssetForNode(n, reusableAsset, kind)" in keyframe_response
    assert "character_reference" in keyframe_response
    assert "scene_reference" in keyframe_response
    assert 'kind === "asset" ? "资产图" : "关键帧"' in generation_results
    assert "${label}已生成" in generation_results
    assert "资产素材" in generation_results
    assert 'asset: "资产图生成"' in generation_progress
    assert "此前排队" in generation_progress


def test_video_revision_and_named_asset_lookup_submit_markers() -> None:
    source = _source()
    runtime_client = (STUDIO_ROOT / "src" / "runtime-client.js").read_text(encoding="utf-8")
    node_actions = (STUDIO_ROOT / "src" / "node-actions.js").read_text(encoding="utf-8")
    video_actions = (STUDIO_ROOT / "src" / "node-video-actions.js").read_text(encoding="utf-8")
    generation_guards = (STUDIO_ROOT / "src" / "node-generation-guards.js").read_text(encoding="utf-8")
    node_menu = (STUDIO_ROOT / "src" / "panels" / "node-menu.js").read_text(encoding="utf-8")
    inspector = (STUDIO_ROOT / "src" / "asset-reference-inspector.js").read_text(encoding="utf-8")

    assert "preflightVideoRevision" in runtime_client
    assert "generateVideoRevision" in runtime_client
    assert "/video-revisions/preflight" in runtime_client
    assert "/video-revisions" in runtime_client
    assert "staleRuntimeRouteMessage" in runtime_client
    assert "error.status = response.status" in runtime_client
    assert "Restart the 8790 Runtime Service" in runtime_client
    assert "unconnectedLabelMatchedAssets" in generation_guards
    assert "showUnconnectedNamedAssetModal" in generation_guards
    assert "user_excluded_unconnected_named_asset" in generation_guards
    assert "label_matched" in inspector
    assert "named_asset_not_connected_fail_closed" not in generation_guards
    assert "startRemoteVideoRevision" in node_actions
    assert "videoRevision" in video_actions
    assert "AFS_ENABLE_EXPERIMENTAL_VIDEO_REVISION" in video_actions
    assert "enableVideoRevisionDraft" in source
    assert "video-revision-draft" in node_menu


def test_mvp_experience_hardening_carry_chain_and_asset_inspector_markers() -> None:
    summary = (STUDIO_ROOT / "src" / "asset-reference-summary.js")
    inspector = (STUDIO_ROOT / "src" / "asset-reference-inspector.js")
    canvas_view = (STUDIO_ROOT / "src" / "canvas-view.js").read_text(encoding="utf-8")
    canvas_body = (STUDIO_ROOT / "src" / "canvas-node-body.js").read_text(encoding="utf-8")
    result_view = (STUDIO_ROOT / "src" / "node-result-view.js").read_text(encoding="utf-8")
    optimizer = (STUDIO_ROOT / "src" / "optimizer.js").read_text(encoding="utf-8")
    node_actions = (STUDIO_ROOT / "src" / "node-actions.js").read_text(encoding="utf-8")
    generation_guards = (STUDIO_ROOT / "src" / "node-generation-guards.js").read_text(encoding="utf-8")
    styles = _styles()

    assert summary.is_file()
    assert inspector.is_file()
    summary_source = summary.read_text(encoding="utf-8")
    inspector_source = inspector.read_text(encoding="utf-8")
    assert "import { assetsFromNode" in canvas_view
    assert "import { assetsFromNode, carryChainItems" in canvas_body
    assert "import { assetTypeLabel, assetLabel, subjectSuffix" in result_view
    assert "carry-chain-strip" in canvas_body
    assert "carry-chain-chip" in canvas_body
    assert "lastContextBundle" in canvas_body
    assert "visualAssets" in canvas_body
    assert "MAX_CARRY_CHAIN_ITEMS" in summary_source
    assert "function buildAssetReferenceActions" in inspector_source
    assert "buildAssetReferenceActions" in optimizer
    assert "buildAssetReferenceActions" in generation_guards
    assert "named_asset_not_connected_fail_closed" not in generation_guards
    assert "showUnconnectedNamedAssetModal" in generation_guards
    assert "connect-named-asset" in optimizer
    assert "carry-chain-strip" in styles
    assert "carry-chain-chip.invalid" in styles


def test_mvp_experience_hardening_video_status_and_feedback_markers() -> None:
    feedback = STUDIO_ROOT / "src" / "quality-feedback.js"
    node_actions = (STUDIO_ROOT / "src" / "node-actions.js").read_text(encoding="utf-8")
    video_actions = (STUDIO_ROOT / "src" / "node-video-actions.js").read_text(encoding="utf-8")
    video_node_flow = (STUDIO_ROOT / "src" / "video-node-flow.js").read_text(encoding="utf-8")
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
    assert "promoteVideoAsset(payload)" in runtime_client
    assert "/video-assets/promote" in runtime_client
    assert 'return requestJson("/feedback"' in runtime_client
    assert "afs:studio-quality-feedback" in result_view
    assert "afs:video-asset-card-draft" in result_view
    assert "video-asset-card-draft" in result_view
    assert "node-preview-download" in result_view
    assert "下载视频" in result_view
    assert "导出原图" in result_view
    assert "openMediaPreviewModal" in result_view
    assert "downloadResolvedMedia" in result_view
    assert "放大查看" in result_view
    assert '["image", "video"].includes(node.type)' in result_view
    drawer_assets = (STUDIO_ROOT / "src" / "panels" / "drawer-assets.js").read_text(encoding="utf-8")
    assert "downloadImageAsset" in drawer_assets
    assert "downloadResolvedMedia(asset.preview_url" in drawer_assets
    assert "导出原图" in drawer_assets
    media_preview = (STUDIO_ROOT / "src" / "media-preview-modal.js").read_text(encoding="utf-8")
    assert "openMediaPreviewModal" in media_preview
    assert "downloadResolvedMedia" in media_preview
    assert "setRuntimeMediaSource(link, url)" in media_preview
    assert "media-preview-modal" in media_preview
    assert "qualityFeedbackView" not in result_view
    assert "openQualityFeedbackMenu" in node_menu
    assert "反馈图片质量" in node_menu
    assert "反馈视频质量" in node_menu
    assert "handleQualityFeedback" in main
    assert "runtime.recordFeedback" in main
    assert "cancelNodeVideoGeneration" in node_actions
    assert "cancelVideo(jobId)" in video_actions
    assert "cancelled_local_only" in video_actions
    assert "厂商侧任务" in video_actions
    assert "停止计费" in video_actions
    assert "ensureVideoFirstFrameAsset" in video_actions
    assert "ensureVideoFirstFrameAsset" in video_node_flow
    assert "inferConnectedFirstFrameAsset" in video_node_flow
    assert "已自动使用上游关键帧作为首帧" in video_node_flow
    assert "VIDEO_AUTO_POLL_INTERVAL_MS" in video_node_flow
    assert "scheduleVideoAutoPoll" in video_node_flow
    assert "clearVideoAutoPoll" in video_node_flow
    assert "本地取消轮询" in node_menu
    canvas_body = (STUDIO_ROOT / "src" / "canvas-node-body.js").read_text(encoding="utf-8")
    assert "node-status cancelled" in node_actions or "node-status cancelled" in canvas_body
    assert "quality-feedback" in styles
    assert "quality-feedback-popover" in styles
    assert "node-status.cancelled" in styles


def test_runtime_client_uses_runtime_port_when_studio_is_served_from_dev_port() -> None:
    runtime_client = (STUDIO_ROOT / "src" / "runtime-client.js").read_text(encoding="utf-8")

    assert 'const FALLBACK_BASE_URL = "http://127.0.0.1:8790"' in runtime_client
    assert 'const RUNTIME_BASE_STORAGE_KEY = "afs_runtime_base_url"' in runtime_client
    assert 'const LOCAL_STATIC_FALLBACK_PORTS = new Set(["8796"])' in runtime_client
    assert "LOCAL_STATIC_FALLBACK_PORTS.has(current.port)" in runtime_client
    assert "return FALLBACK_BASE_URL;" in runtime_client
    assert "explicitRuntimeBaseUrl" in runtime_client
    assert "normalizeRuntimeBaseUrl" in runtime_client
    assert "isLocalHost(url.hostname)" in runtime_client
