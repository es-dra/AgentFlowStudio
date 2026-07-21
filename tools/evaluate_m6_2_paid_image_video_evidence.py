from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agentflow.harness.json_io import write_json


PUBLIC_IMAGE_PRICE_USD = 0.0377
CONSERVATIVE_VIDEO_PRICE_USD_PER_SEC = 0.25
REQUIRED_CLEAN_CASES = 2
FULL_CASES = ("dialogue_room", "four_person_action", "sci_fi_chamber")


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only evaluator for M6.2 paid image/video evidence.")
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument("--budget-usd", default=100.0, type=float)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = evaluate(args.run_root.resolve(), budget_usd=args.budget_usd)
    if args.output is not None:
        write_json(args.output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["verdict"] == "PASS" else 1


def evaluate(run_root: Path, *, budget_usd: float = 100.0) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    if not run_root.exists():
        findings.append({"severity": "P0", "scope": "run_root", "issue": "missing evidence run root", "path": str(run_root)})
        return _report(run_root, budget_usd, [], [], issues, findings)
    if _is_inside_git_worktree(run_root):
        findings.append({"severity": "P0", "scope": "run_root", "issue": "evidence root is inside a Git worktree", "path": str(run_root)})

    smoke = _evaluate_smoke(run_root, findings, issues)
    cases = [_evaluate_case(run_root, case_id, findings, issues) for case_id in FULL_CASES]
    clean_cases = [case for case in cases if case["clean_counted"]]
    if len(clean_cases) < REQUIRED_CLEAN_CASES:
        findings.append(
            {
                "severity": "P0",
                "scope": "cases",
                "issue": "fewer than two complete clean paid cases",
                "clean_case_count": len(clean_cases),
            }
        )
    case_ids = {case["case_id"] for case in clean_cases}
    for expected in ("dialogue_room", "four_person_action"):
        if expected not in case_ids:
            findings.append({"severity": "P1", "scope": expected, "issue": "expected counted case is not clean"})

    budget = _estimate_budget(smoke, cases, budget_usd)
    if budget["conservative_estimated_total_usd"] > budget_usd:
        findings.append({"severity": "P0", "scope": "budget", "issue": "conservative estimate exceeds gate budget", **budget})

    return _report(run_root, budget_usd, smoke, cases, issues, findings, budget=budget)


def _evaluate_smoke(run_root: Path, findings: list[dict[str, Any]], issues: list[dict[str, Any]]) -> dict[str, Any]:
    smoke_root = run_root / "paid_smoke"
    smoke_qa_path = smoke_root / "paid_smoke_technical_qa.json"
    summary: dict[str, Any] = {
        "status": "FAIL",
        "root": str(smoke_root),
        "image_status": "missing",
        "video_status": "missing",
        "resolved_failures": [],
        "estimated_image_count": 0,
        "estimated_video_seconds": 0.0,
    }
    if not smoke_qa_path.exists():
        findings.append({"severity": "P0", "scope": "paid_smoke", "issue": "missing smoke QA report"})
        return summary
    qa = _read_json(smoke_qa_path)
    summary["status"] = str(qa.get("status") or "FAIL")
    image = qa.get("image_retry_safe_reference") or qa.get("image_smoke") or {}
    video = qa.get("video_safe_reference") or {}
    summary["image_status"] = str(image.get("status") or "missing")
    summary["video_status"] = str(video.get("status") or "missing")
    summary["image_model"] = image.get("model") or qa.get("image_smoke", {}).get("model")
    summary["video_model"] = video.get("model")
    summary["estimated_image_count"] = sum(
        1
        for key in ("image_smoke", "image_retry_safe_reference")
        if isinstance(qa.get(key), dict) and qa[key].get("status") == "PASS"
    )
    video_outputs = video.get("outputs") if isinstance(video.get("outputs"), list) else []
    decode = qa.get("decode") if isinstance(qa.get("decode"), dict) else {}
    decoded_duration = float(decode.get("duration_sec") or 0.0)
    output_duration = sum(float(item.get("duration_sec") or 0.0) for item in video_outputs)
    summary["estimated_video_seconds"] = round(decoded_duration or output_duration, 3)
    for key in ("video_first_fail", "video_retry_fail"):
        item = qa.get(key)
        if isinstance(item, dict) and item.get("status") == "FAIL":
            summary["resolved_failures"].append(
                {
                    "id": f"m6_2_smoke_{key}",
                    "severity": "P1",
                    "status": "resolved",
                    "provider": item.get("provider"),
                    "safe_error": item.get("safe_error"),
                    "fix": "safe reference image and provider-safe video prompt succeeded without reusing the failed artifact",
                }
            )
    if summary["status"] != "PASS" or summary["image_status"] != "PASS" or summary["video_status"] != "PASS":
        findings.append({"severity": "P0", "scope": "paid_smoke", "issue": "paid image/video smoke did not pass"})
    if summary["resolved_failures"]:
        issues.extend(summary["resolved_failures"])
    return summary


def _evaluate_case(
    run_root: Path,
    case_id: str,
    findings: list[dict[str, Any]],
    issues: list[dict[str, Any]],
) -> dict[str, Any]:
    case_path = run_root / "cases" / case_id / "case_result.json"
    run_dir = run_root / "candidate_runtime" / "projects" / f"m6-2-{case_id}" / "adaptive_canvas_v2" / "paid-media-v2"
    result = _read_json(case_path) if case_path.exists() else {}
    delivery = _read_json(run_dir / "delivery_manifest.json") if (run_dir / "delivery_manifest.json").exists() else {}
    qa = _read_json(run_dir / "qa" / "technical_qa.json") if (run_dir / "qa" / "technical_qa.json").exists() else {}
    ledger = _read_json(run_dir / "charge_ledger.json") if (run_dir / "charge_ledger.json").exists() else {}
    attempts = ledger.get("attempts") if isinstance(ledger.get("attempts"), list) else []
    statuses = Counter(str(item.get("status")) for item in attempts)
    duplicate_attempt_ids = sorted(item for item, count in Counter(str(attempt.get("attempt_id")) for attempt in attempts).items() if count > 1)
    nonterminal = [item for item in attempts if item.get("status") not in {"succeeded", "failed"}]
    succeeded_with_error = [item for item in attempts if item.get("status") == "succeeded" and item.get("safe_error")]
    unresolved_failed = _unresolved_failed_attempts(attempts)

    shot_count = int(delivery.get("shot_count") or result.get("shot_count") or 0)
    keyframe_count = int(delivery.get("keyframe_count") or 0)
    video_chunk_count = int(delivery.get("video_chunk_count") or 0)
    final_path = run_dir / "final" / "adaptive_canvas_v2_final.mp4"
    contact_sheet = run_dir / "qa" / "contact_sheet_1fps.jpg"
    probe = _ffprobe(final_path) if final_path.exists() else {"status": "FAIL", "error": "missing final video"}

    case_summary = {
        "case_id": case_id,
        "status": str(result.get("status") or "missing"),
        "run_root": str(run_dir),
        "source_m6_1_case_report": result.get("source_m6_1_case_report"),
        "shot_count": shot_count,
        "keyframe_count": keyframe_count,
        "video_chunk_count": video_chunk_count,
        "final_duration_sec": delivery.get("final_duration_sec") or result.get("video_seconds"),
        "final_sha256": delivery.get("final_sha256") or result.get("final_sha256"),
        "final_path": str(final_path),
        "contact_sheet_path": str(contact_sheet),
        "contact_sheet_sha256": qa.get("contact_sheet_sha256"),
        "technical_qa_status": qa.get("status"),
        "technical_qa_findings": qa.get("findings") or [],
        "ffprobe_status": probe.get("status"),
        "idempotency": result.get("idempotency") or {},
        "paid_attempt_count": int(ledger.get("paid_attempt_count") or 0),
        "attempt_rows": len(attempts),
        "attempt_statuses": dict(statuses),
        "duplicate_attempt_ids": duplicate_attempt_ids,
        "nonterminal_attempt_count": len(nonterminal),
        "succeeded_with_error_count": len(succeeded_with_error),
        "unresolved_failed_attempt_count": len(unresolved_failed),
        "estimated_image_count": sum(1 for item in attempts if item.get("capability") == "image" and item.get("provider_calls_started") is True),
        "estimated_video_seconds": _case_video_seconds(delivery, attempts),
        "clean_counted": False,
        "classification": "pending",
    }

    structural_ok = (
        result.get("status") == "PASS"
        and delivery.get("status") == "registered"
        and qa.get("status") == "pass"
        and result.get("idempotency", {}).get("status") == "PASS"
        and shot_count >= 2
        and keyframe_count == shot_count
        and video_chunk_count == shot_count
        and final_path.exists()
        and contact_sheet.exists()
        and probe.get("status") == "PASS"
        and not any(str(item.get("severity")) in {"P0", "P1"} for item in qa.get("findings") or [])
    )
    ledger_clean = not duplicate_attempt_ids and not nonterminal and not succeeded_with_error and not unresolved_failed
    case_summary["clean_counted"] = bool(structural_ok and ledger_clean)
    if case_summary["clean_counted"]:
        case_summary["classification"] = "CLEAN_FULL_CASE"
    elif structural_ok:
        case_summary["classification"] = "RECOVERY_EVIDENCE_NOT_COUNTED"
    else:
        case_summary["classification"] = "INCOMPLETE_OR_FAILED"

    if case_summary["classification"] == "RECOVERY_EVIDENCE_NOT_COUNTED":
        issues.append(
            {
                "id": f"m6_2_{case_id}_recovery_ledger",
                "severity": "P1",
                "status": "fixed_in_code_not_counted_as_clean_case",
                "case_id": case_id,
                "duplicate_attempt_ids": duplicate_attempt_ids,
                "nonterminal_attempt_count": len(nonterminal),
                "succeeded_with_error_count": len(succeeded_with_error),
                "fix": "charge ledger attempt ids now include the prompt fingerprint and completed attempts cannot be resurrected",
            }
        )
    if not structural_ok:
        findings.append({"severity": "P0", "scope": case_id, "issue": "case structural media contract did not pass", "summary": case_summary})
    elif not ledger_clean and case_id in {"dialogue_room", "four_person_action"}:
        findings.append({"severity": "P1", "scope": case_id, "issue": "expected counted case has ledger defects", "summary": case_summary})
    for failed in _resolved_failed_attempts(attempts):
        issues.append(
            {
                "id": f"m6_2_{case_id}_{failed['stage']}_retry",
                "severity": "P2",
                "status": "resolved",
                "case_id": case_id,
                "stage": failed["stage"],
                "safe_error": failed.get("safe_error"),
                "fix": "same artifact fingerprint later succeeded within retry cap without duplicating final truth",
            }
        )
    return case_summary


def _unresolved_failed_attempts(attempts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_fingerprint: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for attempt in attempts:
        by_fingerprint[str(attempt.get("charge_fingerprint"))].append(attempt)
    unresolved = []
    for attempt in attempts:
        if attempt.get("status") != "failed":
            continue
        siblings = by_fingerprint[str(attempt.get("charge_fingerprint"))]
        if not any(item.get("status") == "succeeded" for item in siblings):
            unresolved.append(attempt)
    return unresolved


def _resolved_failed_attempts(attempts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unresolved_ids = {id(item) for item in _unresolved_failed_attempts(attempts)}
    return [item for item in attempts if item.get("status") == "failed" and id(item) not in unresolved_ids]


def _case_video_seconds(delivery: dict[str, Any], attempts: list[dict[str, Any]]) -> float:
    final_duration = float(delivery.get("final_duration_sec") or 0.0)
    failed_video_starts = sum(
        1
        for item in attempts
        if item.get("capability") == "video" and item.get("provider_calls_started") is True and item.get("status") == "failed"
    )
    return final_duration + failed_video_starts * 10.0


def _estimate_budget(smoke: dict[str, Any], cases: list[dict[str, Any]], budget_usd: float) -> dict[str, Any]:
    image_count = float(smoke.get("estimated_image_count") or 0) + sum(float(case.get("estimated_image_count") or 0) for case in cases)
    video_seconds = float(smoke.get("estimated_video_seconds") or 0.0) + sum(float(case.get("estimated_video_seconds") or 0.0) for case in cases)
    estimated = image_count * PUBLIC_IMAGE_PRICE_USD + video_seconds * CONSERVATIVE_VIDEO_PRICE_USD_PER_SEC
    return {
        "budget_cap_usd": budget_usd,
        "actual_receipt_status": "provider adapters did not return billed-cost receipts; estimate is conservative evidence-only accounting",
        "estimated_image_count": int(image_count),
        "estimated_video_seconds": round(video_seconds, 3),
        "image_unit_usd": PUBLIC_IMAGE_PRICE_USD,
        "video_unit_usd_per_sec": CONSERVATIVE_VIDEO_PRICE_USD_PER_SEC,
        "conservative_estimated_total_usd": round(estimated, 4),
        "within_budget": estimated <= budget_usd,
    }


def _report(
    run_root: Path,
    budget_usd: float,
    smoke: dict[str, Any] | list[Any],
    cases: list[dict[str, Any]],
    issues: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    *,
    budget: dict[str, Any] | None = None,
) -> dict[str, Any]:
    p0 = [item for item in findings if item.get("severity") == "P0"]
    p1 = [item for item in findings if item.get("severity") == "P1"]
    return {
        "schema_version": "afs.m6_2.paid_image_video_evidence_evaluator.v0.1",
        "verdict": "PASS" if not p0 and not p1 else "FAIL",
        "P0": len(p0),
        "P1": len(p1),
        "run_root": str(run_root),
        "provider_services": {
            "image": {"service_id": "image_relay", "provider": "api_relay", "model": "gpt-image-2"},
            "video": {"service_id": "seedance_i2v", "provider": "volc_seedance", "model": "doubao-seedance-2-0-fast"},
        },
        "budget": budget or {"budget_cap_usd": budget_usd},
        "paid_smoke": smoke,
        "clean_case_count": sum(1 for case in cases if case.get("clean_counted")),
        "cases": cases,
        "issue_ledger": {
            "P0_open": len(p0),
            "P1_open": len(p1),
            "resolved": issues,
            "open_findings": findings,
        },
        "non_claims": [
            "not_owner_human_acceptance",
            "not_business_validation",
            "not_public_release",
            "not_media_provider_quality_certification",
            "not_paid_provider_invoice",
        ],
    }


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def _ffprobe(path: Path) -> dict[str, Any]:
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,size:stream=codec_type,width,height,r_frame_rate,nb_frames",
            "-of",
            "json",
            str(path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return {"status": "FAIL", "stderr_tail": proc.stderr[-500:]}
    try:
        payload = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"status": "FAIL", "stderr_tail": "ffprobe returned invalid JSON"}
    return {"status": "PASS", **payload}


def _is_inside_git_worktree(path: Path) -> bool:
    proc = subprocess.run(["git", "-C", str(path), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return proc.returncode == 0 and bool(proc.stdout.strip())


if __name__ == "__main__":
    raise SystemExit(main())
