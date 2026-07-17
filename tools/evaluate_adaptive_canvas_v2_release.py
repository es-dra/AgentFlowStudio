from __future__ import annotations

import argparse
import json
import logging
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from agentflow_studio.production.adaptive_canvas_v2 import (  # noqa: E402
    AdaptiveRunOptions,
    ChargeLedger,
    build_script_truth_from_profile,
    compile_duration_chunks,
    run_adaptive_canvas_production,
)
from agentflow_studio.production.real_anime_4shot import (  # noqa: E402
    alternate_no_provider_profile,
    real_anime_4shot_paid_profile,
)
from apps.api.runtime_service import create_runtime_app  # noqa: E402
from apps.api.runtime_store import RuntimeStore, read_json  # noqa: E402


def main() -> int:
    logging.getLogger("httpx").setLevel(logging.WARNING)
    parser = argparse.ArgumentParser(description="Read-only evaluator for Adaptive Canvas v2 release candidate.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    report = evaluate(args.root)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["verdict"] == "PASS" else 1


def evaluate(root: Path) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    core_path = root / "agentflow_studio" / "production" / "adaptive_canvas_v2.py"
    profile_path = root / "agentflow_studio" / "production" / "real_anime_4shot.py"
    core_text = core_path.read_text(encoding="utf-8")
    profile_text = profile_path.read_text(encoding="utf-8")
    for forbidden in ("SHOT_COUNT = 4", "SHOT_DURATION_SEC = 15", "FINAL_DURATION_SEC = 60", "range(1, 5)"):
        if forbidden in core_text:
            findings.append({"severity": "P1", "scope": "core", "issue": f"fixed profile value in adaptive core: {forbidden}"})
    if "duration_sec=15.0" not in profile_text:
        findings.append({"severity": "P1", "scope": "profile", "issue": "paid profile no longer encodes 4x15 test constraint"})

    with tempfile.TemporaryDirectory(prefix="afs-adaptive-eval-") as tmp_name:
        runtime_root = Path(tmp_name) / "runtime"
        paid = real_anime_4shot_paid_profile()
        counter = alternate_no_provider_profile()
        paid_result = run_adaptive_canvas_production(
            AdaptiveRunOptions(
                runtime_root=runtime_root,
                project_id="eval-paid-profile",
                run_id="run-001",
                profile=paid,
                mode="fake",
            )
        )
        counter_result = run_adaptive_canvas_production(
            AdaptiveRunOptions(
                runtime_root=runtime_root,
                project_id="eval-counter-profile",
                run_id="run-001",
                profile=counter,
                mode="fake",
            )
        )
        store = RuntimeStore(runtime_root)
        paid_workspace = store.load_production_run("eval-paid-profile", "run-001")
        counter_workspace = store.load_production_run("eval-counter-profile", "run-001")
        _check_paid_profile(paid_result, paid_workspace, findings)
        _check_counter_profile(counter_result, counter_workspace, findings)
        _check_api_projection(runtime_root, findings)
        _check_ledger(runtime_root, findings)

    _check_compiler(findings)
    verdict = "PASS" if not any(item["severity"] in {"P0", "P1"} for item in findings) else "FAIL"
    return {
        "schema_version": "afs.adaptive_canvas_v2.evaluator.v0.1",
        "verdict": verdict,
        "p0": sum(1 for item in findings if item["severity"] == "P0"),
        "p1": sum(1 for item in findings if item["severity"] == "P1"),
        "findings": findings,
        "provider_dispatch_count": 0,
        "non_claims": [
            "not_provider_smoke",
            "not_generated_media_quality",
            "not_human_acceptance",
            "not_business_validation",
        ],
    }


def _check_paid_profile(result: dict[str, Any], run: dict[str, Any], findings: list[dict[str, str]]) -> None:
    if result["paid_attempt_count"] != 0:
        findings.append({"severity": "P0", "scope": "paid_fake", "issue": "fake evaluator started provider attempts"})
    durations = [shot["target_duration_sec"] for shot in run["shots"]]
    if durations != [15.0, 15.0, 15.0, 15.0]:
        findings.append({"severity": "P1", "scope": "paid_profile", "issue": "4x15 paid profile changed"})
    if run["timeline"]["duration_sec"] != 60.0:
        findings.append({"severity": "P1", "scope": "paid_profile", "issue": "paid profile timeline is not 60 seconds"})
    if {shot["generation_strategy"] for shot in run["shots"]} != {"image_to_video"}:
        findings.append({"severity": "P1", "scope": "paid_profile", "issue": "paid profile should use image_to_video anchors"})


def _check_counter_profile(result: dict[str, Any], run: dict[str, Any], findings: list[dict[str, str]]) -> None:
    if result["paid_attempt_count"] != 0:
        findings.append({"severity": "P0", "scope": "counter_fake", "issue": "counterexample fake run started provider attempts"})
    durations = [shot["target_duration_sec"] for shot in run["shots"]]
    if len(durations) == 4 or all(duration == 15.0 for duration in durations):
        findings.append({"severity": "P1", "scope": "counter_profile", "issue": "counterexample did not prove adaptive durations"})
    first = run["shots"][0]
    second = run["shots"][1]
    if first["generation_strategy"] != "text_to_video" or first["selected_keyframe"]["status"] != "not_required":
        findings.append({"severity": "P1", "scope": "strategy", "issue": "text_to_video path created or required a keyframe"})
    if second["generation_strategy"] != "image_to_video" or second["selected_keyframe"]["status"] != "selected":
        findings.append({"severity": "P1", "scope": "strategy", "issue": "image_to_video path did not bind selected keyframe"})
    if second["reference_binding"]["status"] != "selected":
        findings.append({"severity": "P1", "scope": "strategy", "issue": "image_to_video path did not bind reference sheet"})


def _check_api_projection(runtime_root: Path, findings: list[dict[str, str]]) -> None:
    client = TestClient(create_runtime_app(runtime_root=runtime_root))
    response = client.get("/projects/eval-counter-profile/adaptive-canvas-v2/workspace?run_id=run-001")
    if response.status_code != 200:
        findings.append({"severity": "P1", "scope": "api", "issue": f"workspace route failed: {response.status_code}"})
        return
    raw = response.text
    for forbidden in ("/tmp/", "/var/", ".mp4", "api_key", "bearer"):
        if forbidden in raw.lower():
            findings.append({"severity": "P1", "scope": "api", "issue": f"workspace exposed unsafe token: {forbidden}"})
    payload = response.json()
    if payload["shots"][0]["generation_strategy"] != "text_to_video":
        findings.append({"severity": "P1", "scope": "api", "issue": "workspace missing strategy projection"})


def _check_ledger(runtime_root: Path, findings: list[dict[str, str]]) -> None:
    ledger = read_json(runtime_root / "projects" / "eval-paid-profile" / "adaptive_canvas_v2" / "run-001" / "charge_ledger.json")
    attempts = ledger["attempts"]
    image = next(item for item in attempts if item["stage"] == "keyframe" and item["shot_id"] == "shot-001")
    video = next(item for item in attempts if item["stage"] == "video_chunk" and item["shot_id"] == "shot-001")
    if image["charge_fingerprint"] == video["charge_fingerprint"]:
        findings.append({"severity": "P1", "scope": "ledger", "issue": "image and video charge fingerprints collide"})
    cap_ledger = ChargeLedger(runtime_root / "cap-ledger.json", project_id="p", run_id="r", max_paid_attempts=1)
    first = cap_ledger.reserve(
        stage="script",
        shot_id=None,
        chunk_id=None,
        candidate_id="candidate-001",
        capability="llm",
        service_id="prompt_optimizer",
        prompt="p",
    )
    cap_ledger.mark_started(first["attempt_id"])
    try:
        second = cap_ledger.reserve(
            stage="reference_sheet",
            shot_id=None,
            chunk_id=None,
            candidate_id="candidate-001",
            capability="image",
            service_id="image_relay",
            prompt="p2",
        )
        cap_ledger.mark_started(second["attempt_id"])
    except Exception:
        return
    findings.append({"severity": "P1", "scope": "ledger", "issue": "paid attempt cap did not stop second attempt"})


def _check_compiler(findings: list[dict[str, str]]) -> None:
    script = build_script_truth_from_profile(alternate_no_provider_profile())
    if script["shots"][0]["chunk_plan"] != compile_duration_chunks(8.0, (10, 5)):
        findings.append({"severity": "P1", "scope": "duration_compiler", "issue": "script did not use canonical duration compiler"})
    if not compile_duration_chunks(12.0, (10, 5))[-1]["requires_continuity_anchor"]:
        findings.append({"severity": "P1", "scope": "duration_compiler", "issue": "multi-chunk shot lacks continuity anchor"})


if __name__ == "__main__":
    raise SystemExit(main())
