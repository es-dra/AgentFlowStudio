from __future__ import annotations

from pathlib import Path


WORKBENCH_ROOT = Path("apps/workbench")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_libtv_resource_entries_open_safe_local_canvas_placeholders() -> None:
    app = _read(WORKBENCH_ROOT / "src" / "app.js")
    state = _read(WORKBENCH_ROOT / "src" / "state.js")
    workspace = _read(WORKBENCH_ROOT / "src" / "render-studio-workspace.js")
    css = _read(WORKBENCH_ROOT / "styles-libtv-shell.css")

    assert 'studioResourceMode: ""' in state
    assert "state.studioResourceMode = node.dataset.addResourceKind || \"\"" in app
    assert 'addResourceKind: "upload"' in workspace
    assert 'addResourceKind: "history"' in workspace

    for marker in [
        "renderResourceCanvas",
        "libtv-upload-dropzone",
        "libtv-history-resource-picker",
        "上传资源",
        "选择图片、视频或音频文件作为参考素材。",
        "从生成历史选择",
        "按图片、视频、音频筛选可复用记录，并加入当前镜头。",
    ]:
        assert marker in workspace

    for marker in [".resource-canvas", ".added-node-panel"]:
        assert marker in css

    for forbidden in ["input type=\"file\"", "showOpenFilePicker", "FileReader", "readAsDataURL"]:
        assert forbidden not in workspace
