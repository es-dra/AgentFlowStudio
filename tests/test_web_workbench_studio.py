from __future__ import annotations
from pathlib import Path
WORKBENCH_ROOT = Path("apps/workbench")
def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")
def test_libtv_style_canvas_workspace_is_wired() -> None:
    index = _read(WORKBENCH_ROOT / "index.html")
    state = _read(WORKBENCH_ROOT / "src" / "workbench-state.js")
    app = _read(WORKBENCH_ROOT / "src" / "app.js")
    app_state = _read(WORKBENCH_ROOT / "src" / "state.js")
    interactions = _read(WORKBENCH_ROOT / "src" / "canvas-interactions.js")
    render = _read(WORKBENCH_ROOT / "src" / "render.js")
    renderer = _read(WORKBENCH_ROOT / "src" / "render-studio-workspace.js")
    header = _read(WORKBENCH_ROOT / "src" / "render-studio-canvas-header.js")
    starter_flows = _read(WORKBENCH_ROOT / "src" / "render-studio-starter-flows.js")
    add_node_flow = _read(WORKBENCH_ROOT / "src" / "render-studio-add-node-flow.js")
    panels = _read(WORKBENCH_ROOT / "src" / "render-studio-panels.js")
    history = _read(WORKBENCH_ROOT / "src" / "render-studio-history.js")
    resource_entry = _read(WORKBENCH_ROOT / "src" / "render-studio-resource-entry.js")
    studio_source = renderer + header + starter_flows + add_node_flow + _read(WORKBENCH_ROOT / "src" / "render-studio-video-node-flow.js") + _read(WORKBENCH_ROOT / "src" / "render-studio-audio-node-flow.js") + panels + history + resource_entry
    normalizer = _read(WORKBENCH_ROOT / "src" / "studio-workspace-state.js")
    css = (
        _read(WORKBENCH_ROOT / "styles-studio-canvas-v2.css")
        + _read(WORKBENCH_ROOT / "styles-studio-canvas-header.css")
        + _read(WORKBENCH_ROOT / "styles-studio-starters.css")
        + _read(WORKBENCH_ROOT / "styles-studio-character-flow.css")
        + _read(WORKBENCH_ROOT / "styles-studio-image-video-flow.css")
        + _read(WORKBENCH_ROOT / "styles-studio-audio-video-flow.css")
        + _read(WORKBENCH_ROOT / "styles-studio-add-node-flow.css") + _read(WORKBENCH_ROOT / "styles-studio-text-node-flow.css") + _read(WORKBENCH_ROOT / "styles-studio-video-node-flow.css") + _read(WORKBENCH_ROOT / "styles-studio-audio-node-flow.css") + _read(WORKBENCH_ROOT / "styles-studio-script-generator-flow.css")
        + _read(WORKBENCH_ROOT / "styles-studio-director-merge-flow.css")
        + _read(WORKBENCH_ROOT / "styles-studio-resource-entry.css")
        + _read(WORKBENCH_ROOT / "styles-studio-canvas-panels.css")
        + _read(WORKBENCH_ROOT / "styles-studio-utility-panels.css") + _read(WORKBENCH_ROOT / "styles-studio-toolbox.css")
    )

    assert '<link rel="stylesheet" href="./styles-studio-workspace.css" />' in index
    assert '<link rel="stylesheet" href="./styles-studio-canvas-v2.css" />' in index
    assert '<link rel="stylesheet" href="./styles-studio-canvas-header.css" />' in index
    assert '<link rel="stylesheet" href="./styles-studio-starters.css" />' in index
    assert '<link rel="stylesheet" href="./styles-studio-character-flow.css" />' in index
    assert '<link rel="stylesheet" href="./styles-studio-image-video-flow.css" />' in index
    assert '<link rel="stylesheet" href="./styles-studio-audio-video-flow.css" />' in index
    assert '<link rel="stylesheet" href="./styles-studio-add-node-flow.css" />' in index and '<link rel="stylesheet" href="./styles-studio-text-node-flow.css" />' in index and '<link rel="stylesheet" href="./styles-studio-video-node-flow.css" />' in index and '<link rel="stylesheet" href="./styles-studio-audio-node-flow.css" />' in index and '<link rel="stylesheet" href="./styles-studio-script-generator-flow.css" />' in index
    assert '<link rel="stylesheet" href="./styles-studio-director-merge-flow.css" />' in index
    assert '<link rel="stylesheet" href="./styles-studio-resource-entry.css" />' in index
    assert '<link rel="stylesheet" href="./styles-studio-canvas-panels.css" />' in index
    assert '<link rel="stylesheet" href="./styles-studio-utility-panels.css" />' in index and '<link rel="stylesheet" href="./styles-studio-toolbox.css" />' in index
    assert "styles-studio-canvas-focus.css" not in index
    assert "styles-studio-canvas-mode.css" not in index
    assert not (WORKBENCH_ROOT / "styles-studio-canvas-focus.css").exists()
    assert not (WORKBENCH_ROOT / "styles-studio-canvas-mode.css").exists()

    assert "normalizeStudioWorkspace" in state
    assert "source.studio_workspace" in state
    assert "studio_workspace: normalizeStudioWorkspace(source.studio_workspace)" in state
    assert 'studioPanel: ""' in app_state
    assert "canvasPanX: 0" in app_state
    assert "canvasPanY: 0" in app_state
    assert "canvasZoom: 1" in app_state
    assert 'studioAddedNodeKind: ""' in app_state
    assert 'studioFocus: "canvas"' not in app_state
    assert 'studioMode: "produce"' not in app_state

    assert 'import { renderStudioWorkspace } from "./render-studio-workspace.js";' in render
    assert "workspace-canvas-v2" in render
    assert 'return withWindow("Create", [' in render
    assert "renderStudioWorkspace(workbench.studio_workspace, state)" in render
    assert "state.artifact ? renderArtifactPanel(state) : null" in render

    for marker in [
        "libtv-canvas",
        "libtv-topbar",
        "libtv-project-pill",
        "libtv-canvas-stage",
        "libtv-node-layer",
        "libtv-node",
        "studioStarterMode",
        "studioStarterKind",
        "selectedStarterNode",
        "renderScriptStarterFlow",
        "renderCharacterStarterFlow",
        "renderImageVideoStarterFlow",
        "renderAudioVideoStarterFlow",
        "renderAddNodeFlow",
        "selectedAddNode",
        "libtv-script-flow",
        "libtv-script-node",
        "libtv-script-connector",
        "libtv-script-control-card",
        "libtv-character-flow",
        "libtv-character-source",
        "libtv-character-result",
        "libtv-character-toolbar",
        "libtv-character-replace-tip",
        "角色图",
        "全景",
        "多角度",
        "打光",
        "九宫格",
        "高清",
        "宫格切分",
        "点击按钮，可替换上传你的角色图",
        "生成器未启动",
        "libtv-image-video-flow",
        "libtv-first-frame-source",
        "libtv-video-result",
        "libtv-video-control-card",
        "libtv-video-mode-tabs",
        "libtv-video-tool-row",
        "首帧",
        "视频",
        "文生视频",
        "全能参考",
        "图生视频",
        "首尾帧",
        "图片参考",
        "标记",
        "运镜",
        "角色库",
        "Seedance 2.0 VIP",
        "16:9 · 720P · 5s",
        "点击按钮，可替换上传你的首帧图",
        "视频生成未启动",
        "libtv-audio-video-flow",
        "libtv-audio-source",
        "libtv-audio-waveform",
        "libtv-audio-video-result",
        "libtv-audio-control-card",
        "libtv-audio-mode-tabs",
        "libtv-audio-tool-row",
        "音频",
        "图片",
        "00:00 / 00:03",
        "根据上传的音频生成对应场景画面，镜头语言、节奏、音乐匹配情绪变化，电影级质感。",
        "1个",
        "135",
        "联网搜索",
        "自动校验素材",
        "点击按钮，可替换上传你的音频文件",
        "音频驱动未启动",
        "libtv-add-node-flow",
        "libtv-added-node",
        "libtv-added-node-control",
        "libtv-added-node-kind",
        "文本生成未启动",
        "图片生成未启动",
        "视频生成未启动",
        "音频生成未启动",
        "脚本生成未启动",
        "视频合成未启动",
        "导演台未启动",
        "输入剧本、广告词或品牌文案要求",
        "描述海报、分镜或角色设计",
        "描述创意广告、动画或电影片段",
        "选择节点只创建本地安全占位，不上传素材、不启动生成。",
        "本地起步模板",
        "故事脚本生成",
        "剧本",
        "《我在盛唐写天下》",
        "双击剧本内容，可直接编辑或替换",
        "根据我上传的剧本生成一个完整的故事脚本",
        "GVLM 3.1",
        "角色三视图",
        "首帧图生视频",
        "音频生视频",
        "libtv-bottom-bar",
        "studioTool",
        "addNodeKind",
        "renderAddNodeMenu",
        "renderAssetsPanel",
        "renderToolboxPanel",
        "renderHistoryPanel",
        "renderHistoryZoom",
        "图片历史",
        "视频历史",
        "音频历史",
        "创建时间倒序",
        "批量选择",
        "仅看可复用",
        "renderShortcutsPanel",
        "renderHelpPanel",
        "renderInspectorPanel",
        "renderGatePanel",
        "canvasSurface",
        "canvasContent",
        "aria-label",
        "添加节点",
        "文本",
        "剧本、广告词、品牌文案",
        "图片",
        "海报、分镜、角色设计",
        "视频",
        "创意广告、动画、电影",
        "视频合成",
        "多个视频片段合为一个",
        "导演台",
        "搭建3D场景，截图作为构图参考",
        "音频",
        "音效、配音、音乐",
        "脚本",
        "创意脚本、生成故事板",
        "添加资源",
        "上传",
        "可上传图片、视频、音频文件",
        "从生成历史选择",
        "从历史生成中选择素材",
        "Beta",
        "NEW",
        "生成能力门",
        "项目记忆",
        "脚本生成器",
        "libtv-node-palette",
        "libtv-add-resource-section",
        "libtv-node-badge",
        "libtv-asset-tabs",
        "libtv-asset-groups",
        "项目输入",
        "生成候选",
        "记忆证据",
        "资产管理",
        "工具箱",
        "历史资产",
        "快捷键",
        "帮助中心",
    ]:
        assert marker in studio_source

    assert "[data-studio-tool]" in app
    assert "bindCanvasInteractions(root, state, paint)" in app
    assert "state.studioPanel = state.studioPanel === panel ? \"\" : panel" in app
    assert "[data-add-node-kind]" in app
    assert 'if (panel === "add")' in app
    assert "state.studioAddedNodeKind = node.dataset.addNodeKind || \"\"" in app
    assert "state.studioAddedNodeKind = \"\"" in app
    assert "state.selectedCardId = match.card_id" in app
    assert "[data-studio-focus]" not in app
    assert "[data-studio-mode]" not in app

    assert "primary_command" in normalizer
    assert "operations_summary" in normalizer
    assert "provider_blockers" in normalizer
    assert "bindCanvasInteractions" in interactions
    assert "data-canvas-action" in interactions
    assert "canvasTransformStyle" in interactions
    assert "zoomPercent" in interactions
    assert ".libtv-image-video-flow" in interactions
    assert ".libtv-audio-video-flow" in interactions
    assert '["script", "character", "image", "audio"]' in app

    for marker in [
        ".libtv-canvas",
        ".libtv-canvas-stage.is-panning",
        ".libtv-script-flow",
        ".libtv-script-node",
        ".libtv-script-connector",
        ".libtv-edit-tip",
        ".libtv-script-control-card",
        ".libtv-character-flow",
        ".libtv-character-source",
        ".libtv-character-result",
        ".libtv-character-toolbar",
        ".libtv-character-replace-tip",
        ".libtv-image-video-flow",
        ".libtv-first-frame-source",
        ".libtv-video-result",
        ".libtv-video-control-card",
        ".libtv-video-mode-tabs",
        ".libtv-audio-video-flow",
        ".libtv-audio-source",
        ".libtv-audio-waveform",
        ".libtv-audio-video-result",
        ".libtv-audio-control-card",
        ".libtv-audio-mode-tabs",
        ".libtv-audio-tool-row",
        ".libtv-add-node-flow",
        ".libtv-added-node",
        ".libtv-added-node-control",
        ".libtv-added-node-kind",
        ".libtv-bottom-bar",
        ".libtv-add-menu",
        ".libtv-add-resource-section",
        ".libtv-node-badge",
        ".libtv-side-panel",
        ".libtv-toolbox-panel",
        ".libtv-history-panel",
        ".libtv-history-modal",
        ".libtv-history-grid",
        ".libtv-history-card",
        ".libtv-shortcuts-panel",
        ".libtv-help-panel",
        ".libtv-inspector-panel",
        ".libtv-gate-panel",
        "radial-gradient(circle at 1px 1px",
    ]:
        assert marker in css

    for retired_marker in ["studio-command-strip", "studio-focus-tab", "studio-mode-switch", "renderStudioFocusTabs"]:
        assert retired_marker not in renderer
