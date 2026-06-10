from __future__ import annotations

from pathlib import Path


SCRIPT = Path("tools/workbench_libtv_toolbox_browser_qa.py")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_libtv_toolbox_browser_qa_script_contract() -> None:
    assert SCRIPT.exists()
    source = _read(SCRIPT)

    for marker in [
        "agentflow_workbench_libtv_toolbox_browser_qa",
        "VIEWPORTS",
        "desktop",
        "tablet",
        "mobile",
        "TV工具箱",
        "多角度",
        "运镜标记",
        "首尾帧",
        "图片高清",
        "文字生音乐",
        "角色库",
        "data-studio-tool='toolbox'",
        "libtv-tv-tool-row",
        "required_labels_missing",
        "intent_clicks",
        "active_tool_visible",
        "receipt_text",
        "[data-toolbox-intent='angles']",
        "[data-toolbox-intent='motion']",
        "[data-toolbox-intent='keyframes']",
        "本地工具意图已登记",
        "未创建真实任务",
        "未启动 provider",
        "provider_request_urls",
        "not human acceptance",
        "not provider smoke",
    ]:
        assert marker in source
