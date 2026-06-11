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
    assert "createNode" in source


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
