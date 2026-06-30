from __future__ import annotations

import json
import subprocess

from studio_static_helpers import STUDIO_ROOT, _styles


def test_studio_visual_asset_promotion_sends_accepted_human_gate_provenance() -> None:
    panel = (STUDIO_ROOT / "src" / "panels" / "visual-asset-panel.js").read_text(encoding="utf-8")
    provenance = (STUDIO_ROOT / "src" / "human-gate-provenance.js").read_text(encoding="utf-8")
    render = (STUDIO_ROOT / "src" / "panels" / "visual-asset-panel-render.js").read_text(encoding="utf-8")
    index = (STUDIO_ROOT / "index.html").read_text(encoding="utf-8")
    request_builder = STUDIO_ROOT / "src" / "panels" / "visual-asset-promotion-request.js"
    builder_source = request_builder.read_text(encoding="utf-8") if request_builder.is_file() else ""
    styles = _styles()

    assert request_builder.is_file()
    assert "buildVisualAssetPromotionPayload" in panel
    assert "promotionGateProvenance(node)" in builder_source
    assert "promotionGateReviewSummary(node)" in render
    assert "visual-asset-promotion-gate-summary" in render
    assert "visual-asset-promotion-gate-summary" in styles
    assert "visual-asset-promotion-gate.css" in index
    assert "source_human_gate_id" in provenance
    assert "source_asset_card_candidate_id" in provenance
    assert "promotionGateReviewSummary" in provenance
    assert "accepted_for_next_step" in provenance
    assert "asset_card_candidate" in provenance
    assert "provider" not in provenance.lower()


def test_visual_asset_promotion_payload_builder_is_deterministic_and_safe() -> None:
    script = r'''
import { buildVisualAssetPromotionPayload } from "./apps/studio/src/panels/visual-asset-promotion-request.js";

const fixedPayload = buildVisualAssetPromotionPayload({
  node: {
    id: "node-asset-1",
    params: {
      humanGateDecisions: [
        { human_gate_id: "runtime-human-gate:demo:old", target_type: "asset_card_candidate", target_id: "asset_card_candidate:old", decision: "needs_revision" },
        { human_gate_id: "runtime human gate / accepted", target_type: "asset_card_candidate", target_id: "asset card candidate / main", decision: "accepted_for_next_step", note: "Studio local step gate decision. reuse_scope=project_reuse_candidate; shot_ref_count=3; writes_fixed_asset=false" },
      ],
    },
  },
  imageAsset: { asset_id: "img_asset_1" },
  decision: "fixed",
  label: "Lin Wan",
  assetType: "character",
  signature: "black short hair",
  featureCard: { appearance: "black short hair" },
  negativeLocks: ["keep black short hair"],
  supersedesAssetId: "vas_old_1",
  reviewedAt: "2026-06-30T22:30:00+08:00",
});

const directPayload = buildVisualAssetPromotionPayload({
  node: { id: "node-asset-2", params: { humanGateDecisions: [] } },
  imageAsset: { asset_id: "img_asset_2" },
  decision: "rejected",
  label: "Rejected candidate",
  assetType: "prop",
  signature: "not used",
  featureCard: { review: "rejected candidate" },
  negativeLocks: [],
  reviewedAt: "2026-06-30T22:31:00+08:00",
});

process.stdout.write(JSON.stringify({ fixedPayload, directPayload }));
'''
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(completed.stdout)
    fixed = payload["fixedPayload"]
    direct = payload["directPayload"]

    assert fixed["source_image_asset_refs"] == ["img_asset_1"]
    assert fixed["source_node_id"] == "node-asset-1"
    assert fixed["source_human_gate_id"] == "runtime_human_gate_accepted"
    assert fixed["source_asset_card_candidate_id"] == "asset_card_candidate_main"
    assert fixed["supersedes_asset_id"] == "vas_old_1"
    assert fixed["reviewed_at"] == "2026-06-30T22:30:00+08:00"
    assert fixed["review_decision"] == "fixed"
    assert "provider" not in json.dumps(fixed).lower()
    assert "data_base64" not in json.dumps(fixed).lower()
    assert "reuse_scope" not in json.dumps(fixed).lower()

    assert "source_human_gate_id" not in direct
    assert "source_asset_card_candidate_id" not in direct
    assert direct["supersedes_asset_id"] is None
    assert direct["review_decision"] == "rejected"


def test_visual_asset_promotion_review_summary_uses_safe_human_gate_note() -> None:
    script = r'''
import { promotionGateReviewSummary } from "./apps/studio/src/human-gate-provenance.js";

const node = {
  params: {
    humanGateDecisions: [
      {
        human_gate_id: "runtime-human-gate:old",
        target_type: "asset_card_candidate",
        target_id: "asset_card_candidate:old",
        decision: "needs_revision",
        note: "reuse_scope=shot_local_candidate; shot_ref_count=1",
      },
      {
        human_gate_id: "runtime human gate / accepted",
        target_type: "asset_card_candidate",
        target_id: "asset card candidate / main",
        decision: "accepted_for_next_step",
        note: "Studio local step gate decision. reuse_scope=project_reuse_candidate; shot_ref_count=3; writes_fixed_asset=false",
      },
    ],
  },
};

const legacyNode = {
  params: {
    humanGateDecisions: [
      {
        human_gate_id: "runtime-human-gate:legacy",
        target_type: "asset_card_candidate",
        target_id: "asset_card_candidate:legacy",
        decision: "accepted_for_next_step",
      },
    ],
  },
};

process.stdout.write(JSON.stringify({
  summary: promotionGateReviewSummary(node),
  legacySummary: promotionGateReviewSummary(legacyNode),
}));
'''
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(completed.stdout)
    summary = payload["summary"]
    legacy_summary = payload["legacySummary"]

    assert summary["source_human_gate_id"] == "runtime_human_gate_accepted"
    assert summary["source_asset_card_candidate_id"] == "asset_card_candidate_main"
    assert summary["reuse_scope"] == "project_reuse_candidate"
    assert summary["shot_ref_count"] == 3
    assert summary["label"] == "Project reuse / 3 shots"
    assert summary["writes_fixed_asset"] is False
    assert legacy_summary["reuse_scope"] == ""
    assert legacy_summary["label"] == "Accepted asset-card gate"
