from __future__ import annotations

from pathlib import Path


WORKBENCH_ROOT = Path("apps/workbench")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_libtv_canvas_execution_feedback_is_folded_into_edges_and_queue() -> None:
    workspace = _read(WORKBENCH_ROOT / "src" / "render-studio-workspace.js")
    css = _read(WORKBENCH_ROOT / "styles-libtv-shell.css")

    for marker in [
        "renderEdgeLayer",
        "studio-edge-layer",
        "studio-canvas-edge connected",
        '" active"',
        "生成队列",
        "分镜脚本 · 已完成",
        "关键帧 · 排队中",
        "视频片段 · 生成中",
        "待生成",
        "排队中",
        "生成中",
        "已完成",
        "失败",
        "本地预览",
    ]:
        assert marker in workspace

    for marker in [
        ".studio-edge-layer",
        ".studio-canvas-edge",
        ".studio-canvas-edge.active",
        ".queue-panel",
        ".status-chip.loading",
        ".status-chip.success",
        ".status-chip.error",
        ".status-chip.preview",
    ]:
        assert marker in css

    for forbidden in ["fetch(\"/provider", "fetch('/provider", "fetch(\"/generate", "AFS_ALLOW_REMOTE", "OPENAI_API_KEY", "signed_url"]:
        assert forbidden not in workspace


def test_libtv_execution_intent_state_is_not_a_user_page() -> None:
    state = _read(WORKBENCH_ROOT / "src" / "state.js")
    app = _read(WORKBENCH_ROOT / "src" / "app.js")
    workspace = _read(WORKBENCH_ROOT / "src" / "render-studio-workspace.js")

    assert 'studioExecutionIntent: ""' in state
    assert "data-execution-intent" not in app
    assert "render-studio-execution-scaffold.js" not in workspace
    assert "生成队列" in workspace
