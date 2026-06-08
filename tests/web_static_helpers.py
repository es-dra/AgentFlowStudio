from __future__ import annotations

from pathlib import Path


WEB_ROOT = Path("apps/web")
WEB_FIXTURE_ROOT = Path("tests/fixtures/web_static_artifact_viewer/product_run")


def read_web_file(name: str) -> str:
    return (WEB_ROOT / name).read_text(encoding="utf-8")


def read_web_shell_source() -> str:
    return "\n".join(
        read_web_file(name)
        for name in [
            "index.html",
            "app-shell-template.js",
            "app-shell-review-template.js",
            "app-shell-memory-template.js",
        ]
    )


def read_fixture_file(name: str) -> str:
    return (WEB_FIXTURE_ROOT / name).read_text(encoding="utf-8")
