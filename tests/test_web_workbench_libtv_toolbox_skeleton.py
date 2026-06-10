from __future__ import annotations

from pathlib import Path


WORKBENCH_ROOT = Path("apps/workbench")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_libtv_toolbox_exposes_main_creation_tool_skeleton_without_provider() -> None:
    panels = _read(WORKBENCH_ROOT / "src" / "render-studio-panels.js")
    toolbox = _read(WORKBENCH_ROOT / "src" / "render-studio-toolbox.js")

    for marker in [
        "TV工具箱",
        "创作工具",
        "多角度",
        "运镜标记",
        "首尾帧",
        "图片高清",
        "文字生音乐",
        "角色库",
        "仅登记工具意图，真实生成继续由能力门控制。",
        "画布辅助",
        "libtv-toolbox-section",
        "libtv-tv-tool-row",
        "libtv-safe-tool-note",
    ]:
        assert marker in toolbox

    assert 'import { renderToolboxPanel } from "./render-studio-toolbox.js";' in panels
    assert "renderToolboxPanel(state)" in panels

    for forbidden in [
        "fetch(\"/provider",
        "AFS_ALLOW_REMOTE_IMAGE",
        "AFS_ALLOW_REMOTE_VIDEO",
        "showOpenFilePicker",
        "FileReader",
    ]:
        assert forbidden not in toolbox


def test_libtv_toolbox_skeleton_styles_support_mobile_internal_scroll() -> None:
    css = _read(WORKBENCH_ROOT / "styles-studio-toolbox.css")
    index = _read(WORKBENCH_ROOT / "index.html")

    for marker in [
        "grid-template-rows: auto minmax(0, 1fr);",
        ".libtv-toolbox-body",
        ".libtv-toolbox-section",
        ".libtv-tv-tool-row",
        ".libtv-safe-tool-note",
        "overflow-y: auto;",
    ]:
        assert marker in css

    assert '<link rel="stylesheet" href="./styles-studio-toolbox.css" />' in index


def test_libtv_toolbox_intent_flow_is_local_state_only() -> None:
    state = _read(WORKBENCH_ROOT / "src" / "state.js")
    app = _read(WORKBENCH_ROOT / "src" / "app.js")
    toolbox = _read(WORKBENCH_ROOT / "src" / "render-studio-toolbox.js")
    css = _read(WORKBENCH_ROOT / "styles-studio-toolbox.css")

    assert 'studioToolIntent: ""' in state
    assert "data-toolbox-intent" in app
    assert "studioToolIntent" in app

    for marker in [
        "activeIntent",
        "data-toolbox-intent",
        "libtv-toolbox-status",
        "libtv-tool-intent-flow",
        "本地工具意图已登记",
        "等待能力门授权",
        "未创建真实任务",
        "未启动 provider",
    ]:
        assert marker in toolbox

    for marker in [
        ".libtv-tv-tool-row.active",
        ".libtv-toolbox-status",
        ".libtv-tool-intent-flow",
    ]:
        assert marker in css

    for source in [state, app, toolbox, css]:
        for forbidden in [
            "fetch(\"/provider",
            "fetch('/provider",
            "fetch(\"/generate",
            "fetch('/generate",
            "AFS_ALLOW_REMOTE",
            "OPENAI_API_KEY",
            "signed_url",
            "showOpenFilePicker",
            "FileReader",
        ]:
            assert forbidden not in source
