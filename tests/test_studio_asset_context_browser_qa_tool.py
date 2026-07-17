from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = REPO_ROOT / "tools"
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from tools import studio_asset_context_browser_qa as browser_qa
from tools import studio_asset_context_browser_qa_support as browser_qa_support


def test_browser_qa_screenshot_defaults_next_to_report(tmp_path) -> None:
    report = tmp_path / "evidence" / "browser_report.json"

    screenshot = browser_qa.resolve_screenshot_path(report, "")

    assert screenshot == report.with_suffix(".png")


def test_browser_qa_screenshot_can_be_overridden(tmp_path) -> None:
    report = tmp_path / "browser_report.json"
    explicit = tmp_path / "screens" / "safe.png"

    screenshot = browser_qa.resolve_screenshot_path(report, str(explicit))

    assert screenshot == Path(explicit).resolve()


def test_prompt_optimization_summary_counts_live_llm_calls() -> None:
    summary = browser_qa.prompt_optimization_summary(
        [
            {"provider_calls_started": True},
            {"provider_calls_started": False},
            {"provider_calls_started": True},
        ]
    )

    assert summary == {
        "prompt_optimization_count": 3,
        "prompt_optimization_provider_calls_started_count": 2,
        "live_llm_provider_smoke": True,
    }


def test_prompt_optimization_summary_marks_gate_closed() -> None:
    summary = browser_qa.prompt_optimization_summary(
        [
            {"provider_calls_started": False},
            {},
        ]
    )

    assert summary == {
        "prompt_optimization_count": 2,
        "prompt_optimization_provider_calls_started_count": 0,
        "live_llm_provider_smoke": False,
    }


def test_browser_qa_proxy_closes_all_remote_provider_gates_by_default(monkeypatch) -> None:
    for key in browser_qa_support.REMOTE_PROVIDER_GATES:
        monkeypatch.setenv(key, "true")

    with browser_qa_support.remote_provider_gates_closed():
        for key in browser_qa_support.REMOTE_PROVIDER_GATES:
            assert key not in browser_qa_support.os.environ

    for key in browser_qa_support.REMOTE_PROVIDER_GATES:
        assert browser_qa_support.os.environ[key] == "true"
    assert "AFS_ALLOW_REMOTE_VIDEO" in browser_qa_support.REMOTE_PROVIDER_GATES
    assert "AFS_ALLOW_REMOTE_AUDIO" in browser_qa_support.REMOTE_PROVIDER_GATES


def test_browser_qa_proxy_can_keep_explicit_llm_gate(monkeypatch) -> None:
    for key in browser_qa_support.REMOTE_PROVIDER_GATES:
        monkeypatch.setenv(key, "true")

    with browser_qa_support.remote_provider_gates_closed(allow_live_llm=True):
        assert browser_qa_support.os.environ["AFS_ALLOW_REMOTE_LLM"] == "true"
        for key in browser_qa_support.MEDIA_PROVIDER_GATES:
            assert key not in browser_qa_support.os.environ

    for key in browser_qa_support.REMOTE_PROVIDER_GATES:
        assert browser_qa_support.os.environ[key] == "true"
