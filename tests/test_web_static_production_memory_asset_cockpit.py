from __future__ import annotations

import json
import subprocess
from pathlib import Path

from agentflow.memory.production_asset_consistency_review import (
    ASSET_CONSISTENCY_REVIEW_FIXTURE_KIND,
    build_asset_consistency_review,
    write_asset_consistency_review,
)
from agentflow.memory.production_asset_profile_context_projection import (
    build_asset_profile_context_projection,
    write_asset_profile_context_projection,
)
from agentflow.memory.production_asset_profile_promotion import build_asset_profile_promotion_review
from tests.production_memory_asset_profile_promotion_helpers import (
    GENERATED_AT,
    asset_profiles_and_candidate,
)


def test_web_static_renders_asset_profile_context_projection_cockpit(tmp_path: Path) -> None:
    projection = _projection(tmp_path)
    write_asset_profile_context_projection(projection, tmp_path)
    projection_ref = json.dumps(str(tmp_path / "asset_profile_context_projection.json"))

    payload = _build_web_view_payload("asset_profile_context_projection.json", projection_ref)

    assert payload["artifactType"] == "agentflow_production_memory_asset_profile_context_projection"
    assert payload["artifactClass"] == "known_contract"
    assert payload["sourceRole"] == "production memory asset profile context projection"
    assert payload["memoryBundleCount"] == 1
    assert payload["hasProjection"] is True
    assert payload["projectFormat"] == "agentflow_production_memory_asset_profile_context_projection"
    assert payload["state"] == "asset context projection ready"
    assert "Asset profile context" in payload["laneTitles"]
    assert "Included profiles" in payload["laneTitles"]
    assert "Blocked profiles" in payload["laneTitles"]
    assert "Included profile refs" in payload["bundleTitles"]
    assert "Blocked profile refs" in payload["bundleTitles"]
    assert "Context policy" in payload["bundleTitles"]
    assert "asset-profile:character:lead:v2" in payload["memoryIds"]
    assert payload["nextPassStatus"] == "ready"
    assert payload["nextPassAction"] == "use_asset_profiles_for_next_task_context"
    assert "profile version inclusion authority:review ready" in payload["protocolControls"]
    assert "provider calls not started:review ready" in payload["protocolControls"]
    assert "Company KB write disabled:review ready" in payload["protocolControls"]
    assert "agentflow_production_memory_asset_profile_context_projection" in payload["inspectorTypes"]
    assert "projection_status:ready" in payload["inspectorFacts"]
    assert "included_refs:1" in payload["inspectorFacts"]
    assert "blocked_refs:1" in payload["inspectorFacts"]
    assert "writes_company_kb:false" in payload["inspectorFacts"]
    assert "provider_calls_started:false" in payload["inspectorFacts"]


def test_web_static_renders_asset_consistency_review_cockpit(tmp_path: Path) -> None:
    projection = _projection(tmp_path)
    review = build_asset_consistency_review(
        asset_profile_context_projection=projection,
        consistency_fixture=_fixture(projection),
        reviewed_at="2026-06-03T01:00:00+08:00",
    )
    write_asset_consistency_review(review, tmp_path)
    review_ref = json.dumps(str(tmp_path / "asset_consistency_review.json"))

    payload = _build_web_view_payload("asset_consistency_review.json", review_ref)

    assert payload["artifactType"] == "agentflow_production_memory_asset_consistency_review"
    assert payload["artifactClass"] == "known_contract"
    assert payload["sourceRole"] == "production memory asset consistency review"
    assert payload["memoryBundleCount"] == 1
    assert payload["hasConsistencyReview"] is True
    assert payload["projectFormat"] == "agentflow_production_memory_asset_consistency_review"
    assert payload["state"] == "asset consistency review ready"
    assert "Asset consistency review" in payload["laneTitles"]
    assert "Consistency findings" in payload["laneTitles"]
    assert "Blocked findings" in payload["laneTitles"]
    assert "Overall consistency" in payload["bundleTitles"]
    assert "Consistency findings" in payload["bundleTitles"]
    assert "Blocked findings" in payload["bundleTitles"]
    assert "asset-profile:character:lead:v2" in payload["memoryIds"]
    assert payload["nextPassStatus"] == "ready"
    assert payload["nextPassAction"] == "record_tester_feedback_or_continue_next_context"
    assert "asset feedback not auto-created:review ready" in payload["protocolControls"]
    assert "profile update candidate not auto-created:review ready" in payload["protocolControls"]
    assert "promotion decision not auto-created:review ready" in payload["protocolControls"]
    assert "Company KB write disabled:review ready" in payload["protocolControls"]
    assert "agentflow_production_memory_asset_consistency_review" in payload["inspectorTypes"]
    assert "review_status:ready_for_operator_review" in payload["inspectorFacts"]
    assert "overall_consistency_result:kept" in payload["inspectorFacts"]
    assert "consistency_findings:1" in payload["inspectorFacts"]
    assert "blocked_findings:0" in payload["inspectorFacts"]
    assert "writes_company_kb:false" in payload["inspectorFacts"]
    assert "provider_calls_started:false" in payload["inspectorFacts"]


def test_web_static_asset_cockpit_adds_no_provider_scan_persistence_or_loulan_inspector() -> None:
    files = [
        Path("apps/web/artifact-contracts.js"),
        Path("apps/web/artifact-workspace.js"),
        Path("apps/web/memory-workbench-controller.js"),
        Path("apps/web/memory-workbench-inspector.js"),
        Path("apps/web/memory-workbench-production-assets.js"),
    ]
    combined = "\n".join(path.read_text(encoding="utf-8").lower() for path in files if path.exists())

    assert "lou" + "lan" not in combined
    for forbidden in [
        "fetch(",
        "xmlhttprequest",
        "websocket",
        "eventsource",
        "navigator.sendbeacon",
        "localstorage",
        "indexeddb",
        "document.cookie",
        "showsavefilepicker",
        "createwritable",
        "filesystemwritablefilestream",
        "directory",
        "provider execution",
    ]:
        assert forbidden not in combined


def _build_web_view_payload(file_name: str, path_ref: str) -> dict:
    script = f"""
import {{ parseFiles, normalizeWorkspace }} from "./apps/web/artifact-workspace.js";
import {{ buildMemoryWorkbenchView }} from "./apps/web/memory-workbench-controller.js";
import {{ readFile }} from "node:fs/promises";

const file = {{
  name: {json.dumps(file_name)},
  text: async () => await readFile({path_ref}, "utf8"),
}};
const artifacts = await parseFiles([file]);
const workspace = normalizeWorkspace(artifacts);
const view = buildMemoryWorkbenchView(workspace, "selected_files");

console.log(JSON.stringify({{
  artifactType: artifacts[0].artifactType,
  artifactClass: artifacts[0].artifactClass,
  sourceRole: artifacts[0].sourceRole,
  memoryBundleCount: workspace.memoryBundle.length,
  hasProjection: Boolean(workspace.productionMemoryAssetProfileContextProjection),
  hasConsistencyReview: Boolean(workspace.productionMemoryAssetConsistencyReview),
  projectFormat: view.project.format,
  state: view.state,
  laneTitles: view.lanes.map((lane) => lane.title),
  bundleTitles: view.bundle_summary.map((item) => item.title),
  memoryIds: view.memory_loaded.map((item) => item.id),
  nextPassStatus: view.next_pass.status,
  nextPassAction: view.next_pass.action,
  protocolControls: view.protocol_summary.controls.map((item) => `${{item.label}}:${{item.status}}`),
  inspectorTypes: view.artifact_inspector.map((item) => item.artifact_type),
  inspectorFacts: view.artifact_inspector.flatMap((item) => item.facts.map((fact) => `${{fact.label}}:${{fact.value}}`)),
}}));
"""
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def _projection(tmp_path: Path) -> dict:
    asset_profiles, candidate = asset_profiles_and_candidate(tmp_path)
    _decision, version = build_asset_profile_promotion_review(
        asset_profiles=asset_profiles,
        update_candidate=candidate,
        decision="promoted",
        rationale="Operator approved the structured profile patch for tester review continuity.",
        reviewer_role="operator",
        decided_at=GENERATED_AT,
    )
    assert version is not None
    return build_asset_profile_context_projection(
        asset_profile_versions=[version],
        generated_at="2026-06-03T00:30:00+08:00",
    )


def _fixture(projection: dict) -> dict:
    return {
        "kind": ASSET_CONSISTENCY_REVIEW_FIXTURE_KIND,
        "artifact_type": ASSET_CONSISTENCY_REVIEW_FIXTURE_KIND,
        "schema_version": projection["schema_version"],
        "fixture_id": "asset-consistency-fixture:character-lead-cross-scene-001",
        "project_id": projection["project_id"],
        "source_context_projection_ref": projection["projection_id"],
        "source_result_ref": "next-pass-result:sanitized-cross-scene-001",
        "source_feedback_input_type": "json_fixture",
        "comparison_scope": "cross_scene",
        "review_items": [
            {
                "profile_ref": "asset-profile:character:lead:v2",
                "profile_kind": "character",
                "output_refs": ["output:scene-001", "output:scene-002"],
                "review_dimension": "character_identity",
                "review_result": "kept",
                "failure_attribution": "unknown",
                "drift_observations": [],
                "violated_constraints": [],
                "evidence_refs": ["output:scene-001", "output:scene-002"],
                "suggested_next_state": "no_change",
            }
        ],
    }
