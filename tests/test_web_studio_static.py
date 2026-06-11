from __future__ import annotations

from pathlib import Path


STUDIO_ROOT = Path("apps/studio")


def test_studio_static_entrypoint_is_the_only_user_frontend() -> None:
    assert STUDIO_ROOT.exists()
    assert not Path("apps/workbench").exists()
    assert not Path("apps/web").exists()

    index = (STUDIO_ROOT / "index.html").read_text(encoding="utf-8")
    assert './src/main.js' in index
    assert './styles/director.css' in index
    assert "AFS Studio 创作图谱" in index
    assert "/workbench" not in index


def test_studio_user_surface_does_not_reintroduce_old_workbench_terms() -> None:
    forbidden = [
        "/workbench",
        "项目记忆",
        "任务中心",
        "生成能力门",
        "高级诊断",
        "连接与诊断",
        "候选记忆",
        "确认/拒绝",
        "LibTV",
    ]
    sources = []
    for suffix in ("*.html", "*.css", "*.js"):
        sources.extend(STUDIO_ROOT.rglob(suffix))

    combined = "\n".join(path.read_text(encoding="utf-8") for path in sources)
    for term in forbidden:
        assert term not in combined


def test_studio_keeps_flow_native_canvas_controls() -> None:
    source = "\n".join(path.read_text(encoding="utf-8") for path in STUDIO_ROOT.rglob("*.js"))

    assert "openAddNodeMenu" in source
    assert "openOptimizer" in source
    assert "director" in source
    assert "prompt-optimizations" in source
    assert "keyframe-generations" in source
    assert "image-assets" in source
    assert "uploadNodeImage" in source
    assert "collectConnectedImageAssetRefs" in source
    assert "connected_reference_nodes" in source
    assert "candidate_previews" in source
    assert "reusable_image_assets" in source
    assert "mergeImageAssets" in source
    assert "node-preview-img" in source
    assert "resizeNodeForImagePreview" in source
    assert "previewAspectRatio" in source
    assert "has-image-preview" in source
    assert "startNodeGeneration" in source
    assert "studio-state" in source
    assert "loadStudioState" in source
    assert "saveStudioState" in source
    assert "createNode" in source
    assert "undo()" in source
    assert "redo()" in source


def test_studio_model_picker_only_exposes_current_mvp_models() -> None:
    source = (STUDIO_ROOT / "src" / "presets" / "models.js").read_text(encoding="utf-8")

    assert "MiniMax-M3" in source
    assert "MiniMax image-01" in source
    assert "local-creative-agent" in source
    assert 'providerServiceId: "minimax_image"' in source
    for retired in ("Midjourney", "Seedream", "Seedance", "Qwen 3", "Lib Video", "Lib Image"):
        assert retired not in source


def test_studio_v02_flow_native_surface_is_visible() -> None:
    source = "\n".join(path.read_text(encoding="utf-8") for path in STUDIO_ROOT.rglob("*.js"))
    styles = "\n".join(path.read_text(encoding="utf-8") for path in STUDIO_ROOT.rglob("*.css"))

    for label in (
        "上传剧本生成分镜",
        "创建角色三视图",
        "布置二维导演台",
        "生成关键帧提示词",
        "生成 5s 视频片段提示词",
        "画布元素",
        "显性资产",
        "设为参考",
        "用于当前节点",
        "从画布定位",
    ):
        assert label in source

    for marker in ("save-pill", "asset-card", "asset-thumb", "asset-action"):
        assert marker in styles


def test_studio_layout_and_director_prompt_link_are_explicit() -> None:
    source = "\n".join(path.read_text(encoding="utf-8") for path in STUDIO_ROOT.rglob("*.js"))
    styles = "\n".join(path.read_text(encoding="utf-8") for path in STUDIO_ROOT.rglob("*.css"))

    assert "drawer-open" in source
    assert "compact-project" in source
    assert "#topbar.drawer-open" in styles
    assert "left: var(--drawer-w)" in styles

    assert "DIRECTOR_OBJECTS" in source
    for label in ("镜头/机位", "人物/主体", "Key Light", "Fill Light", "Back Light", "反光板", "柔光布", "遮光旗"):
        assert label in source
    assert "top_down_2d" in source
    assert "director-board" in source

    assert "director_setup" in source
    assert "director_summary" in source
    assert "导演台布置" in source
    assert "已参考导演台布置" in source
    assert "opt-source-chip" in styles
    assert "director-edge" in styles
    assert "reference-edge" in styles
    assert "edge-label" in styles
    assert "relation_type" in source
    assert "max-height: none" in styles


def test_prompt_optimizer_sources_stay_product_facing() -> None:
    source = "\n".join(path.read_text(encoding="utf-8") for path in STUDIO_ROOT.rglob("*.js"))

    for label in ("影视结构", "项目风格", "角色/场景设定", "导演台布置"):
        assert label in source
    for forbidden in ("权重", "知识库", "provider raw", "候选记忆"):
        assert forbidden not in source
