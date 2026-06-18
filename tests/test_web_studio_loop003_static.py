from __future__ import annotations

from studio_static_helpers import STUDIO_ROOT

def test_loop003_qal003_002_generated_image_promotion_entries_have_regression_markers() -> None:
    canvas_view = (STUDIO_ROOT / "src" / "canvas-view.js").read_text(encoding="utf-8")
    drawer = "".join(
        path.read_text(encoding="utf-8")
        for path in (
            STUDIO_ROOT / "src" / "panels" / "drawer.js",
            STUDIO_ROOT / "src" / "panels" / "drawer-assets.js",
            STUDIO_ROOT / "src" / "panels" / "drawer-asset-actions.js",
        )
    )
    node_actions = (STUDIO_ROOT / "src" / "node-actions.js").read_text(encoding="utf-8")
    visual_asset_panel = (STUDIO_ROOT / "src" / "panels" / "visual-asset-panel.js").read_text(encoding="utf-8")

    assert 'data-action="fix-visual-asset"' in canvas_view
    assert "fixNodeVisualAsset" in node_actions
    assert "candidate_previews" in node_actions
    assert "reusable_image_assets" in node_actions
    assert 'initialAssetType: assetType' in drawer
    assert 'initialAssetType = "character"' in visual_asset_panel
    assert 'data-action="draft-card"' in visual_asset_panel
    assert "runtime.draftAssetCard" in visual_asset_panel
    assert "candidate_locks" in visual_asset_panel
    assert "missing_fields" in visual_asset_panel
    assert "draft-status" in visual_asset_panel


def test_loop003_qal003_003_asset_detail_reads_runtime_and_exposes_node_actions() -> None:
    runtime_client = (STUDIO_ROOT / "src" / "runtime-client.js").read_text(encoding="utf-8")
    asset_detail = (STUDIO_ROOT / "src" / "panels" / "asset-detail-popover.js").read_text(encoding="utf-8")
    canvas_input = (
        (STUDIO_ROOT / "src" / "canvas-input.js").read_text(encoding="utf-8")
        + (STUDIO_ROOT / "src" / "canvas-node-action-handler.js").read_text(encoding="utf-8")
    )
    drawer = (
        (STUDIO_ROOT / "src" / "panels" / "drawer.js").read_text(encoding="utf-8")
        + (STUDIO_ROOT / "src" / "panels" / "drawer-assets.js").read_text(encoding="utf-8")
        + (STUDIO_ROOT / "src" / "panels" / "drawer-asset-actions.js").read_text(encoding="utf-8")
    )

    assert "getVisualAsset(assetId)" in runtime_client
    assert "runtime.getVisualAsset(assetId)" in asset_detail
    assert "removeAssetFromSelectedNode" in asset_detail
    assert "excludeAssetForNextRun" in asset_detail
    assert "temporaryAssetExclusions" in asset_detail
    assert "openAssetDetailPopover(store, runtime" in canvas_input
    assert "openAssetDetailPopover(store, runtime" in drawer


def test_loop003_qal003_004_recent_or_current_projects_are_not_hidden_by_filter() -> None:
    main = (STUDIO_ROOT / "src" / "main.js").read_text(encoding="utf-8")
    controller = (STUDIO_ROOT / "src" / "studio-project-controller.js").read_text(encoding="utf-8")
    session = (STUDIO_ROOT / "src" / "studio-project-session.js").read_text(encoding="utf-8")

    assert "RECENT_PROJECTS_KEY" in session
    assert "rememberProject" in session
    assert "recentProjectIds" in session
    assert "persistActiveProject" in controller
    assert "item.project_id === currentId || recent.includes(item.project_id)" in controller
    assert "hiddenProjectCount" in controller
    assert "createProjectController" in main


def test_loop003_qal003_005_kling_sound_control_stays_hidden_without_descriptor_support() -> None:
    prompt_bar = (STUDIO_ROOT / "src" / "prompt-bar.js").read_text(encoding="utf-8")
    specs = (STUDIO_ROOT / "src" / "presets" / "specs.js").read_text(encoding="utf-8")

    assert "VIDEO_SOUND" not in prompt_bar
    assert "VIDEO_SOUND" not in specs
    assert "videoSpecLabel" in specs
    assert "spec.sound" not in specs
