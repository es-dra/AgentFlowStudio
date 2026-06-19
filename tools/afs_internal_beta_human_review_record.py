from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ALLOWED_DECISIONS = {
    "accepted_for_next_beta_round",
    "needs_fix_before_next_beta_round",
    "blocked_by_provider_or_configuration",
}


def build_human_review_record(report: dict[str, Any], review_input: dict[str, Any]) -> dict[str, Any]:
    packet = report.get("human_review_packet") or {}
    sections = packet.get("required_sections") or []
    pass_threshold = int((packet.get("score_scale") or {}).get("pass_threshold") or 4)
    decision = _safe_token(review_input.get("decision"))
    section_scores = _section_scores(sections, review_input.get("section_scores") or {})
    warnings = _review_warnings(report, decision, section_scores, pass_threshold)
    all_scores_pass = bool(section_scores) and all(score >= pass_threshold for score in section_scores.values())
    accepted = decision == "accepted_for_next_beta_round" and all_scores_pass and not warnings
    status = decision if accepted or decision in {"needs_fix_before_next_beta_round", "blocked_by_provider_or_configuration"} and not _blocking_warnings(warnings) else "review_requires_followup"
    return {
        "artifact_type": "afs_internal_beta_human_review_record",
        "schema_version": "0.1.0",
        "status": status,
        "source_report_digest": _report_digest(report),
        "source_report_status": _safe_text(report.get("status")),
        "reviewed_at": _safe_text(review_input.get("reviewed_at")) or datetime.now(UTC).replace(microsecond=0).isoformat(),
        "reviewer": {"id": _safe_token(review_input.get("reviewer_id")) or "internal_beta_operator"},
        "decision": decision,
        "section_scores": section_scores,
        "score_summary": {
            "min_score": min(section_scores.values()) if section_scores else 0,
            "pass_threshold": pass_threshold,
            "all_required_scores_pass": all_scores_pass,
        },
        "human_acceptance_claim": decision if accepted else "not_claimed",
        "business_validation_claim": "not_claimed",
        "durable_memory_promotion": "not_claimed",
        "provider_quality_approval": "not_claimed",
        "operator_notes": _safe_text(review_input.get("notes")),
        "warnings": warnings,
        "boundaries": [
            "human review record only",
            "not business validation",
            "not durable memory promotion",
            "not provider quality approval",
        ],
    }


def write_human_review_record(report: dict[str, Any], review_input: dict[str, Any], output_path: Path) -> dict[str, Any]:
    record = build_human_review_record(report, review_input)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


def main() -> int:
    args = _parse_args()
    report = _read_json(Path(args.report))
    review_input = _read_json(Path(args.review_json))
    record = write_human_review_record(report, review_input, Path(args.output))
    print(json.dumps({"status": record["status"], "output": str(Path(args.output).resolve())}, ensure_ascii=False))
    return 0 if record["status"] != "review_requires_followup" else 2


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write a safe AFS internal beta human review record.")
    parser.add_argument("--report", required=True, help="Acceptance report JSON path.")
    parser.add_argument("--review-json", required=True, help="Operator review input JSON path.")
    parser.add_argument("--output", required=True, help="Safe human review record JSON output path.")
    return parser.parse_args()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _section_scores(sections: list[dict[str, Any]], raw_scores: dict[str, Any]) -> dict[str, int]:
    scores: dict[str, int] = {}
    for section in sections:
        section_id = _safe_token(section.get("section_id"))
        raw_score = raw_scores.get(section_id)
        try:
            score = int(raw_score)
        except (TypeError, ValueError):
            continue
        if 1 <= score <= 5:
            scores[section_id] = score
    return scores


def _review_warnings(report: dict[str, Any], decision: str, scores: dict[str, int], pass_threshold: int) -> list[str]:
    packet = report.get("human_review_packet") or {}
    required_ids = {_safe_token(section.get("section_id")) for section in packet.get("required_sections") or []}
    warnings: list[str] = []
    if report.get("status") != "contract_verified_pending_human_acceptance":
        warnings.append("source_report_not_pending_human_acceptance")
    if decision not in ALLOWED_DECISIONS:
        warnings.append("unknown_decision")
    if set(scores) != required_ids:
        warnings.append("missing_required_section_score")
    if any(score < pass_threshold for score in scores.values()):
        warnings.append("score_below_pass_threshold")
    return warnings


def _blocking_warnings(warnings: list[str]) -> bool:
    return any(item in {"source_report_not_pending_human_acceptance", "unknown_decision", "missing_required_section_score"} for item in warnings)


def _report_digest(report: dict[str, Any]) -> str:
    payload = json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _safe_token(value: Any) -> str:
    text = _safe_text(value)
    safe = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in text.strip())
    return safe[:80].strip("_")


def _safe_text(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"https?://\S+", "[url-redacted]", text)
    text = re.sub(r"[A-Za-z]:\\[^\s`'\"<>]+", "[local-path]", text)
    text = re.sub(r"/(?:home|opt|tmp|var)/[^\s`'\"<>]+", "[server-path]", text)
    replacements = {
        "session_token": "session credential",
        "signed_url": "signed link",
        "provider_raw_response": "provider raw payload",
        "invite": "credential",
    }
    for old, new in replacements.items():
        text = text.replace(old, new).replace(old.upper(), new).replace(old.title(), new)
    return text.replace("signed", "redacted-link")


if __name__ == "__main__":
    raise SystemExit(main())
