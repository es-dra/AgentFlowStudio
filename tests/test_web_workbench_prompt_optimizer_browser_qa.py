from __future__ import annotations

from pathlib import Path


SCRIPT = Path("tools/workbench_prompt_optimizer_browser_qa.py")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_prompt_optimizer_browser_qa_script_contract() -> None:
    assert SCRIPT.exists()
    source = _read(SCRIPT)

    for marker in [
        "agentflow_workbench_prompt_optimizer_browser_qa",
        "--base-url",
        "--output-dir",
        "--viewport",
        "VIEWPORTS",
        "desktop",
        "mobile",
        "prompt-optimizations",
        "data-action='optimize-current-prompt'",
        "已按影视结构优化",
        "已结合当前项目风格",
        "optimized_prompt_visible",
        "runtime_optimizer_request_urls",
        "provider_request_urls",
        "not human acceptance",
        "not provider smoke",
    ]:
        assert marker in source

    for hidden_label in ["Runtime 已优化", "Provider 未启动", "本地规则降级"]:
        assert hidden_label not in source


def test_prompt_optimizer_browser_qa_keeps_secret_and_provider_boundaries() -> None:
    source = _read(SCRIPT)

    for marker in ["api_key", "signed_url", "provider_config", "AFS_ALLOW_REMOTE", r"[A-Z]:\\"]:
        assert marker in source
