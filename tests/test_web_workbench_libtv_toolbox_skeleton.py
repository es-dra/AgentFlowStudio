from __future__ import annotations

from pathlib import Path


WORKBENCH_ROOT = Path("apps/workbench")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_libtv_toolbox_is_bottom_dock_popover() -> None:
    app = _read(WORKBENCH_ROOT / "src" / "app.js")
    panels = _read(WORKBENCH_ROOT / "src" / "render-studio-panels.js")
    toolbox = _read(WORKBENCH_ROOT / "src" / "render-studio-toolbox.js")
    css = _read(WORKBENCH_ROOT / "styles-libtv-shell.css") + _read(WORKBENCH_ROOT / "styles-studio-canvas-experience.css")

    assert "renderToolboxPanel" in panels
    assert "工具箱" in panels
    assert "[data-toolbox-intent]" in app or "[data-toolbox-intent]" in _read(WORKBENCH_ROOT / "src" / "studio-experience-events.js")
    assert "libtv-bottom-bar" in panels

    for marker in ["分镜整理", "角色一致性", "灯光方案", "机位运镜", "负面提示词"]:
        assert marker in toolbox
    for marker in ["文本", "图片", "视频", "视频合成", "导演台", "音频", "脚本", "上传", "从生成历史选择"]:
        assert marker in panels
    for marker in [".libtv-bottom-bar", ".libtv-tool", ".libtv-toolbox-panel"]:
        assert marker in css
