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
    assert ".mp4,.webm,.mov" in html
    assert 'id="language-toggle"' in html
    assert "stat-strip" in html
    assert "内容生产验收" in html
    assert "<main" in html
    for landmark in [
        'id="artifact-inventory"',
        'id="summary-panel"',
        'id="inspector-panel"',
        'id="evidence-map-panel"',
        'id="risk-ledger-panel"',
        'id="asset-ledger-panel"',
        'id="video-preview-panel"',
        'id="feedback-panel"',
        'id="report-preview"',
    ]:
        assert landmark in html


def test_static_viewer_app_declares_artifact_aliases_and_normalized_types() -> None:
    app = _read_web_file("app.js")
    artifact_workspace = _read_web_file("artifact-workspace.js")
    artifact_contracts = _read_web_file("artifact-contracts.js")
    artifact_ledgers = _read_web_file("artifact-ledgers.js")
    ui_copy = _read_web_file("ui-copy.js")
    render_helpers = _read_web_file("render-helpers.js")
    combined_source = app + artifact_workspace + artifact_contracts + artifact_ledgers + ui_copy + render_helpers

    assert 'from "./artifact-workspace.js"' in app
    assert 'from "./ui-copy.js"' in app
    assert 'from "./render-helpers.js"' in app
    assert "ARTIFACT_ALIASES" in artifact_contracts
    assert "finished_package_manifest.json" in artifact_contracts
    assert "package_manifest.json" in artifact_contracts
    assert "package_manifest" in artifact_contracts
    assert "detectArtifactType" in artifact_workspace
    assert "normalizeWorkspace" in artifact_workspace
    for artifact_type in [
        "run_manifest",
        "package_manifest",
        "quality_report",
        "review_report",
        "delivery_readiness",
        "markdown_report",
        "selection_diagnostics",
        "highlight_score_report",
        "candidate_windows",
        "clip_plan",
        "real_slice_manifest",
        "final_video_manifest",
        "subtitle_manifest",
        "audio_mix_manifest",
        "cover_manifest",
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
    artifact_contracts = _read_web_file("artifact-contracts.js")
    combined_source = artifact_workspace + artifact_contracts
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
        assert source_token in combined_source

    assert "artifact.artifactClass" in app
    assert "artifact.schemaWarnings" in app


def test_static_viewer_declares_m12_chinese_copy_and_in_memory_language_switch() -> None:
    app = _read_web_file("app.js")
    ui_copy = _read_web_file("ui-copy.js")
    render_helpers = _read_web_file("render-helpers.js")

    assert 'language: "zh"' in app
    assert 'state.language = state.language === "zh" ? "en" : "zh"' in app
    assert "localStorage" not in app + ui_copy + render_helpers
    assert "先看成品能否交付，再看证据和风险。" in ui_copy
    assert "交付总览" in ui_copy
    assert "审查 Inspector" in ui_copy
    assert "报告审阅" in ui_copy
    assert "Contract Inspector" in ui_copy
    assert "通过 pass" in ui_copy
    assert "警告 warning" in ui_copy
    assert "未知 unknown" in ui_copy
    assert "未找到详细检查项" in ui_copy
    assert "statusPill" in render_helpers
    assert "normalizeStatus" in render_helpers


def test_static_viewer_declares_m121_acceptance_metrics_and_empty_state_boundary() -> None:
    ui_copy = _read_web_file("ui-copy.js")
    artifact_workspace = _read_web_file("artifact-workspace.js")

    for phrase in ["已选文件", "参与验收", "风险提示", "解析错误"]:
        assert phrase in ui_copy

    assert "summaryArtifacts.length > 0" in artifact_workspace
    assert "Missing recommended artifact" in artifact_workspace


def test_static_viewer_declares_m14_productive_review_workbench_layout() -> None:
    html = _read_web_file("index.html")
    css = _read_web_file("styles.css")
    ui_copy = _read_web_file("ui-copy.js")

    for token in [
        'class="topbar"',
        'class="workflow-rail"',
        'class="content-stage"',
        'class="review-rail"',
        'id="recommended-artifacts"',
        'id="contract-inspector"',
    ]:
        assert token in html

    assert 'class="hero"' not in html
    assert "交付总览" in ui_copy
    assert "推荐文件组" in ui_copy
    assert "Contract Inspector" in ui_copy
    assert "topbar" in css
    assert "content-stage" in css
    assert "review-rail" in css


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
const empty = normalizeWorkspace([]);

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
  partialWarnings: partial.warnings.join("\\n"),
  emptyWarningCount: empty.warnings.length,
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
    assert "Missing recommended artifact" in payload["partialWarnings"]
    assert payload["emptyWarningCount"] == 0


def test_static_viewer_normalizes_expanded_artifact_universe_ledgers_and_local_video() -> None:
    script = """
import { parseFiles, normalizeWorkspace } from "./apps/web/artifact-workspace.js";

const files = [
  { name: "selection_diagnostics.json", text: async () => JSON.stringify({ status: "warning", warnings: ["few strong hooks"], rejection_reason_counts: { duplicate: 2 } }) },
  { name: "highlight_score_report.json", text: async () => JSON.stringify({ status: "passed", selected_candidates: [{ candidate_id: "cand_1", final_score: 0.92 }], warnings: ["near miss rejected"] }) },
  { name: "candidate_windows.json", text: async () => JSON.stringify({ status: "succeeded", candidates: [{ candidate_id: "cand_1", start_sec: 1, end_sec: 5 }] }) },
  { name: "clip_plan.json", text: async () => JSON.stringify({ status: "succeeded", clip_plan_id: "clip_plan_1", segments: [{ output_name: "clips/cand_1.mp4", start_sec: 1, end_sec: 5 }] }) },
  { name: "real_slice_manifest.json", text: async () => JSON.stringify({ status: "succeeded", clips: [{ path: "clips/cand_1.mp4", exists: true }] }) },
  { name: "final_video_manifest.json", text: async () => JSON.stringify({ status: "succeeded", output_path: "final_video.mp4", duration_sec: 18.2 }) },
  { name: "subtitle_manifest.json", text: async () => JSON.stringify({ status: "succeeded", subtitle_path: "subtitles.srt", timeline: "final_video" }) },
  { name: "audio_mix_manifest.json", text: async () => JSON.stringify({ status: "succeeded", output_video_path: "final_video_with_bgm.mp4", bgm_path: "bgm.mp3" }) },
  { name: "cover_manifest.json", text: async () => JSON.stringify({ status: "succeeded", cover_path: "cover.jpg" }) },
  { name: "delivery_readiness.json", text: async () => JSON.stringify({ status: "fail", summary: { total_runs: 1, failed: 1 }, runs: [{ run_id: "package_run", status: "fail", failures: ["missing highlight_score_report.json"], warnings: ["review: 4 warnings"] }] }) },
  { name: "finished_package_manifest.json", text: async () => JSON.stringify({ schema_version: "0.1", status: "succeeded", package_id: "pkg", assets: [], evidence: { final_video_manifest: "upstream/final_video_manifest.json", clip_plan: "upstream/clip_plan.json" } }) },
  { name: "review.mp4", type: "video/mp4", text: async () => "not read for video" },
];
const workspace = normalizeWorkspace(await parseFiles(files));

console.log(JSON.stringify({
  classes: Object.fromEntries(workspace.artifacts.map((artifact) => [artifact.fileName, artifact.artifactClass])),
  evidenceTypes: workspace.evidenceMap.map((item) => item.artifactType),
  riskText: workspace.riskLedger.map((item) => item.message).join("\\n"),
  assetRoles: workspace.assetLedger.map((item) => item.role),
  videoNames: workspace.videos.map((item) => item.fileName),
}));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    for artifact_type in [
        "selection_diagnostics",
        "highlight_score_report",
        "candidate_windows",
        "clip_plan",
        "real_slice_manifest",
        "final_video_manifest",
        "subtitle_manifest",
        "audio_mix_manifest",
        "cover_manifest",
    ]:
        assert artifact_type in payload["evidenceTypes"]

    assert payload["classes"]["review.mp4"] == "local_media"
    assert payload["videoNames"] == ["review.mp4"]
    assert "few strong hooks" in payload["riskText"]
    assert "near miss rejected" in payload["riskText"]
    assert "missing highlight_score_report.json" in payload["riskText"]
    assert "upstream/final_video_manifest.json" in payload["assetRoles"] or "final_video" in payload["assetRoles"]
    assert "final_video" in payload["assetRoles"]
    assert "subtitle" in payload["assetRoles"]
    assert "cover" in payload["assetRoles"]


def test_static_viewer_uses_package_evidence_and_multiple_report_tabs() -> None:
    artifact_ledgers = _read_web_file("artifact-ledgers.js")
    app = _read_web_file("app.js")
    html = _read_web_file("index.html")

    assert "package_manifest.evidence" in artifact_ledgers
    assert "addDeliveryReadinessRisks" in artifact_ledgers
    assert "addReviewSectionRisks" in artifact_ledgers
    assert 'id="report-tabs"' in html
    assert "renderReportTabs" in app
    assert "selectedReport" in app
    assert "const currentReport = selectedReport(workspace)" in app


def test_static_viewer_rendering_consumes_normalized_workspace_not_raw_payloads() -> None:
    app = _read_web_file("app.js")

    assert "normalizeWorkspace(artifacts)" in app
    assert "renderWorkspace(state.workspace" in app
    assert "workspace.evidenceMap" in app
    assert "workspace.riskLedger" in app
    assert "workspace.assetLedger" in app
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
        + _read_web_file("artifact-contracts.js")
        + _read_web_file("artifact-ledgers.js")
        + _read_web_file("artifact-values.js")
        + _read_web_file("video-preview.js")
        + _read_web_file("feedback-event.js")
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
        "FileSystemWritableFileStream",
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


def test_static_viewer_video_preview_is_explicit_local_file_only() -> None:
    html = _read_web_file("index.html")
    video_preview = _read_web_file("video-preview.js")
    app = _read_web_file("app.js")

    assert ".mp4,.webm,.mov" in html
    assert "URL.createObjectURL" in video_preview
    assert "URL.revokeObjectURL" in video_preview
    assert "canPlayType" in video_preview
    assert "video/mp4" in video_preview
    assert "video/webm" in video_preview
    assert "video/quicktime" in video_preview
    assert "workspace.videos" in app
    assert "manifest" not in video_preview.lower()


def test_static_viewer_feedback_event_copy_does_not_write_files() -> None:
    html = _read_web_file("index.html")
    feedback = _read_web_file("feedback-event.js")
    app = _read_web_file("app.js")

    assert "feedback_event" in feedback
    assert "narratocut_web_static_viewer" in feedback
    assert "navigator.clipboard.writeText" in feedback
    assert "feedback-output" in html
    assert "textarea" in html
    assert "renderFeedbackArtifacts" in app
    for forbidden in ["showSaveFilePicker", "createWritable", "fetch(", "sendBeacon"]:
        assert forbidden not in feedback


def test_static_viewer_readme_documents_boundaries() -> None:
    readme = _read_web_file("README.md").lower()

    for phrase in [
        "read-only",
        "local-only",
        "no upload",
        "no backend execution",
        "no persistence",
        "feedback event copy",
        "does not scan directories",
        "unknown_json",
        "unsupported_file",
        "schema_version",
        "warning",
        "local video preview",
        "no provider config",
        "no workflow execution",
        "m1.2.1",
        "m1.3",
        "m1.5",
        "m2",
    ]:
        assert phrase in readme

    assert "m1.2" in readme
    assert "default chinese" in readme
    assert "in-memory" in readme
