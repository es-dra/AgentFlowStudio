from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app
from tools.studio_asset_context_sample_reference import write_sample_reference


PROJECT_ID = "studio-s1-live-comparison"
IMAGE_GATE = "AFS_ALLOW_REMOTE_IMAGE"
PROVIDER_CONFIG = "AFS_PROVIDER_CONFIG"
PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    runtime_root = Path(args.runtime_root or tempfile.mkdtemp(prefix="afs-studio-s1-live-")).resolve()
    report_path = Path(args.report or REPO_ROOT / "runs" / "studio_asset_context_live_comparison_report.json").resolve()
    runtime_root.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    if args.provider_config:
        os.environ[PROVIDER_CONFIG] = str(Path(args.provider_config).resolve())
    if args.sample_reference_output and not args.reference_image:
        args.reference_image = str(write_sample_reference(args.sample_reference_output))

    preflight = _preflight(args)
    if preflight is not None:
        _write_report(report_path, preflight)
        print(json.dumps({"status": preflight["status"], "report": str(report_path)}, ensure_ascii=False))
        return 2

    client = TestClient(create_runtime_app(runtime_root=runtime_root))
    payload = _run_comparison(client, args)
    report = _runner_report(
        payload,
        runtime_root=runtime_root,
        live_authorized=args.allow_live_provider,
        provider_config_supplied=bool(os.environ.get(PROVIDER_CONFIG)),
    )
    _write_report(report_path, report)
    print(json.dumps({"status": report["status"], "report": str(report_path)}, ensure_ascii=False))
    if args.allow_live_provider and not report["provider_calls_started"]:
        return 3
    if args.allow_live_provider and report["comparison_status"] != "succeeded":
        return 3
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the AFS Studio S1 A/B/C asset-context comparison.")
    parser.add_argument("--runtime-root", default="")
    parser.add_argument("--report", default="")
    parser.add_argument("--provider-config", default="")
    parser.add_argument("--provider-service-id", default="codex_image")
    parser.add_argument("--reference-image", default="", help="Optional local image to upload as the fixed character asset.")
    parser.add_argument("--sample-reference-output", default="", help="Write and use a deterministic sample reference PNG when --reference-image is not supplied.")
    parser.add_argument("--allow-live-provider", action="store_true", help="Required in addition to AFS_ALLOW_REMOTE_IMAGE=true.")
    return parser.parse_args(argv)


def _preflight(args: argparse.Namespace) -> dict[str, Any] | None:
    gate_ready = _image_gate_ready()
    if gate_ready and not args.allow_live_provider:
        return _preflight_report(
            status="blocked",
            block_id="live_provider_flag_missing",
            reason="AFS_ALLOW_REMOTE_IMAGE is true, but --allow-live-provider was not supplied.",
            live_authorized=False,
        )
    if args.allow_live_provider and not gate_ready:
        return _preflight_report(
            status="blocked",
            block_id="image_gate_closed",
            reason="Live provider comparison requires AFS_ALLOW_REMOTE_IMAGE=true.",
            live_authorized=False,
        )
    if args.allow_live_provider and not os.environ.get(PROVIDER_CONFIG, "").strip():
        return _preflight_report(
            status="blocked",
            block_id="provider_config_missing",
            reason="Live provider comparison requires AFS_PROVIDER_CONFIG or --provider-config.",
            live_authorized=True,
        )
    if args.allow_live_provider and not args.reference_image:
        return _preflight_report(
            status="blocked",
            block_id="reference_image_missing",
            reason="Live provider comparison requires --reference-image so the fixed asset is grounded in a real local image.",
            live_authorized=True,
        )
    if args.allow_live_provider and not Path(args.reference_image).is_file():
        return _preflight_report(
            status="blocked",
            block_id="reference_image_not_found",
            reason="The --reference-image path does not exist or is not a file.",
            live_authorized=True,
        )
    return None


def _run_comparison(client: TestClient, args: argparse.Namespace) -> dict[str, Any]:
    image_asset_id = _upload_reference_image(client, args.reference_image)
    visual_asset = _promote_fixed_asset(client, image_asset_id)
    response = client.post(
        f"/projects/{PROJECT_ID}/generation-comparisons",
        json={
            "node_id": "target-shot-001",
            "prompt_text": "Lin Wan stands on a rain rooftop, cinematic keyframe.",
            "optimized_prompt": "A controlled rain-rooftop keyframe. Lin Wan faces camera, practical neon rim light, stable red trench coat, tight medium shot, cinematic realism.",
            "target_platform": "short_video",
            "style": "cinematic",
            "aspect_ratio": "9:16",
            "candidate_count": 1,
            "seed": 260612,
            "provider_service_id": args.provider_service_id,
            "context_subgraph": _context_subgraph(visual_asset["asset_id"]),
            "manual_scores": {},
            "generated_at": "2026-06-12T20:00:00+08:00",
        },
    )
    if response.status_code != 200:
        raise RuntimeError(f"comparison request failed: {response.status_code} {response.text}")
    return response.json()


def _upload_reference_image(client: TestClient, reference_image: str) -> str:
    image_bytes = Path(reference_image).read_bytes() if reference_image else PNG_BYTES
    response = client.post(
        f"/projects/{PROJECT_ID}/image-assets",
        json={
            "node_id": "lin-wan-fixed-asset",
            "filename": Path(reference_image).name if reference_image else "lin-wan-synthetic-reference.png",
            "mime_type": _mime_type(reference_image),
            "data_base64": base64.b64encode(image_bytes).decode("ascii"),
            "role": "character_reference",
            "generated_at": "2026-06-12T19:55:00+08:00",
        },
    )
    if response.status_code != 200:
        raise RuntimeError(f"image upload failed: {response.status_code} {response.text}")
    return str(response.json()["asset"]["asset_id"])


def _promote_fixed_asset(client: TestClient, image_asset_id: str) -> dict[str, Any]:
    response = client.post(
        f"/projects/{PROJECT_ID}/visual-assets/promote",
        json={
            "source_image_asset_refs": [image_asset_id],
            "asset_type": "character",
            "label": "Lin Wan",
            "signature": "black short hair, red trench coat, left brow scar",
            "feature_card": {
                "appearance": "black short hair, young woman, left brow scar",
                "wardrobe": "red trench coat",
                "palette": "red coat against cool rainy rooftop",
            },
            "negative_locks": [
                "keep black short hair",
                "keep red trench coat",
                "keep left brow scar",
            ],
            "source_node_id": "lin-wan-fixed-asset",
            "review_decision": "fixed",
            "reviewed_at": "2026-06-12T19:58:00+08:00",
        },
    )
    if response.status_code != 200:
        raise RuntimeError(f"visual asset promote failed: {response.status_code} {response.text}")
    return response.json()["asset"]


def _context_subgraph(asset_id: str) -> dict[str, Any]:
    return {
        "target_node_id": "target-shot-001",
        "runtime_work_mode": "comparison_qa",
        "nodes": [
            {"id": "target-shot-001", "type": "image", "title": "Target shot", "prompt": "Lin Wan on rooftop."},
            {"id": "lin-wan-fixed-asset", "type": "image", "title": "Lin Wan fixed asset", "prompt": "", "visual_asset_ids": [asset_id]},
        ],
        "edges": [{"id": "edge-lin-target", "from": "lin-wan-fixed-asset", "to": "target-shot-001", "relation_type": "reference"}],
    }


def _runner_report(
    payload: dict[str, Any],
    *,
    runtime_root: Path,
    live_authorized: bool,
    provider_config_supplied: bool,
) -> dict[str, Any]:
    report = payload["report"]
    arms = report.get("arms") or []
    return {
        "artifact_type": "studio_asset_context_live_comparison_runner_report",
        "schema_version": "0.1.0",
        "status": "succeeded" if report.get("status") == "succeeded" else "blocked",
        "runner_mode": "live_provider" if live_authorized else "gate_closed_readiness",
        "runtime_root_persisted": False,
        "runtime_root_label": runtime_root.name,
        "provider_config_supplied": provider_config_supplied,
        "comparison_status": report.get("status"),
        "provider_gate": report.get("provider_gate"),
        "provider_calls_started": payload.get("provider_calls_started") is True,
        "arm_definitions": report.get("arm_definitions"),
        "arm_summary": [
            {
                "arm_id": item.get("arm_id"),
                "status": item.get("status"),
                "provider_calls_started": item.get("provider_calls_started") is True,
                "retry_count": int(item.get("retry_count") or 0),
                "block_ids": [
                    str(block.get("block_id"))
                    for block in (item.get("blocks") or [])
                    if isinstance(block, dict) and block.get("block_id")
                ],
                "fixed_asset_injection": item.get("fixed_asset_injection") is True,
                "result_ref_count": len(item.get("result_refs") or []),
                "subject_reference_asset_id": item.get("subject_reference_asset_id"),
                "reference_image_count": len(item.get("reference_images") or []),
                "included_asset_count": _included_asset_count(item.get("context_bundle")),
            }
            for item in arms
        ],
        "artifacts": payload.get("artifacts"),
        "non_claims": [
            "live provider mode is provider smoke evidence only",
            "not human acceptance",
            "not business validation",
            "not durable memory",
        ],
    }


def _included_asset_count(context_bundle: Any) -> int:
    if not isinstance(context_bundle, dict):
        return 0
    return len(context_bundle.get("included_assets") or [])


def _preflight_report(
    *,
    status: str,
    block_id: str,
    reason: str,
    live_authorized: bool,
) -> dict[str, Any]:
    return {
        "artifact_type": "studio_asset_context_live_comparison_runner_report",
        "schema_version": "0.1.0",
        "status": status,
        "runner_mode": "preflight",
        "provider_gate": {"capability": "image", "env": IMAGE_GATE, "status": "ready_not_run" if _image_gate_ready() else "blocked"},
        "live_call_authorized": live_authorized,
        "provider_calls_started": False,
        "blocks": [{"block_id": block_id, "reason": reason}],
        "non_claims": [
            "preflight only",
            "not live provider smoke",
            "not human acceptance",
            "not business validation",
        ],
    }


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def _image_gate_ready() -> bool:
    return os.environ.get(IMAGE_GATE, "").strip().lower() in {"1", "true", "yes", "on"}


def _mime_type(path: str) -> str:
    suffix = Path(path).suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".webp":
        return "image/webp"
    return "image/png"


if __name__ == "__main__":
    raise SystemExit(main())
