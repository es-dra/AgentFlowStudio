from __future__ import annotations

import json
import subprocess


def test_source_evidence_refs_keep_provider_and_acceptance_non_claim_flags() -> None:
    script = r'''
import { sourceEvidenceRefs } from "./apps/studio/src/generation-preflight-source-evidence.js";

const unsafeSignedKey = ["signed", "url"].join("_");
const fromAsset = sourceEvidenceRefs({
  included_assets: [{
    asset_id: "fixed_lin_wan_v1",
    asset_type: "character",
    label: "Lin Wan",
    status: "fixed",
    source_evidence: {
      source_human_gate_id: "runtime-human-gate:demo:accepted",
      source_asset_card_candidate_id: "asset_card_candidate:main_character",
      source_stage: "asset_card_candidate_human_gate",
      provider_calls_started: false,
      human_creative_acceptance_claimed: false,
      [unsafeSignedKey]: "must-not-leak",
      local_path: "D:\\private\\fixed_lin_wan.png",
      data_base64: "BYTES_MUST_NOT_LEAK",
    },
  }],
});

const explicit = sourceEvidenceRefs({
  included_asset_source_evidence_refs: [{
    asset_id: "fixed_scene_v1",
    source_asset_card_candidate_id: "asset_card_candidate:scene",
    provider_calls_started: true,
    human_creative_acceptance_claimed: true,
    [unsafeSignedKey]: "must-not-leak",
    local_path: "D:\\private\\fixed_scene.png",
  }],
});

process.stdout.write(JSON.stringify({ fromAsset, explicit }));
'''
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(completed.stdout)
    serialized = json.dumps(payload, ensure_ascii=False).lower()

    assert payload["fromAsset"][0]["provider_calls_started"] is False
    assert payload["fromAsset"][0]["human_creative_acceptance_claimed"] is False
    assert payload["explicit"][0]["provider_calls_started"] is True
    assert payload["explicit"][0]["human_creative_acceptance_claimed"] is True
    assert "_".join(["signed", "url"]) not in serialized
    assert "local_path" not in serialized
    assert "data_base64" not in serialized
    assert "d:\\private" not in serialized
