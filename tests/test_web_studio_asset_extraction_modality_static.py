import json
import subprocess

from studio_static_helpers import STUDIO_ROOT


def test_studio_asset_extraction_contract_module_is_wired() -> None:
    contract = (STUDIO_ROOT / "src" / "asset-extraction-contract.js").read_text(encoding="utf-8")
    structured = (STUDIO_ROOT / "src" / "structured-shot.js").read_text(encoding="utf-8")
    script_breakdown = (STUDIO_ROOT / "src" / "script-breakdown.js").read_text(encoding="utf-8")

    assert "normalizeAssetExtractionRefs" in contract
    assert "audio_only_non_visual_city_reference" in contract
    assert "visual_evidence_span" in contract
    assert "display_name" in contract
    assert "asset-extraction-contract.js" in structured
    assert "normalizeShotAssetRefs" in script_breakdown
    assert "display_name" in script_breakdown
    assert "descriptive_signature" in script_breakdown
    assert "evidence_modality" in script_breakdown


def test_studio_structured_shot_applies_modality_and_generic_name_gate() -> None:
    script = r'''
import { structuredShotFromSegment, normalizeShotAssetRefs } from "./apps/studio/src/structured-shot.js";

const audio = structuredShotFromSegment("城市环境底噪和 distant city noise 持续，只有城市噪音。", 1);
const visual = structuredShotFromSegment("Rain-night city street with skyline, buildings, neon signs, and wet road.", 2);
const generic = structuredShotFromSegment("@人物 在雨夜城市街道奔跑，穿红色外套，霓虹照亮侧脸。", 3);
const unresolved = structuredShotFromSegment("@人物", 4);
const providerRefs = normalizeShotAssetRefs(
  [{ label: "城市噪音", asset_type: "scene", source: "provider", evidence_text: "distant city noise" }],
  "distant city noise"
);

process.stdout.write(JSON.stringify({ audio, visual, generic, unresolved, providerRefs }));
'''
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(completed.stdout)

    assert not any(ref["asset_type"] == "scene" for ref in payload["audio"]["asset_refs"])
    assert any(item["reason"] == "audio_only_non_visual_city_reference" for item in payload["audio"]["dropped_asset_ref_diagnostics"])

    scene = next(ref for ref in payload["visual"]["asset_refs"] if ref["asset_type"] == "scene")
    assert scene["evidence_modality"] == "visual"
    assert scene["visual_evidence_span"]

    character = next(ref for ref in payload["generic"]["asset_refs"] if ref["asset_type"] == "character")
    assert character["display_name"] not in {"人", "人物", "主角"}
    assert character["provisional_name"] is True

    assert payload["unresolved"]["asset_refs"] == []
    assert any(item["reason"] == "unresolved_generic_character" for item in payload["unresolved"]["dropped_asset_ref_diagnostics"])
    assert payload["providerRefs"] == []
