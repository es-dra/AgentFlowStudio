from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow_studio.production.manga_first_l4a_schema import (
    json_digest,
    read_json_object,
    sha256_file,
)


def build_legacy_fixture_regression_manifest(
    *,
    l1_root: str | Path,
    l2_root: str | Path,
    l3_root: str | Path,
) -> dict[str, Any]:
    l1 = Path(l1_root)
    l2 = Path(l2_root)
    l3 = Path(l3_root)
    l1_manifest = read_json_object(l1 / "recovery_manifest.json")
    l2_manifest = read_json_object(l2 / "timeline_manifest.json")
    l3_eval = read_json_object(l3 / "visual_creative_evaluation.json")
    p1_findings = [
        {
            "id": item["id"],
            "severity": item["severity"],
            "title": item["title"],
            "observation": item["observation"],
        }
        for item in l3_eval.get("findings", [])
        if item.get("severity") == "P1"
    ]
    body = {
        "schema_version": "afs.manga_first_l4a.legacy_regression_fixture.v0.1",
        "authority": "recovery_and_regression_fixture_only",
        "not_new_canonical_truth": True,
        "l1": {
            "root": str(l1),
            "manifest_sha256": sha256_file(l1 / "recovery_manifest.json"),
            "status": l1_manifest.get("status"),
            "png_count": len(list((l1 / "media" / "keyframes").glob("*.png"))),
            "mp4_count": len(list((l1 / "media" / "videos").glob("*.mp4"))),
            "verification": l1_manifest.get("verification", {}),
        },
        "l2": {
            "root": str(l2),
            "timeline_manifest_sha256": sha256_file(l2 / "timeline_manifest.json"),
            "status": l2_manifest.get("status"),
            "duration_seconds": l2_manifest.get("outputs", {}).get("full_coverage_silent_review", {}).get("duration_seconds"),
            "audio_stream_count": l2_manifest.get("outputs", {}).get("full_coverage_silent_review", {}).get("audio_stream_count"),
        },
        "l3": {
            "root": str(l3),
            "evaluation_sha256": sha256_file(l3 / "visual_creative_evaluation.json"),
            "verdict": l3_eval.get("verdict"),
            "severity_counts": l3_eval.get("severity_counts"),
            "p1_findings": p1_findings,
            "inspection": l3_eval.get("inspection", {}),
        },
        "provider_dispatch_count": 0,
        "non_claims": [
            "not_final_manga_first_canonical_authority",
            "not_visual_creative_qa_pass",
            "not_human_acceptance",
            "not_business_validation",
        ],
    }
    return {**body, "fixture_manifest_sha256": json_digest(body)}
