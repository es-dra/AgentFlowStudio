from __future__ import annotations

from pathlib import Path


WEB_ROOT = Path("apps/web")


def _read_web_file(name: str) -> str:
    return (WEB_ROOT / name).read_text(encoding="utf-8")


def test_static_viewer_html_declares_local_artifact_workbench() -> None:
    html = _read_web_file("index.html")

    assert 'href="styles.css"' in html
    assert 'src="app.js"' in html
    assert 'type="module"' in html
    assert 'type="file"' in html
    assert "multiple" in html
    assert "<main" in html
    for landmark in [
        'id="artifact-inventory"',
        'id="summary-panel"',
        'id="inspector-panel"',
        'id="report-preview"',
    ]:
        assert landmark in html


def test_static_viewer_app_declares_artifact_aliases_and_normalized_types() -> None:
    app = _read_web_file("app.js")
    artifact_workspace = _read_web_file("artifact-workspace.js")
    combined_source = app + artifact_workspace

    assert 'from "./artifact-workspace.js"' in app
    assert "ARTIFACT_ALIASES" in artifact_workspace
    assert "finished_package_manifest.json" in artifact_workspace
    assert "package_manifest.json" in artifact_workspace
    assert "package_manifest" in artifact_workspace
    assert "detectArtifactType" in artifact_workspace
    assert "normalizeWorkspace" in artifact_workspace
    for artifact_type in [
        "run_manifest",
        "quality_report",
        "review_report",
        "delivery_readiness",
        "markdown_report",
    ]:
        assert artifact_type in combined_source


def test_static_viewer_app_keeps_local_read_only_boundary() -> None:
    app = _read_web_file("app.js") + _read_web_file("artifact-workspace.js")
    forbidden_patterns = [
        "fetch(",
        "XMLHttpRequest",
        "WebSocket",
        "EventSource",
        "navigator.sendBeacon",
        "showSaveFilePicker",
        "createWritable",
        "indexedDB",
        "localStorage.setItem",
        "OPENAI_API_KEY",
        "NARRATOCUT_OPENAI_API_KEY",
        "data/processed/runs/demo",
        "D:/Projects/NarratoCut/data",
        "D:\\Projects\\NarratoCut\\data",
    ]

    for pattern in forbidden_patterns:
        assert pattern not in app


def test_static_viewer_report_preview_uses_safe_text_rendering() -> None:
    app = _read_web_file("app.js")

    assert "textContent" in app
    assert "escapeHtml" in app
    assert ".innerHTML" not in app


def test_static_viewer_readme_documents_boundaries() -> None:
    readme = _read_web_file("README.md").lower()

    for phrase in [
        "read-only",
        "local-only",
        "no upload",
        "no backend execution",
        "no persistence",
        "feedback writing is out of scope",
        "does not scan directories",
    ]:
        assert phrase in readme
