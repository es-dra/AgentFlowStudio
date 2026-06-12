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
        "visual-asset-panel",
    ):
        assert marker in source
    for marker in ("opt-context-assets", "opt-inline-btn", "context-bundle-summary", "visual-asset-panel"):
        assert marker in styles
    assert "mode-tab asset_capture" not in source
    assert "mode-tab context_generate" not in source


def test_studio_model_picker_only_exposes_current_mvp_models() -> None:
    source = (STUDIO_ROOT / "src" / "presets" / "models.js").read_text(encoding="utf-8")

    assert "MiniMax-M3" in source
    assert "MiniMax image-01" in source
    assert "local-creative-agent" in source
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


def test_prompt_optimizer_sources_stay_product_facing() -> None:
    source = _source()

    for label in ("影视结构", "项目风格", "角色/场景设定", "导演台布置"):
        assert label in source
    for forbidden in ("权重", "知识库", "provider raw", "候选记忆"):
        assert forbidden not in source
