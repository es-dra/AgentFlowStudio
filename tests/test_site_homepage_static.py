from __future__ import annotations

from pathlib import Path


SITE_ROOT = Path("apps/site")


def test_site_homepage_is_distinct_from_studio_workspace() -> None:
    index = (SITE_ROOT / "index.html").read_text(encoding="utf-8")

    assert SITE_ROOT.exists()
    assert '<html lang="zh-CN">' in index
    assert "<title>AFS Studio" in index
    assert 'class="brand" href="/site/"' in index
    assert 'href="/studio/"' in index
    assert 'href="/site/styles/site.css"' in index
    assert 'href="/site/styles/site-preview.css"' in index
    assert 'href="/site/styles/social-square.css"' in index
    assert 'href="/site/styles/site-responsive.css"' in index
    assert 'src="/site/site.js"' in index
    assert 'src="/site/social-square.js"' in index
    assert "data-auth-action" in index
    assert "专业 AI 视频创作工作台" in index
    assert "新建视频项目" in index
    assert "hero-stage" in index
    assert "featured-work" in index
    assert "template-stack" in index
    assert "project-lane" in index
    assert "最近作品" in index
    assert "雨夜追踪镜头" in index
    assert "社交广场" in index
    assert "查看底层算法边界" in index
    assert "提示词智能优化" in index
    assert "上下文智能调度" in index
    assert "质量反馈与漂移控制" in index
    assert 'class="algorithm-section"' not in index
    assert "Runtime Service" not in index
    assert "provider raw" not in index


def test_site_homepage_styles_remain_small_and_safe() -> None:
    style_paths = sorted((SITE_ROOT / "styles").glob("*.css"))
    combined = "\n".join(path.read_text(encoding="utf-8") for path in style_paths).lower()

    assert {path.name for path in style_paths} == {
        "site.css",
        "site-preview.css",
        "site-responsive.css",
        "social-square.css",
    }
    for path in style_paths:
        assert len(path.read_text(encoding="utf-8").splitlines()) <= 300, path

    for marker in ("api_key", "token", "signed_url", "provider raw", "d:\\", "c:\\"):
        assert marker not in combined


def test_site_homepage_auth_entry_script_is_safe_and_status_only() -> None:
    script = (SITE_ROOT / "site.js").read_text(encoding="utf-8")

    assert 'fetch("/auth/status"' in script
    assert "data-auth-action" in script
    assert "entryLabel" in script
    assert "afs_auth_session_token" in script
    assert "Authorization" in script
    assert "http://" not in script
    assert "https://" not in script
    assert "provider raw" not in script.lower()


def test_site_homepage_preview_uses_non_overlapping_flow_layout() -> None:
    index = (SITE_ROOT / "index.html").read_text(encoding="utf-8")
    preview = (SITE_ROOT / "styles" / "site-preview.css").read_text(encoding="utf-8")
    responsive = (SITE_ROOT / "styles" / "site-responsive.css").read_text(encoding="utf-8")

    assert "hero-stage" in index
    assert "模板 01" in index
    assert "当前项目" in index
    assert "grid-template-columns: minmax(0, 1.1fr) minmax(230px, 0.7fr);" in preview
    assert ".template-stack" in preview
    assert ".project-lane" in preview
    assert ".technical-details" in (SITE_ROOT / "styles" / "site.css").read_text(encoding="utf-8")
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in preview
    template_card_rule = preview.split(".template-card {", 1)[1].split(".template-card.active", 1)[0]
    assert "position: absolute;" not in template_card_rule
    assert "width: 210px;" not in preview
    assert "left: 46px;" not in preview
    assert "right: 42px;" not in preview
    assert "bottom: 72px;" not in preview
    assert "grid-template-columns: 1fr;" in responsive
    assert ".hero-stage" in responsive
    assert ".project-lane" in responsive
