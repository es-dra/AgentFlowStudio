from __future__ import annotations

import json
import subprocess
from pathlib import Path


WEB_ROOT = Path("apps/web")
WEB_FIXTURE_ROOT = Path("tests/fixtures/web_static_artifact_viewer/product_run")


def _read_web_file(name: str) -> str:
    return (WEB_ROOT / name).read_text(encoding="utf-8")


def _read_fixture_file(name: str) -> str:
    return (WEB_FIXTURE_ROOT / name).read_text(encoding="utf-8")


def test_static_viewer_html_declares_local_artifact_workbench() -> None:
    html = _read_web_file("index.html")

    assert 'href="styles.css"' in html
    assert 'src="app.js"' in html
    assert 'type="module"' in html
    assert 'lang="zh-CN"' in html
    assert 'type="file"' in html
    assert "multiple" in html
    assert 'id="language-toggle"' in html
    assert 'class="stat-strip"' in html
    assert "本地只读验收台" in html
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
    ui_copy = _read_web_file("ui-copy.js")
    render_helpers = _read_web_file("render-helpers.js")
    combined_source = app + artifact_workspace + ui_copy + render_helpers

    assert 'from "./artifact-workspace.js"' in app
    assert 'from "./ui-copy.js"' in app
    assert 'from "./render-helpers.js"' in app
    assert "ARTIFACT_ALIASES" in artifact_workspace
    assert "finished_package_manifest.json" in artifact_workspace
    assert "package_manifest.json" in artifact_workspace
    assert "package_manifest" in artifact_workspace
    assert "detectArtifactType" in artifact_workspace
    assert "normalizeWorkspace" in artifact_workspace
    for artifact_type in [
        "run_manifest",
        "package_manifest",
        "quality_report",
        "review_report",
        "delivery_readiness",
        "markdown_report",
    ]:
        assert artifact_type in combined_source


def test_static_viewer_real_fixture_covers_supported_artifact_shapes() -> None:
    expected_files = [
        "run_manifest.json",
        "finished_package_manifest.json",
        "quality_report.json",
        "review_report.json",
        "delivery_readiness.json",
        "package_report.md",
        "delivery_readiness.md",
    ]

    for name in expected_files:
        assert (WEB_FIXTURE_ROOT / name).is_file()

    assert '"artifact_index"' in _read_fixture_file("run_manifest.json")
    assert '"assets"' in _read_fixture_file("finished_package_manifest.json")
    assert '"checks"' in _read_fixture_file("quality_report.json")
    assert '"sections"' in _read_fixture_file("review_report.json")
    assert '"runs"' in _read_fixture_file("delivery_readiness.json")
    assert "<script>" in _read_fixture_file("package_report.md")


def test_static_viewer_declares_m11_artifact_classes_and_schema_warnings() -> None:
    artifact_workspace = _read_web_file("artifact-workspace.js")
    app = _read_web_file("app.js")

    for source_token in [
        "artifactClass",
        "participatesInSummary",
        "schemaWarnings",
        "known_contract",
        "unknown_json",
        "unsupported_file",
        "parsed but not included in summary",
        "schema_version missing",
    ]:
        assert source_token in artifact_workspace

    assert "artifact.artifactClass" in app
    assert "artifact.schemaWarnings" in app


def test_static_viewer_declares_m12_chinese_copy_and_in_memory_language_switch() -> None:
    app = _read_web_file("app.js")
    ui_copy = _read_web_file("ui-copy.js")
    render_helpers = _read_web_file("render-helpers.js")

    assert 'language: "zh"' in app
    assert 'state.language = state.language === "zh" ? "en" : "zh"' in app
    assert "localStorage" not in app + ui_copy + render_helpers
    assert "把 NarratoCut 的运行结果" in ui_copy
    assert "通过 pass" in ui_copy
    assert "警告 warning" in ui_copy
    assert "未知 JSON unknown_json" not in ui_copy
    assert "未找到详细检查项" in ui_copy
    assert "statusPill" in render_helpers
    assert "normalizeStatus" in render_helpers


def test_static_viewer_normalizes_real_fixture_and_non_contract_inputs() -> None:
    script = """
import { parseFiles, normalizeWorkspace } from "./apps/web/artifact-workspace.js";
import { readFile } from "node:fs/promises";
import { join } from "node:path";

const fixtureRoot = "tests/fixtures/web_static_artifact_viewer/product_run";
const artifactNames = [
  "run_manifest.json",
  "finished_package_manifest.json",
  "quality_report.json",
  "review_report.json",
  "delivery_readiness.json",
  "package_report.md",
];
const fixtureFiles = await Promise.all(artifactNames.map(async (name) => ({
  name,
  text: async () => await readFile(join(fixtureRoot, name), "utf8"),
})));
const extraFiles = [
  { name: "notes.json", text: async () => JSON.stringify({ hello: "world" }) },
  { name: "notes.txt", text: async () => "plain text note" },
  { name: "bad.json", text: async () => "{" },
];
const artifacts = await parseFiles([...fixtureFiles, ...extraFiles]);
const workspace = normalizeWorkspace(artifacts);
const partial = normalizeWorkspace(await parseFiles([fixtureFiles[0]]));

console.log(JSON.stringify({
  classes: Object.fromEntries(artifacts.map((artifact) => [artifact.fileName, artifact.artifactClass])),
  schemaStatuses: Object.fromEntries(artifacts.map((artifact) => [artifact.fileName, artifact.schemaStatus])),
  warningText: workspace.warnings.join("\\n"),
  errorText: workspace.errors.join("\\n"),
  runId: workspace.run?.runId,
  packageId: workspace.package?.packageId,
  qualityStatus: workspace.quality?.status,
  reviewStatus: workspace.review?.status,
  readinessStatus: workspace.readiness?.status,
  reportCount: workspace.reports.length,
  partialRunId: partial.run?.runId,
  partialPackageLoaded: Boolean(partial.package),
}));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["classes"]["run_manifest.json"] == "known_contract"
    assert payload["classes"]["finished_package_manifest.json"] == "known_contract"
    assert payload["classes"]["notes.json"] == "unknown_json"
    assert payload["classes"]["notes.txt"] == "unsupported_file"
    assert payload["classes"]["bad.json"] == "invalid"
    assert payload["schemaStatuses"]["run_manifest.json"] == "warning"
    assert payload["schemaStatuses"]["quality_report.json"] == "warning"
    assert "schema_version missing" in payload["warningText"]
    assert "parsed but not included in summary" in payload["warningText"]
    assert "unsupported_file" in payload["warningText"]
    assert "bad.json" in payload["errorText"]
    assert payload["runId"] == "package_run_fixture"
    assert payload["packageId"] == "demo_package"
    assert payload["qualityStatus"] == "pass"
    assert payload["reviewStatus"] == "pass"
    assert payload["readinessStatus"] == "fail"
    assert payload["reportCount"] == 1
    assert payload["partialRunId"] == "package_run_fixture"
    assert payload["partialPackageLoaded"] is False


def test_static_viewer_rendering_consumes_normalized_workspace_not_raw_payloads() -> None:
    app = _read_web_file("app.js")

    assert "normalizeWorkspace(artifacts)" in app
    assert "renderWorkspace(state.workspace" in app
    for raw_contract_fragment in [
        ".payload",
        "artifact_index",
        "schema_version",
        "finished_package_manifest",
    ]:
        assert raw_contract_fragment not in app


def test_static_viewer_app_keeps_local_read_only_boundary() -> None:
    app = (
        _read_web_file("app.js")
        + _read_web_file("artifact-workspace.js")
        + _read_web_file("ui-copy.js")
        + _read_web_file("render-helpers.js")
    )
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
    app = _read_web_file("app.js") + _read_web_file("render-helpers.js")

    assert "textContent" in app
    assert ".innerHTML" not in app
    assert "script" not in app.lower()


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
        "unknown_json",
        "unsupported_file",
        "schema_version",
        "warning",
        "no video preview",
        "no provider config",
        "no workflow execution",
    ]:
        assert phrase in readme

    assert "m1.2" in readme
    assert "default chinese" in readme
    assert "in-memory" in readme
