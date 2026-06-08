from __future__ import annotations

import json
import subprocess
from pathlib import Path

from agentflow.memory.production_asset_consistency_review import (
    ASSET_CONSISTENCY_REVIEW_FIXTURE_KIND,
    build_asset_consistency_review,
    write_asset_consistency_review,
)
from agentflow.memory.production_asset_profile_context_projection import build_asset_profile_context_projection
from agentflow.memory.production_asset_profile_promotion import build_asset_profile_promotion_review
from tests.production_memory_asset_profile_promotion_helpers import (
    GENERATED_AT,
    asset_profiles_and_candidate,
)


def test_web_static_asset_review_screen_answers_tester_questions(tmp_path: Path) -> None:
    projection = _projection(tmp_path)
    review = build_asset_consistency_review(
        asset_profile_context_projection=projection,
        consistency_fixture=_mixed_review_fixture(projection),
        reviewed_at="2026-06-03T01:30:00+08:00",
    )
    write_asset_consistency_review(review, tmp_path)
    review_ref = json.dumps(str(tmp_path / "asset_consistency_review.json"))

    payload = _build_web_view_payload("asset_consistency_review.json", review_ref)

    assert payload["assetReviewTarget"] == {
        "character": "asset-profile:character:lead:v2",
        "scene": "next-pass-result:sanitized-cross-scene-001",
    }
    assert payload["assetReviewProfileVersions"] == ["asset-profile:character:lead:v2:v2"]
    assert payload["assetReviewIncludedRefs"] == ["asset-profile:character:lead:v2"]
    assert payload["assetReviewBlockedRefs"] == ["asset-profile:character:lead:v1:superseded_by_profile_version"]
    assert payload["assetReviewConfirmedFeatures"] == ["character_identity:kept"]
    assert payload["assetReviewPartialFeatures"] == ["wardrobe_or_body_anchor:partially_kept"]
    assert payload["assetReviewFailedFeatures"] == ["negative_constraint_violations:not_kept"]
    assert payload["assetReviewUnknownFeatures"] == ["scene_spatial_anchor:cannot_judge"]
    assert payload["assetReviewAllowedChanges"]
    assert payload["assetReviewBlockedChanges"]
    assert payload["assetReviewNextRecommendations"] == [
        "no_change:1",
        "candidate:1",
        "blocked:1",
        "cannot_judge:1",
    ]
    assert "not human acceptance" in payload["assetReviewNonClaims"]
    assert "not business validation" in payload["assetReviewNonClaims"]
    assert "not durable memory" in payload["assetReviewNonClaims"]


def test_web_static_asset_review_screen_is_visible_in_memory_workbench(tmp_path: Path) -> None:
    projection = _projection(tmp_path)
    review = build_asset_consistency_review(
        asset_profile_context_projection=projection,
        consistency_fixture=_mixed_review_fixture(projection),
        reviewed_at="2026-06-03T01:45:00+08:00",
    )
    write_asset_consistency_review(review, tmp_path)
    review_ref = json.dumps(str(tmp_path / "asset_consistency_review.json"))

    payload = _render_web_view_payload("asset_consistency_review.json", review_ref)

    assert "Asset Profile Review Screen" in payload["projectSummary"]
    assert "Current character: asset-profile:character:lead:v2" in payload["projectSummary"]
    assert "Current scene: next-pass-result:sanitized-cross-scene-001" in payload["projectSummary"]
    assert "Included refs: asset-profile:character:lead:v2" in payload["projectSummary"]
    assert "Blocked refs: asset-profile:character:lead:v1 superseded_by_profile_version" in payload["projectSummary"]
    assert "Next recommendations: no_change: 1 / candidate: 1 / blocked: 1 / cannot_judge: 1" in payload["projectSummary"]
    assert "not human acceptance" in payload["projectSummary"]
    assert "not business validation" in payload["projectSummary"]


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
  assetReviewTarget: view.asset_review_screen?.target,
  assetReviewProfileVersions: view.asset_review_screen?.profile_versions,
  assetReviewIncludedRefs: view.asset_review_screen?.included_refs?.map((item) => item.ref_id),
  assetReviewBlockedRefs: view.asset_review_screen?.blocked_refs?.map((item) => `${{item.ref_id}}:${{item.reason}}`),
  assetReviewConfirmedFeatures: view.asset_review_screen?.tester_feedback?.confirmed_features?.map((item) => `${{item.dimension}}:${{item.result}}`),
  assetReviewPartialFeatures: view.asset_review_screen?.tester_feedback?.partial_features?.map((item) => `${{item.dimension}}:${{item.result}}`),
  assetReviewFailedFeatures: view.asset_review_screen?.tester_feedback?.failed_features?.map((item) => `${{item.dimension}}:${{item.result}}`),
  assetReviewUnknownFeatures: view.asset_review_screen?.tester_feedback?.unknown_features?.map((item) => `${{item.dimension}}:${{item.result}}`),
  assetReviewAllowedChanges: view.asset_review_screen?.allowed_changes,
  assetReviewBlockedChanges: view.asset_review_screen?.blocked_changes,
  assetReviewNextRecommendations: view.asset_review_screen?.next_recommendations?.map((item) => `${{item.state}}:${{item.count}}`),
  assetReviewNonClaims: view.asset_review_screen?.non_claims,
}}));
"""
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def _render_web_view_payload(file_name: str, path_ref: str) -> dict:
    script = f"""
import {{ parseFiles, normalizeWorkspace }} from "./apps/web/artifact-workspace.js";
import {{ buildMemoryWorkbenchView }} from "./apps/web/memory-workbench-controller.js";
import {{ renderMemoryWorkbench }} from "./apps/web/memory-workbench-render.js";
import {{ readFile }} from "node:fs/promises";

function element(tagName) {{
  return {{
    tagName,
    className: "",
    children: [],
    dataset: {{}},
    _text: "",
    style: {{ setProperty() {{}} }},
    get classList() {{
      return {{ toggle() {{}} }};
    }},
    set textContent(value) {{
      this._text = String(value);
    }},
    get textContent() {{
      return [this._text, ...this.children.map((child) => child.textContent || "")].join("");
    }},
    append(...children) {{
      this.children.push(...children);
    }},
    replaceChildren(...children) {{
      this.children = children;
    }},
    setAttribute() {{}},
    addEventListener() {{}},
    querySelectorAll() {{
      return [];
    }},
  }};
}}

globalThis.document = {{ createElement: element }};

const elements = {{
  memoryWorkbench: element("section"),
  memorySourceStatus: element("div"),
  memoryStudioStatus: element("div"),
  memoryProjectSummary: element("div"),
  memoryAssetSummary: element("div"),
  memoryBundleSummary: element("div"),
  memoryArtifactInspector: element("div"),
  memoryFeedbackPreview: element("div"),
  memoryFeedbackOutput: element("textarea"),
  memoryFeedbackStatus: element("p"),
  memoryFeedbackCopy: element("button"),
  memoryFocusSummary: element("div"),
  memoryDemoChecklist: element("div"),
  memoryDemoSummary: element("div"),
  memoryActionStrip: element("div"),
  memoryOperatorDock: element("div"),
  memoryStateStrip: element("div"),
  memoryCanvasStage: element("div"),
  memoryProtocolSummary: element("div"),
  memoryLaneGrid: element("div"),
  memoryRunTimeline: element("div"),
  memoryProvenancePanel: element("div"),
}};

const file = {{
  name: {json.dumps(file_name)},
  text: async () => await readFile({path_ref}, "utf8"),
}};
const artifacts = await parseFiles([file]);
const workspace = normalizeWorkspace(artifacts);
const view = buildMemoryWorkbenchView(workspace, "selected_files");
renderMemoryWorkbench(elements, view, {{ statusLabels: {{}}, noDetails: "" }});

console.log(JSON.stringify({{
  projectSummary: elements.memoryProjectSummary.textContent,
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


def _mixed_review_fixture(projection: dict) -> dict:
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
            _review_item("character_identity", "kept", "unknown", [], [], "output:scene-001", "no_change"),
            _review_item(
                "wardrobe_or_body_anchor",
                "partially_kept",
                "profile_issue",
                ["sleeve texture drifted but silhouette stayed recognizable"],
                [],
                "output:scene-002",
                "candidate",
            ),
            _review_item(
                "negative_constraint_violations",
                "not_kept",
                "style_drift",
                ["face shape drifted"],
                ["avoid alternate face shape"],
                "output:scene-003",
                "blocked",
            ),
            _review_item("scene_spatial_anchor", "cannot_judge", "unknown", [], [], "output:scene-004", "cannot_judge"),
        ],
    }


def _review_item(
    dimension: str,
    result: str,
    attribution: str,
    observations: list[str],
    constraints: list[str],
    output_ref: str,
    next_state: str,
) -> dict:
    return {
        "profile_ref": "asset-profile:character:lead:v2",
        "profile_kind": "character",
        "output_refs": [output_ref],
        "review_dimension": dimension,
        "review_result": result,
        "failure_attribution": attribution,
        "drift_observations": observations,
        "violated_constraints": constraints,
        "evidence_refs": [output_ref],
        "suggested_next_state": next_state,
    }
