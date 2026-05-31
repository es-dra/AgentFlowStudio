from __future__ import annotations

import json
import subprocess


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


def test_static_viewer_recognizes_loulan_b01_feedback_loop_gate() -> None:
    script = """
import { parseFiles, normalizeWorkspace } from "./apps/web/artifact-workspace.js";
import { buildMemoryWorkbenchView, memorySourceForArtifacts } from "./apps/web/memory-workbench-controller.js";

const gate = {
  schema_version: "0.1.0",
  artifact_type: "loulan_afs_b01_feedback_loop_gate",
  status: "blocked_pending_human_review",
  provider_calls_started: false,
  writes_long_term_memory: false,
  human_acceptance_recorded: false,
  media_generation_started: false,
  current_gate_summary: {
    b01_decision_items: 5,
    pending_decisions: 5,
    approved_decisions: 0,
    repair_requested: 0,
    rejected_decisions: 0,
    validation_status: "blocked_pending_human_review",
    apply_status: "blocked_validation_not_ready",
    afs_import_ready: false,
    context_projection_ready: false
  }
};
const artifacts = await parseFiles([
  { name: "afs_b01_feedback_loop_gate.json", text: async () => JSON.stringify(gate) },
]);
const workspace = normalizeWorkspace(artifacts);
const view = buildMemoryWorkbenchView(workspace, memorySourceForArtifacts(artifacts));

console.log(JSON.stringify({
  artifactType: artifacts[0].artifactType,
  artifactClass: artifacts[0].artifactClass,
  sourceRole: artifacts[0].sourceRole,
  memoryBundleCount: workspace.memoryBundle.length,
  sourceStatus: view.source_status,
  inspector: view.artifact_inspector[0],
}));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["artifactType"] == "loulan_afs_b01_feedback_loop_gate"
    assert payload["artifactClass"] == "known_contract"
    assert payload["sourceRole"] == "Loulan B01 feedback loop gate"
    assert payload["memoryBundleCount"] == 1
    assert payload["sourceStatus"]["label"] == "Selected files"
    assert payload["inspector"]["title"] == "Loulan B01 feedback loop gate"
    assert payload["inspector"]["status"] == "blocked_pending_human_review"
    facts = {item["label"]: item["value"] for item in payload["inspector"]["facts"]}
    assert facts["pending_decisions"] == "5"
    assert facts["validation_status"] == "blocked_pending_human_review"
    assert facts["apply_status"] == "blocked_validation_not_ready"
    assert facts["context_projection_ready"] == "false"
    assert facts["human_acceptance_recorded"] == "false"
    assert facts["provider_calls_started"] == "false"


def test_static_viewer_recognizes_loulan_b01_decision_crosswalk() -> None:
    script = """
import { parseFiles, normalizeWorkspace } from "./apps/web/artifact-workspace.js";
import { buildMemoryWorkbenchView, memorySourceForArtifacts } from "./apps/web/memory-workbench-controller.js";

const crosswalk = {
  schema_version: "0.1.0",
  artifact_type: "loulan_afs_b01_decision_crosswalk",
  status: "blocked_pending_human_review",
  provider_calls_started: false,
  writes_long_term_memory: false,
  human_acceptance_recorded: false,
  media_generation_started: false,
  decision_layers: [
    { layer_id: "loulan_local_b01_shot_gate", decision_count: 5, pending_count: 5, target_refs: ["shot:B01-S01", "shot:B01-S02", "shot:B01-S03", "shot:B01-S04", "shot:B01-S05"] },
    { layer_id: "afs_b01_import_gate", decision_count: 7, pending_count: 7, target_refs: ["shot:B01-S01", "shot:B01-S02", "shot:B01-S03", "shot:B01-S04", "shot:B01-S05", "character:zhou_tong_school_v1", "character:zhou_tong_qipao_front_v1"] },
    { layer_id: "afs_broader_decision_review_gate", decision_count: 47, pending_count: 47, target_refs_summary: { shot_slots: 5, asset_slots: 42 } }
  ]
};
const artifacts = await parseFiles([
  { name: "afs_b01_decision_crosswalk.json", text: async () => JSON.stringify(crosswalk) },
]);
const workspace = normalizeWorkspace(artifacts);
const view = buildMemoryWorkbenchView(workspace, memorySourceForArtifacts(artifacts));

console.log(JSON.stringify({
  artifactType: artifacts[0].artifactType,
  artifactClass: artifacts[0].artifactClass,
  sourceRole: artifacts[0].sourceRole,
  memoryBundleCount: workspace.memoryBundle.length,
  sourceStatus: view.source_status,
  inspector: view.artifact_inspector[0],
}));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["artifactType"] == "loulan_afs_b01_decision_crosswalk"
    assert payload["artifactClass"] == "known_contract"
    assert payload["sourceRole"] == "Loulan B01 decision crosswalk"
    assert payload["memoryBundleCount"] == 1
    assert payload["sourceStatus"]["label"] == "Selected files"
    assert payload["inspector"]["title"] == "Loulan B01 decision crosswalk"
    assert payload["inspector"]["status"] == "blocked_pending_human_review"
    facts = {item["label"]: item["value"] for item in payload["inspector"]["facts"]}
    assert facts["local_shot_decisions"] == "5"
    assert facts["afs_import_decisions"] == "7"
    assert facts["broader_review_decisions"] == "47"
    assert facts["human_acceptance_recorded"] == "false"
    assert facts["provider_calls_started"] == "false"
