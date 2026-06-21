from studio_static_helpers import STUDIO_ROOT, _styles


def test_prompt_optimization_is_inline_and_selection_safe() -> None:
    optimizer = (STUDIO_ROOT / "src" / "optimizer.js").read_text(encoding="utf-8")
    prompt_bar = (STUDIO_ROOT / "src" / "prompt-bar.js").read_text(encoding="utf-8")
    styles = _styles()

    assert "showPopover" not in optimizer
    assert "optimizer-pop" not in optimizer
    assert "promptOptimizationState" in optimizer
    assert 'status: "running"' in optimizer
    assert 'store.get().nodes[nodeId]' in optimizer
    assert "connectNamedAssetToTarget" in optimizer
    assert "buildAssetReferenceActions" in optimizer
    assert "prompt-shimmer" in prompt_bar
    assert "syncPromptBarState" in prompt_bar
    assert "promptTextShimmer" in styles


def test_text_node_has_script_import_expand_and_breakdown_controls() -> None:
    prompt_bar = (STUDIO_ROOT / "src" / "prompt-bar.js").read_text(encoding="utf-8")
    script_breakdown = (STUDIO_ROOT / "src" / "script-breakdown.js").read_text(encoding="utf-8")
    nodes = (STUDIO_ROOT / "src" / "nodes.js").read_text(encoding="utf-8")

    assert "importScriptFileIntoTextNode" in prompt_bar
    assert "expandTextIdeaToScript" in prompt_bar
    assert "splitTextNodeToStoryboardNodes" in prompt_bar
    assert "导入剧本" in prompt_bar
    assert "扩写剧本" in prompt_bar
    assert "拆分分镜" in prompt_bar
    assert "export function splitScriptIntoShots" in script_breakdown
    assert 'createNode(store, "script"' in script_breakdown
    assert "connect(store, fresh.id, shotNode.id)" in script_breakdown
    assert "剧本拆分分镜" in nodes


def test_text_script_body_receives_generated_content_and_hides_workflow_toolbar() -> None:
    script_breakdown = (STUDIO_ROOT / "src" / "script-breakdown.js").read_text(encoding="utf-8")
    canvas_body = (STUDIO_ROOT / "src" / "canvas-node-body.js").read_text(encoding="utf-8")
    canvas_view = (STUDIO_ROOT / "src" / "canvas-view.js").read_text(encoding="utf-8")
    action_handler = (STUDIO_ROOT / "src" / "canvas-node-action-handler.js").read_text(encoding="utf-8")
    styles = _styles()

    assert "node.content = prompt" in script_breakdown
    assert "visibleText" in script_breakdown
    assert "scriptExpansionState?.status === \"running\"" in canvas_view
    assert "hide-context-toolbar" in canvas_view
    assert ".node.hide-context-toolbar .node-context-toolbar" in styles
    assert "content-shimmer" in canvas_body
    assert ".text-content-view.content-shimmer" in styles
    assert 'node.type === "text" && action === "upload"' in action_handler


def test_storyboard_breakdown_creates_structured_shots_and_asset_prep_nodes() -> None:
    script_breakdown = (STUDIO_ROOT / "src" / "script-breakdown.js").read_text(encoding="utf-8")
    structured_shot = (STUDIO_ROOT / "src" / "structured-shot.js").read_text(encoding="utf-8")
    asset_nodes = (STUDIO_ROOT / "src" / "shot-asset-nodes.js").read_text(encoding="utf-8")

    assert "structuredShotFromSegment" in script_breakdown
    assert "createShotAssetPrepNodes" in script_breakdown
    assert "export function structuredShotFromSegment" in structured_shot
    for field in ["镜号：", "时长：", "画面描述：", "景别：", "光影氛围：", "运镜：", "资产："]:
        assert field in structured_shot
    assert "export function extractShotAssetRefs" in structured_shot
    assert "shotAssetRefs" in script_breakdown
    assert "assetPrepState" in script_breakdown
    assert 'createNode(store, "image"' in asset_nodes
    assert "asset_prep" in asset_nodes
    assert "connect(store, scriptNodeId, assetNode.id)" in asset_nodes


def test_visual_asset_draft_and_existing_asset_edit_show_inline_loading() -> None:
    visual_panel = (STUDIO_ROOT / "src" / "panels" / "visual-asset-panel.js").read_text(encoding="utf-8")
    visual_render = (STUDIO_ROOT / "src" / "panels" / "visual-asset-panel-render.js").read_text(encoding="utf-8")
    node_actions = (STUDIO_ROOT / "src" / "node-actions.js").read_text(encoding="utf-8")
    asset_detail = (STUDIO_ROOT / "src" / "panels" / "asset-detail-popover.js").read_text(encoding="utf-8")
    styles = _styles()

    assert "existingAsset" in visual_panel
    assert "supersedes_asset_id" in visual_panel
    assert "image_asset_refs" in visual_panel
    assert "seedFromExistingAsset" in visual_panel
    assert "is-drafting" in visual_panel
    assert "visualAssetFieldShimmer" in styles
    assert "data-drafting" in visual_render
    assert "lastFixedVisualAsset" in node_actions
    assert "imageAssetFromVisualAsset" in node_actions
    assert "调整资产" in asset_detail
    assert "openVisualAssetPanel" in asset_detail
    assert "existingAsset" in asset_detail
