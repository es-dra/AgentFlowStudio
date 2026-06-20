from __future__ import annotations

import os

from tools.studio_asset_context_browser_qa_support import BrowserQaFakeLLMRegistry, _merge_no_proxy, browser_qa_provider_context


def test_browser_qa_no_proxy_keeps_local_runtime_direct() -> None:
    merged = _merge_no_proxy("example.test")

    for expected in ("example.test", "127.0.0.1", "localhost", "::1"):
        assert expected in merged.split(",")


def test_browser_qa_no_proxy_does_not_duplicate_existing_entries() -> None:
    merged = _merge_no_proxy("localhost,127.0.0.1")

    assert merged.split(",").count("localhost") == 1
    assert merged.split(",").count("127.0.0.1") == 1


def test_browser_qa_stub_llm_context_is_temporary(monkeypatch) -> None:
    monkeypatch.setenv("AFS_BROWSER_QA_STUB_LLM", "true")
    monkeypatch.delenv("AFS_ALLOW_REMOTE_LLM", raising=False)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")

    with browser_qa_provider_context():
        assert BrowserQaFakeLLMRegistry().dispatch("llm", "prompt_optimizer", object())["text"].startswith("意图：")
        assert "AFS_ALLOW_REMOTE_LLM" in os.environ
        assert "AFS_ALLOW_REMOTE_IMAGE" not in os.environ

    assert "AFS_ALLOW_REMOTE_LLM" not in os.environ
    assert os.environ["AFS_ALLOW_REMOTE_IMAGE"] == "true"
