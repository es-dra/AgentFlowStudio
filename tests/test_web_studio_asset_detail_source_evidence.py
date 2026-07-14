from __future__ import annotations

import json
import subprocess
from pathlib import Path


def test_asset_detail_source_evidence_rows_are_safe_and_local() -> None:
    script = r'''
import { assetSourceEvidenceRows } from "./apps/studio/src/panels/asset-detail-popover.js";
import { assetLabel } from "./apps/studio/src/asset-reference-summary.js";

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

process.stdout.write(JSON.stringify({ rows, unnamedLabel: assetLabel({ asset_id: "raw-asset-id-001" }) }));
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

    assert rows == [
        "人工审核：已记录",
        "资产候选：已记录",
        "来源阶段：已记录",
        "生成服务：未调用",
        "人工创意确认：未确认",
    ]
    assert "runtime-human-gate" not in serialized
    assert "asset_card_candidate" not in serialized
    assert "provider_calls_started" not in serialized
    assert payload["unnamedLabel"] == "未命名素材"
    assert "raw-asset-id-001" not in serialized
    assert "_".join(["signed", "url"]) not in serialized
    assert "local_path" not in serialized
    assert "data_base64" not in serialized
    assert "d:\\private" not in serialized


def test_asset_detail_popover_wires_source_evidence_section() -> None:
    text = Path("apps/studio/src/panels/asset-detail-popover.js").read_text(encoding="utf-8")

    assert 'detailList("来源证据", sourceEvidenceRows)' in text
    assert "assetSourceEvidenceRows(asset)" in text


def test_visual_asset_promotion_keeps_source_evidence_in_asset_library_entry() -> None:
    panel = Path("apps/studio/src/panels/visual-asset-panel.js").read_text(encoding="utf-8")

    assert "source_evidence: localAsset.source_evidence || null" in panel
    assert "n.params.visualAssets = mergeVisualAssets" in panel
