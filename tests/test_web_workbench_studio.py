from __future__ import annotations

from pathlib import Path


WORKBENCH_ROOT = Path("apps/workbench")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_libtv_canvas_core_layout_is_wired() -> None:
    studio = _read(WORKBENCH_ROOT / "src" / "render-studio-workspace.js") + _read(WORKBENCH_ROOT / "src" / "studio-workflow-graph.js")
    panels = _read(WORKBENCH_ROOT / "src" / "render-studio-panels.js")
    css = (
        _read(WORKBENCH_ROOT / "styles-studio-canvas-experience.css")
        + _read(WORKBENCH_ROOT / "styles-studio-canvas-interactions.css")
        + _read(WORKBENCH_ROOT / "styles-libtv-shell.css")
    )
    app = _read(WORKBENCH_ROOT / "src" / "app.js")

    for marker in [
        "canvas-product-v3",
        "libtv-canvas-stage",
        "libtv-node-layer workflow-node-layer",
        "studio-edge-layer",
        "studio-canvas-edge connected",
        "libtv-workflow-control",
        "data-connect-from",
        "data-connect-to",
        "data-node-drag-handle",
        "剧本输入",
        "分镜脚本",
        "角色三视图",
        "场景资产",
        "关键帧",
        "导演台",
        "视频片段",
        "成片合成",
    ]:
        assert marker in studio

    for marker in [
        "libtv-bottom-bar",
        "添加节点",
        "工具箱",
        "素材库",
        "历史记录",
        "快捷键",
        "帮助中心",
        "小地图",
        "网格吸附",
        "canvas-asset-drawer",
        "画布",
        "资产",
    ]:
        assert marker in panels

    for marker in [
        ".canvas-product-v3",
        ".libtv-canvas-stage",
        ".workflow-node-layer",
        ".studio-canvas-edge.active",
        ".libtv-node:hover",
        ".studio-node-actions",
        ".libtv-bottom-bar",
        ".canvas-asset-drawer",
        ".libtv-workflow-control",
    ]:
        assert marker in css

    assert "[data-add-node-kind]" in app
    assert "[data-card-id]" in app
    assert "bindCanvasInteractions(root, state, paint)" in app
    assert "bindStudioExperienceEvents(root, state, paint)" in app


def test_canvas_dock_exposes_libtv_style_node_entries() -> None:
    panels = _read(WORKBENCH_ROOT / "src" / "render-studio-panels.js")
    flow = _read(WORKBENCH_ROOT / "src" / "render-studio-add-node-flow.js")

    for marker in [
        '["text", "文本"',
        '["image", "图片"',
        '["video", "视频"',
        '["video_merge", "视频合成"',
        '["director", "导演台"',
        '["audio", "音频"',
        '["script", "脚本"',
        '["upload", "上传"',
        '["history", "从生成历史选择"',
    ]:
        assert marker in panels

    for marker in [
        "libtv-text-node-flow",
        "libtv-image-node-flow",
        "libtv-video-node-flow",
        "libtv-audio-node-flow",
        "libtv-script-generator-flow",
        "libtv-video-merge-flow",
        "libtv-director-flow",
        "libtv-upload-dropzone",
        "libtv-history-resource-picker",
    ]:
        assert marker in flow or marker in _read(WORKBENCH_ROOT / "src" / "render-studio-workspace.js")


def test_director_desk_is_canvas_node_not_admin_page() -> None:
    director = _read(WORKBENCH_ROOT / "src" / "render-director-desk.js")
    flow = _read(WORKBENCH_ROOT / "src" / "render-studio-add-node-flow.js")
    css = _read(WORKBENCH_ROOT / "styles-director-desk.css") + _read(WORKBENCH_ROOT / "styles-studio-canvas-experience.css")

    for marker in [
        "画面参考",
        "director-floor-plan",
        "Key Light",
        "Fill Light",
        "Back Light",
        "Practical",
        "Camera A",
        "Subject A",
        "反光板",
        "柔光布",
        "遮光旗",
        "保存为场景资产",
        "生成专业提示词",
        "应用到当前镜头",
    ]:
        assert marker in director

    for marker in ["libtv-director-flow", "libtv-director-canvas", "libtv-director-camera-panel", "FOV 50°"]:
        assert marker in flow

    for marker in [".director-desk-board", ".director-floor-plan", ".director-light", ".director-camera", ".director-inspector"]:
        assert marker in css


def test_director_node_v3_behaves_like_a_canvas_editor() -> None:
    flow = _read(WORKBENCH_ROOT / "src" / "render-studio-director-node-flow.js")
    model = _read(WORKBENCH_ROOT / "src" / "director-setup-model.js")
    css = _read(WORKBENCH_ROOT / "styles-studio-director-node-flow.css")
    events = _read(WORKBENCH_ROOT / "src" / "studio-experience-events.js")
    source = "\n".join([flow, model, css, events])

    for marker in [
        "director-flow-v3",
        "libtv-director-stage",
        "libtv-director-grid",
        "libtv-director-room",
        "data-director-drag-id",
        "pointerdown",
        "pointermove",
        "directorElementOverrides",
        "DIRECTOR_STAGE_ELEMENTS",
        "directorPromptContext",
        "directorSetupAsset",
        "libtv-director-modifier",
        "libtv-director-prop",
        "Key Light",
        "Fill Light",
        "Back Light",
        "Practical",
        "Camera A",
        "subject-a",
        "FOV 50",
    ]:
        assert marker in source


def test_visible_asset_library_only_shows_explicit_assets() -> None:
    assets = _read(WORKBENCH_ROOT / "src" / "render-visible-assets.js")
    css = _read(WORKBENCH_ROOT / "styles-visible-assets.css") + _read(WORKBENCH_ROOT / "styles-studio-canvas-experience.css")

    for marker in [
        "人物三视图",
        "角色头像",
        "服装版本",
        "场景图",
        "导演台布光图",
        "关键帧",
        "视频片段",
        "音频",
        "设为参考",
        "用于当前镜头",
        "重新生成",
        "查看来源",
        "加入导演台",
    ]:
        assert marker in assets
    for hidden in ["人物性格", "偏好权重", "失败经验", "hidden_constraints"]:
        assert hidden not in assets
    for marker in [".asset-library-page", ".asset-library-layout", ".visible-asset-card", ".asset-preview-panel"]:
        assert marker in css
