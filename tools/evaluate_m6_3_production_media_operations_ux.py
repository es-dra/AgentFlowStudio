"""Evaluator for the M6.3 production media operations UX candidate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


EXPECTED_CASES = ("dialogue_room", "four_person_action", "sci_fi_chamber")
EXPECTED_VIEWPORTS = ("1440x900", "1024x768", "800x900")
EXPECTED_ROLES = (
    "first_time_creator",
    "screenwriter",
    "director_storyboard",
    "art_continuity",
    "producer",
    "editor_media_reviewer",
    "runtime_operator",
    "owner_decision_maker",
    "mobile_reviewer",
    "keyboard_low_vision",
)
EXPECTED_MICRO_CHECKS = (
    "first_screen_10s",
    "primary_next_action_visible",
    "paid_action_preview_not_execution",
    "safe_media_urls",
    "version_compare_available",
    "recovery_cost_state_available",
    "keyboard_focus_visible_sequence",
    "clean_and_recovery_cases_present",
)


def evaluate(round_a_report: Path, round_b_report: Path, issue_ledger: Path) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    round_a = _load_json(round_a_report, findings, "round_a_report")
    round_b = _load_json(round_b_report, findings, "round_b_report")
    ledger = _load_json(issue_ledger, findings, "issue_ledger")

    for label, report in (("round_a", round_a), ("round_b", round_b)):
      _evaluate_browser_round(label, report, findings)
    _evaluate_issue_ledger(ledger, findings)
    return _report(findings, round_a, round_b, ledger)


def _load_json(path: Path, findings: list[dict[str, str]], label: str) -> dict[str, Any]:
    if not path.exists():
        findings.append({"severity": "P0", "issue": f"{label} missing: {path}"})
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        findings.append({"severity": "P0", "issue": f"{label} is not valid JSON: {exc}"})
        return {}
    if not isinstance(payload, dict):
        findings.append({"severity": "P0", "issue": f"{label} must be a JSON object"})
        return {}
    return payload


def _evaluate_browser_round(label: str, report: dict[str, Any], findings: list[dict[str, str]]) -> None:
    if not report:
        return
    if report.get("status") != "passed":
        findings.append({"severity": "P0", "issue": f"{label} browser QA did not pass"})
    if int(report.get("console_error_count") or 0) != 0:
        findings.append({"severity": "P0", "issue": f"{label} console errors are nonzero"})
    if int(report.get("response_error_count") or 0) != 0:
        findings.append({"severity": "P0", "issue": f"{label} failed responses are nonzero"})

    cases = report.get("cases") if isinstance(report.get("cases"), dict) else {}
    for case_id in EXPECTED_CASES:
        for viewport in EXPECTED_VIEWPORTS:
            key = f"{case_id}:{viewport}"
            item = cases.get(key)
            if not isinstance(item, dict):
                findings.append({"severity": "P0", "issue": f"{label} missing browser case {key}"})
                continue
            if float(item.get("video_duration_sec") or 0) <= 0:
                findings.append({"severity": "P0", "issue": f"{label} video metadata missing for {key}"})
            for field in ("media_url_safe", "canvas_first_screen", "storyboard_operations", "redo_preview", "redo_version_compare", "recovery_and_cost_state"):
                if item.get(field) is not True:
                    findings.append({"severity": "P0", "issue": f"{label} {key} did not prove {field}"})
            if int(item.get("provider_dispatch_count") or 0) != 0:
                findings.append({"severity": "P0", "issue": f"{label} {key} triggered provider dispatch"})

    roles = report.get("role_task_completion_matrix") if isinstance(report.get("role_task_completion_matrix"), dict) else {}
    for role in EXPECTED_ROLES:
        if roles.get(role, {}).get("completed") is not True:
            findings.append({"severity": "P1", "issue": f"{label} role task incomplete: {role}"})

    micro = report.get("micro_experience_checks") if isinstance(report.get("micro_experience_checks"), dict) else {}
    for check in EXPECTED_MICRO_CHECKS:
        if micro.get(check) is not True:
            findings.append({"severity": "P1", "issue": f"{label} micro UX check failed: {check}"})

    screenshots = report.get("screenshots") if isinstance(report.get("screenshots"), dict) else {}
    if len(screenshots) < 54:
        findings.append({"severity": "P1", "issue": f"{label} has insufficient screenshot evidence: {len(screenshots)}"})
    for key, value in screenshots.items():
        path = Path(str(value))
        if not path.exists():
            findings.append({"severity": "P1", "issue": f"{label} screenshot missing for {key}: {path}"})


def _evaluate_issue_ledger(ledger: dict[str, Any], findings: list[dict[str, str]]) -> None:
    if not ledger:
        return
    issues = ledger.get("issues")
    if not isinstance(issues, list) or not issues:
        findings.append({"severity": "P1", "issue": "issue ledger must contain at least one resolved issue from the UX loop"})
        return
    required = ("id", "severity", "status", "symptom", "user_impact", "root_cause_layer", "fix", "retest")
    for issue in issues:
        if not isinstance(issue, dict):
            findings.append({"severity": "P1", "issue": "issue ledger contains a non-object item"})
            continue
        missing = [field for field in required if not issue.get(field)]
        if missing:
            findings.append({"severity": "P1", "issue": f"issue {issue.get('id', '<unknown>')} missing fields: {', '.join(missing)}"})
        severity = str(issue.get("severity") or "").upper()
        status = str(issue.get("status") or "").lower()
        if severity in {"P0", "P1"} and status != "resolved":
            findings.append({"severity": "P0", "issue": f"{severity} issue is not resolved: {issue.get('id')}"})
        if severity == "P2" and issue.get("high_impact") is True and status != "resolved":
            findings.append({"severity": "P1", "issue": f"high-impact P2 issue is not resolved: {issue.get('id')}"})


def _report(findings: list[dict[str, str]], round_a: dict[str, Any], round_b: dict[str, Any], ledger: dict[str, Any]) -> dict[str, Any]:
    p0 = sum(item["severity"] == "P0" for item in findings)
    p1 = sum(item["severity"] == "P1" for item in findings)
    p2_open = 0
    if isinstance(ledger.get("issues"), list):
        p2_open = sum(
            str(issue.get("severity") or "").upper() == "P2" and str(issue.get("status") or "").lower() != "resolved"
            for issue in ledger["issues"]
            if isinstance(issue, dict)
        )
    return {
        "schema_version": "afs.m6_3.production_media_operations_ux_evaluator.v0.1",
        "verdict": "PASS" if not findings else "FAIL",
        "P0": p0,
        "P1": p1,
        "open_P2": p2_open,
        "findings": findings,
        "rounds": {
            "A": _round_summary(round_a),
            "B": _round_summary(round_b),
        },
        "issue_count": len(ledger.get("issues") or []) if isinstance(ledger, dict) else 0,
        "provider_dispatch_count": 0,
        "cost_usd": 0,
        "non_claims": [
            "not_owner_acceptance",
            "not_business_validation",
            "not_paid_provider_smoke",
            "not_generated_media_commercial_qa",
            "not_public_release",
        ],
    }


def _round_summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": report.get("status"),
        "case_count": len(report.get("cases") or {}) if isinstance(report, dict) else 0,
        "screenshot_count": len(report.get("screenshots") or {}) if isinstance(report, dict) else 0,
        "console_error_count": report.get("console_error_count"),
        "response_error_count": report.get("response_error_count"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--round-a-report", required=True)
    parser.add_argument("--round-b-report", required=True)
    parser.add_argument("--issue-ledger", required=True)
    args = parser.parse_args()
    report = evaluate(Path(args.round_a_report), Path(args.round_b_report), Path(args.issue_ledger))
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
