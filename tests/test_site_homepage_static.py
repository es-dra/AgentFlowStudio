from __future__ import annotations

from pathlib import Path


SITE_ROOT = Path("apps/site")


def test_site_homepage_is_distinct_from_studio_workspace() -> None:
    index = (SITE_ROOT / "index.html").read_text(encoding="utf-8")

    assert SITE_ROOT.exists()
    assert '<html lang="zh-CN">' in index
    assert "<title>AFS Studio" in index
    assert 'href="/studio/"' in index
    assert 'href="/site/styles/site.css"' in index
    assert 'href="/site/styles/site-preview.css"' in index
    assert 'href="/site/styles/site-responsive.css"' in index
    assert "AI 内容生产的操作层" in index
    assert "product-preview" in index
    assert "提示词智能优化" in index
    assert "上下文智能调度" in index
    assert "质量反馈与漂移控制" in index
    assert "Runtime Service" not in index
    assert "provider raw" not in index


def test_site_homepage_styles_remain_small_and_safe() -> None:
    style_paths = sorted((SITE_ROOT / "styles").glob("*.css"))
    combined = "\n".join(path.read_text(encoding="utf-8") for path in style_paths).lower()

    assert {path.name for path in style_paths} == {
        "site.css",
        "site-preview.css",
        "site-responsive.css",
    }
    for path in style_paths:
        assert len(path.read_text(encoding="utf-8").splitlines()) <= 300, path

    for marker in ("api_key", "token", "signed_url", "provider raw", "d:\\", "c:\\"):
        assert marker not in combined
