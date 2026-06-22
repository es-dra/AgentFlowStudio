from __future__ import annotations

from pathlib import Path


SITE_ROOT = Path("apps/site")


def test_site_homepage_mounts_social_square_without_internal_terms() -> None:
    index = (SITE_ROOT / "index.html").read_text(encoding="utf-8")

    assert 'href="#social-square"' in index
    assert 'id="social-square"' in index
    assert 'data-social-square-list' in index
    assert 'data-social-square-form' in index
    assert 'src="/site/social-square.js"' in index
    assert 'href="/site/styles/social-square.css"' in index
    assert "社交广场" in index
    assert "发布需求" in index
    assert "承接需求" in index
    assert "provider raw" not in index.lower()
    assert "Runtime Service" not in index


def test_social_square_frontend_script_is_same_origin_and_auth_gated() -> None:
    script = (SITE_ROOT / "social-square.js").read_text(encoding="utf-8")

    assert 'fetch("/community/requests"' in script
    assert "/accept" in script
    assert "/submit" in script
    assert "afs_auth_session_token" in script
    assert "Authorization" in script
    assert "http://" not in script
    assert "https://" not in script
    assert "provider raw" not in script.lower()


def test_social_square_styles_are_small_and_non_overlapping() -> None:
    styles = (SITE_ROOT / "styles" / "social-square.css").read_text(encoding="utf-8")

    assert len(styles.splitlines()) <= 300
    assert ".social-square" in styles
    assert ".square-grid" in styles
    assert "grid-template-columns" in styles
    assert "position: absolute" not in styles
    for marker in ("api_key", "signed_url", "provider raw", "d:\\", "c:\\"):
        assert marker not in styles.lower()
