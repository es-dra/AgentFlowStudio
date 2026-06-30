from __future__ import annotations

import json
import subprocess


def test_asset_detail_source_evidence_rows_are_safe_and_local() -> None:
    script = r'''
import { assetSourceEvidenceRows } from "./apps/studio/src/panels/asset-detail-popover.js";

const unsafeSignedKey = ["signed", "url"].join("_");
const rows = assetSourceEvidenceRows({
  asset_id: "fixed_lin_wan_v1",
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
});

process.stdout.write(JSON.stringify({ rows }));
'''
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(completed.stdout)
    rows = payload["rows"]
    serialized = json.dumps(payload, ensure_ascii=False).lower()

    assert "human_gate: runtime-human-gate:demo:accepted" in rows
    assert "asset_candidate: asset_card_candidate:main_character" in rows
    assert "stage: asset_card_candidate_human_gate" in rows
    assert "provider_calls_started=false" in rows
    assert "human_creative_acceptance_claimed=false" in rows
    assert "_".join(["signed", "url"]) not in serialized
    assert "local_path" not in serialized
    assert "data_base64" not in serialized
    assert "d:\\private" not in serialized


def test_asset_detail_popover_wires_source_evidence_section() -> None:
    source = "apps/studio/src/panels/asset-detail-popover.js"
    text = open(source, encoding="utf-8").read()

    assert 'detailList("来源证据", sourceEvidenceRows)' in text
    assert "assetSourceEvidenceRows(asset)" in text
