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


def test_site_homepage_preview_uses_non_overlapping_flow_layout() -> None:
    index = (SITE_ROOT / "index.html").read_text(encoding="utf-8")
    preview = (SITE_ROOT / "styles" / "site-preview.css").read_text(encoding="utf-8")
    responsive = (SITE_ROOT / "styles" / "site-responsive.css").read_text(encoding="utf-8")

    assert "preview-flow" in index
    assert "本次系统参考" in index
    assert "grid-template-columns: 118px minmax(0, 1fr) 210px;" in preview
    assert ".preview-flow" in preview
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in preview
    assert "position: absolute;" not in preview.split(".node-card", 1)[1].split(".node-card span", 1)[0]
    assert "width: 210px;" not in preview
    assert "left: 46px;" not in preview
    assert "right: 42px;" not in preview
    assert "bottom: 72px;" not in preview
    assert "grid-template-columns: 1fr;" in responsive
    assert ".node-link" in responsive
    assert "display: none;" in responsive
