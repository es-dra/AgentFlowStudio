from __future__ import annotations

import json
import subprocess


def _node_json(script: str) -> dict:
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(completed.stdout)


def test_keyframe_constraint_rows_normalize_edit_reorder_and_project_deterministically() -> None:
    payload = _node_json(
        r'''
import {
  addKeyframeConstraintRow,
  moveKeyframeConstraintRow,
  normalizeKeyframeConstraints,
  projectKeyframeConstraintsForProvider,
  removeKeyframeConstraintRow,
  toggleKeyframeConstraintRow,
  updateKeyframeConstraintRow,
} from "./apps/studio/src/keyframe-constraints.js";

let constraints = normalizeKeyframeConstraints({
  rows: [
    { id: "character", section: "character", text: "hero keeps the red scarf", enabled: true, order: 1, projection: "provider", unknown_secret_key: "must drop" },
    { id: "scene", section: "scene", text: "rainy market entrance", enabled: true, order: 2, projection: "provider" },
  ],
});
constraints = addKeyframeConstraintRow(constraints, {
  id: "camera",
  section: "camera",
  text: "wide lens",
  enabled: true,
  projection: "provider",
});
constraints = toggleKeyframeConstraintRow(constraints, "scene", false);
constraints = updateKeyframeConstraintRow(constraints, "camera", { text: "low angle close-up" });
constraints = moveKeyframeConstraintRow(constraints, "camera", -1);
constraints = removeKeyframeConstraintRow(constraints, "character");

process.stdout.write(JSON.stringify({
  constraints,
  projection: projectKeyframeConstraintsForProvider(constraints),
}));
'''
    )

    rows = payload["constraints"]["rows"]
    assert [row["id"] for row in rows] == ["camera", "scene"]
    assert rows[0]["order"] == 0
    assert rows[1]["enabled"] is False
    assert "unknown_secret_key" not in rows[0]
    assert payload["projection"]["prompt_text"] == "Camera: low angle close-up"


def test_keyframe_constraints_projection_snapshot_excludes_disabled_audit_and_unsafe_rows() -> None:
    payload = _node_json(
        r'''
import {
  normalizeKeyframeConstraints,
  projectKeyframeConstraintsForProvider,
} from "./apps/studio/src/keyframe-constraints.js";

const constraints = normalizeKeyframeConstraints({
  rows: [
    { id: "motion", section: "motion", text: "cloth moves slightly in rain", enabled: true, order: 60, projection: "provider" },
    { id: "local", section: "local_reference", text: "private board label", label: "Private Concept Board", enabled: true, order: 80, projection: "provider" },
    { id: "disabled_camera", section: "camera", text: "unused wide lens", enabled: false, order: 40, projection: "provider" },
    { id: "character", section: "character", text: "same red coat and tired eyes", enabled: true, order: 10, projection: "provider" },
    { id: "scene", section: "scene", text: "rainy back alley", enabled: true, order: 20, projection: "provider" },
    { id: "object", section: "object", text: "silver compass in left hand", enabled: true, order: 30, projection: "provider" },
    { id: "unsafe_camera", section: "camera", text: "use C:\\private\\pose.png", enabled: true, order: 41, projection: "provider" },
    { id: "lighting", section: "lighting", text: "cold neon rim light", enabled: true, order: 50, projection: "provider" },
    { id: "negative", section: "negative", text: "no text, no watermark", enabled: true, order: 70, projection: "provider" },
    { id: "fixed", section: "fixed_asset", text: "do not leak asset label", asset_id: "vas_hero", label: "Local Hero Label", enabled: true, order: 90, projection: "provider" },
  ],
});
const projection = projectKeyframeConstraintsForProvider(constraints);
process.stdout.write(JSON.stringify({ constraints, projection }));
'''
    )

    local_row = next(row for row in payload["constraints"]["rows"] if row["id"] == "local")
    fixed_row = next(row for row in payload["constraints"]["rows"] if row["id"] == "fixed")
    assert local_row["projection"] == "audit_only"
    assert fixed_row["projection"] == "audit_only"
    assert [section["section"] for section in payload["projection"]["sections"]] == [
        "character",
        "scene",
        "object",
        "lighting",
        "motion",
        "negative",
    ]
    assert payload["projection"]["prompt_text"] == "\n".join([
        "Character: same red coat and tired eyes",
        "Scene: rainy back alley",
        "Object: silver compass in left hand",
        "Lighting: cold neon rim light",
        "Motion: cloth moves slightly in rain",
        "Negative: no text, no watermark",
    ])
    serialized_projection = json.dumps(payload["projection"])
    assert "Private Concept Board" not in serialized_projection
    assert "Local Hero Label" not in serialized_projection
    assert "C:\\private" not in serialized_projection
    assert "unused wide lens" not in serialized_projection


def test_keyframe_generation_request_projects_only_provider_rows_to_runtime_surfaces() -> None:
    payload = _node_json(
        r'''
import { buildKeyframeGenerationRequest } from "./apps/studio/src/optimizer-contract.js";

const keyframe = {
  id: "keyframe_1",
  type: "image",
  title: "Keyframe 1",
  prompt: "Base keyframe prompt.",
  params: {
    nodeRole: "keyframe_generation",
    lastOptimizedPromptPlain: "Optimized base prompt.",
    spec: { ratio: "16:9", count: 2 },
    visualAssets: [{ asset_id: "vas_hero", label: "Hero", status: "fixed", image_asset_refs: ["img_hero_fixed"] }],
    temporaryAssetExclusions: [{ asset_id: "vas_old", reason: "keyframe_constraints_editor_fixed_asset_exclusion" }],
    keyframeConstraints: {
      rows: [
        { id: "character", section: "character", text: "hero keeps the red scarf", enabled: true, order: 1, projection: "provider" },
        { id: "scene", section: "scene", text: "rainy station platform", enabled: true, order: 2, projection: "provider" },
        { id: "disabled", section: "camera", text: "disabled camera row", enabled: false, order: 3, projection: "provider" },
        { id: "local", section: "local_reference", text: "private moodboard only", label: "Private Concept Board", enabled: true, order: 4, projection: "audit_only", asset_id: "local_ref_1" },
        { id: "fixed", section: "fixed_asset", text: "fixed local asset note", label: "Local Fixed Label", asset_id: "vas_hero", enabled: true, order: 5, projection: "audit_only" },
        { id: "unsafe", section: "lighting", text: "signed_url=https://example.test/private.png?token=secret", enabled: true, order: 6, projection: "provider" },
      ],
    },
  },
};
const state = { nodes: { keyframe_1: keyframe }, edges: {}, assets: [] };
const request = buildKeyframeGenerationRequest(state, keyframe);
process.stdout.write(JSON.stringify(request));
'''
    )

    assert payload["prompt_text"] == "\n".join([
        "Base keyframe prompt.",
        "",
        "Keyframe constraints:",
        "Character: hero keeps the red scarf",
        "Scene: rainy station platform",
    ])
    assert payload["optimized_prompt"] == "\n".join([
        "Optimized base prompt.",
        "",
        "Keyframe constraints:",
        "Character: hero keeps the red scarf",
        "Scene: rainy station platform",
    ])
    assert payload["asset_refs"] == ["img_hero_fixed"]
    assert payload["temporary_asset_exclusions"] == [
        {"asset_id": "vas_old", "reason": "keyframe_constraints_editor_fixed_asset_exclusion"},
        {"asset_id": "vas_hero", "reason": "keyframe_constraint_fixed_asset_exclusion"},
    ]
    assert "keyframeConstraints" not in payload["node_parameters"]
    context_target = next(node for node in payload["context_subgraph"]["nodes"] if node["id"] == "keyframe_1")
    assert "keyframeConstraints" not in context_target["node_parameters"]
    assert context_target["prompt"] == "Base keyframe prompt."
    provider_visible = json.dumps({
        "prompt_text": payload["prompt_text"],
        "optimized_prompt": payload["optimized_prompt"],
        "asset_refs": payload["asset_refs"],
        "context_subgraph": payload["context_subgraph"],
        "node_parameters": payload["node_parameters"],
        "temporary_asset_exclusions": payload["temporary_asset_exclusions"],
    })
    for forbidden in (
        "Private Concept Board",
        "private moodboard only",
        "Local Fixed Label",
        "fixed local asset note",
        "disabled camera row",
        "signed_url",
        "token=secret",
        "local_ref_1",
    ):
        assert forbidden not in provider_visible


def test_fixed_asset_exclusion_helper_uses_existing_one_run_override_and_clear_path() -> None:
    payload = _node_json(
        r'''
import { buildKeyframeGenerationRequest } from "./apps/studio/src/optimizer-contract.js";
import { clearOneRunOverrides } from "./apps/studio/src/node-generation-guards.js";
import { syncTemporaryAssetExclusionsFromKeyframeConstraints } from "./apps/studio/src/keyframe-constraints.js";

const node = {
  id: "keyframe_1",
  type: "image",
  prompt: "Base prompt",
  params: {
    nodeRole: "keyframe_generation",
    spec: { ratio: "16:9", count: 1 },
    visualAssets: [{ asset_id: "vas_hero", status: "fixed", image_asset_refs: ["img_hero_fixed"] }],
    temporaryAssetExclusions: [],
    keyframeConstraints: {
      rows: [
        { id: "fixed_hero", section: "fixed_asset", text: "exclude once", enabled: true, projection: "audit_only", asset_id: "vas_hero" },
      ],
    },
  },
};
syncTemporaryAssetExclusionsFromKeyframeConstraints(node);
const before = node.params.temporaryAssetExclusions.some((item) => item.asset_id === "vas_hero");
const state = { nodes: { keyframe_1: node }, edges: {}, assets: [] };
const request = buildKeyframeGenerationRequest(state, node);
const store = {
  get: () => state,
  set: (mutator) => mutator(state),
};
clearOneRunOverrides(store, "keyframe_1");
process.stdout.write(JSON.stringify({
  before,
  requestExclusions: request.temporary_asset_exclusions,
  afterClear: state.nodes.keyframe_1.params.temporaryAssetExclusions,
}));
'''
    )

    assert payload["before"] is True
    assert payload["requestExclusions"] == [
        {"asset_id": "vas_hero", "reason": "keyframe_constraint_fixed_asset_exclusion"}
    ]
    assert payload["afterClear"] == []
