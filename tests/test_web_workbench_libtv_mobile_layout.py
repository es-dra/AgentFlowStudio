from __future__ import annotations

from pathlib import Path


WORKBENCH_ROOT = Path("apps/workbench")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_libtv_mobile_canvas_controls_do_not_force_horizontal_overflow() -> None:
    css = _read(WORKBENCH_ROOT / "styles-studio-canvas-panels.css")

    for marker in [
        "@media (max-width: 720px)",
        ".libtv-bottom-bar",
        "max-width: calc(100vw - 24px)",
        "overflow-x: auto",
        ".libtv-node-layer",
        "grid-template-columns: minmax(0, 1fr)",
        ".libtv-node",
        "width: 100%",
    ]:
        assert marker in css
