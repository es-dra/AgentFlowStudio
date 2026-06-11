from __future__ import annotations

from pathlib import Path


WORKBENCH_ROOT = Path("apps/workbench")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_prompt_input_is_shared_across_libtv_node_controls() -> None:
    node_prompt = _read(WORKBENCH_ROOT / "src" / "render-node-prompt.js")
    for marker in [
        "renderNodePrompt",
        "node-prompt-box",
        "node-prompt-input",
        "data-node-prompt-input",
        "optimize-current-prompt",
        "promptSurface",
        "优化",
        "renderPromptOptimizerPanel",
    ]:
        assert marker in node_prompt


def test_text_image_script_add_node_flows_use_node_prompt_optimizer() -> None:
    flow = _read(WORKBENCH_ROOT / "src" / "render-studio-add-node-flow.js")
    events = _read(WORKBENCH_ROOT / "src" / "studio-experience-events.js")
    controls = _read(WORKBENCH_ROOT / "src" / "studio-node-control-state.js")
    summary = _read(WORKBENCH_ROOT / "src" / "render-node-control-summary.js")
    css = _read(WORKBENCH_ROOT / "styles-studio-node-controls.css")

    for marker in [
        "renderTextNodeFlow",
        "libtv-text-node-flow",
        "文本节点 2",
        "自己编写内容",
        "文生视频",
        "renderScriptGeneratorFlow",
        "libtv-script-generator-flow",
        "剧本生成分镜脚本",
        "视频参考生成分镜脚本",
        "角色生成分镜脚本",
        "renderImageNodeFlow",
        "libtv-image-node-flow",
        "图片节点",
        "图生图",
        "图片高清",
        "风格",
        "标记",
        "renderNodePrompt(state",
        'surface: "text"',
        'surface: "script"',
        'surface: "image"',
        "nodeControlButton",
        "nodeControlSelect",
        "image-mode",
        "image-spec",
        "renderNodeControlSummary",
        "图片生成设置",
        "text-attempt",
        "script-attempt",
    ]:
        assert marker in flow

    for marker in [
        "renderNodeControlSummary",
        "data-node-control-summary",
        "data-active-node-mode",
        "node-control-summary-chips",
        "node-control-summary-hint",
        "图生图",
        "文生视频",
        "文本输入",
    ]:
        assert marker in summary + css

    for marker in ["[data-node-control]", "selectNodeControl", "nodeControlSelections"]:
        assert marker in events + controls

    for forbidden in ["showOpenFilePicker", "FileReader", "readAsDataURL", "AFS_ALLOW_REMOTE_LLM"]:
        assert forbidden not in flow


def test_video_audio_node_flows_use_inline_prompt_optimizer() -> None:
    video_flow = _read(WORKBENCH_ROOT / "src" / "render-studio-video-node-flow.js")
    audio_flow = _read(WORKBENCH_ROOT / "src" / "render-studio-audio-node-flow.js")

    for marker in [
        "renderVideoNodeFlow",
        "libtv-video-node-flow",
        "视频节点",
        "文生视频",
        "全能参考",
        "首尾帧",
        "运镜",
        "角色库",
        "Seedance 2.0 VIP",
        "16:9 / 720P / 5s",
        'surface: "video"',
        "renderNodePrompt(state",
        "nodeControlButton",
        "nodeControlSelect",
        "nodeControlToggle",
        "video-mode",
        "video-spec",
        "video-toggle-",
        "video-motion-panel",
        "video-motion-path",
        "video-motion",
        "video-motion-strength",
        "video-subject-motion",
        "video-motion-rhythm",
        "镜头运动",
        "运动强度",
        "主体动作",
        "镜头节奏",
        "renderNodeControlSummary",
        "视频生成设置",
    ]:
        assert marker in video_flow

    for marker in [
        "renderAudioNodeFlow",
        "libtv-audio-node-flow",
        "音频节点",
        "文本输入",
        "停顿",
        "语气词",
        "音色",
        "语速",
        'surface: "audio"',
        "renderNodePrompt(state",
        "nodeControlButton",
        "nodeControlSelect",
        "nodeControlToggle",
        "audio-target",
        "audio-spec",
        "audio-toggle-",
        "renderNodeControlSummary",
        "音频生成设置",
    ]:
        assert marker in audio_flow

    for forbidden in ["showOpenFilePicker", "FileReader", "AFS_ALLOW_REMOTE_VIDEO", "fetch(\"/provider"]:
        assert forbidden not in video_flow
        assert forbidden not in audio_flow


def test_director_and_video_merge_add_node_flows_match_canvas_product_shape() -> None:
    flow = _read(WORKBENCH_ROOT / "src" / "render-studio-add-node-flow.js")

    for marker in [
        "renderDirectorFlow",
        "libtv-director-flow",
        "libtv-director-canvas",
        "libtv-director-toolbar",
        "libtv-director-object-list",
        "libtv-director-camera-panel",
        "导演台",
        "导演视角",
        "机位视角",
        "场景",
        "Camera A",
        "Key Light",
        "Fill Light",
        "FOV 50°",
        "AI 识图导入",
    ]:
        assert marker in flow

    for marker in [
        "renderVideoMergeFlow",
        "libtv-video-merge-flow",
        "libtv-video-merge-preview",
        "libtv-video-merge-timeline",
        "libtv-video-merge-control",
        "请连接视频节点后操作",
        "片段 01",
        "转场",
        "节奏",
        "统一画幅",
    ]:
        assert marker in flow


def test_director_v3_flow_supports_top_view_dragging_and_asset_outputs() -> None:
    director_flow = _read(WORKBENCH_ROOT / "src" / "render-studio-director-node-flow.js")
    director_model = _read(WORKBENCH_ROOT / "src" / "director-setup-model.js")
    director_css = _read(WORKBENCH_ROOT / "styles-studio-director-node-flow.css")
    events = _read(WORKBENCH_ROOT / "src" / "studio-experience-events.js")
    app = _read(WORKBENCH_ROOT / "src" / "app.js")
    visible_assets = _read(WORKBENCH_ROOT / "src" / "render-visible-assets.js")
    source = "\n".join([director_flow, director_model, director_css, events, app, visible_assets])

    for marker in [
        "renderDirectorFlowV3",
        "director-flow-v3",
        "libtv-director-stage",
        "libtv-director-room",
        "libtv-director-modifier",
        "libtv-director-prop",
        "data-director-drag-id",
        "beginDirectorObjectDrag",
        "directorElementOverrides",
        "DIRECTOR_STAGE_ELEMENTS",
        "directorElements(state)",
        "directorPromptContext",
        "directorSetupAsset",
        "save-director-setup",
        "apply-director-setup-to-shot",
        "Camera A",
        "Key Light",
        "Fill Light",
        "Back Light",
        "Practical",
        "FOV 50",
        "selectedVisibleAssetId",
        "directorSavedSetupId",
    ]:
        assert marker in source


def test_starter_flows_keep_libtv_vertical_creation_paths() -> None:
    starters = _read(WORKBENCH_ROOT / "src" / "render-studio-starter-flows.js")
    for marker in [
        "renderScriptStarterFlow",
        "script-draft-goal",
        "从剧本生成分镜",
        "生成分镜计划",
        "renderCharacterStarterFlow",
        "角色三视图",
        "生成三视图",
        "renderImageVideoStarterFlow",
        "首帧图生视频",
        "renderAudioVideoStarterFlow",
        "音频生视频",
        "renderStarterNodes",
    ]:
        assert marker in starters
