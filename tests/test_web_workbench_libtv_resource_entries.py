from __future__ import annotations

from pathlib import Path


WORKBENCH_ROOT = Path("apps/workbench")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_libtv_resource_entries_open_safe_local_panels() -> None:
    app = _read(WORKBENCH_ROOT / "src" / "app.js")
    state = _read(WORKBENCH_ROOT / "src" / "state.js")
    panels = _read(WORKBENCH_ROOT / "src" / "render-studio-panels.js")
    resource_entry = _read(WORKBENCH_ROOT / "src" / "render-studio-resource-entry.js")

    assert 'studioResourceMode: ""' in state
    assert "state.studioResourceMode = node.dataset.addResourceKind || \"\"" in app
    assert 'state.studioPanel = "resource"' in app
    assert 'if (panel === "resource") return renderResourceEntryPanel(state.studioResourceMode, workspace)' in panels

    for marker in [
        "renderResourceEntryPanel",
        "libtv-resource-entry-panel",
        "libtv-upload-resource-panel",
        "libtv-history-resource-picker",
        "添加资源",
        "上传素材",
        "拖放文件或选择安全摘要",
        "图片",
        "视频",
        "音频",
        "文本",
        "只登记素材摘要，不读取本地文件字节。",
        "从生成历史选择",
        "图片历史(0)",
        "视频历史(0)",
        "音频历史(0)",
        "时间降序",
        "批量操作",
        "暂无历史记录",
        "添加到画布",
        "取消",
    ]:
        assert marker in resource_entry

    for forbidden in ["input type=\"file\"", "showOpenFilePicker", "FileReader", "readAsDataURL"]:
        assert forbidden not in resource_entry


def test_libtv_resource_entry_styles_are_registered() -> None:
    index = _read(WORKBENCH_ROOT / "index.html")
    css = _read(WORKBENCH_ROOT / "styles-studio-resource-entry.css")

    assert '<link rel="stylesheet" href="./styles-studio-resource-entry.css" />' in index
    for marker in [
        ".libtv-resource-entry-panel",
        ".libtv-resource-tabs",
        ".libtv-upload-dropzone",
        ".libtv-resource-kind-grid",
        ".libtv-history-resource-picker",
        ".libtv-resource-empty",
        ".libtv-resource-history-card",
        "min-height: 184px;",
        "grid-template-rows: 68px auto minmax(42px, auto) auto;",
        "overflow: hidden;",
        ".libtv-resource-history-card small",
        "-webkit-line-clamp: 3;",
        "overflow-wrap: anywhere;",
        "section.libtv-history-resource-picker {",
        "grid-template-rows: auto auto auto minmax(0, 1fr) auto;",
        "overflow-y: auto;",
        "min-height: 0;",
    ]:
        assert marker in css
