from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PACKAGE_REPORT = "package_report.md"


def build_package_report(run_dir: str | Path) -> str:
    root = Path(run_dir)
    package = _load_json(root / "finished_package_manifest.json")
    run_manifest = _load_json(root / "run_manifest.json")
    quality = _load_json(root / "quality_report.json")
    review = _load_json(root / "review_report.json")
    clip_plan = _load_json(root / "clip_plan.json")
    score_report = _load_json(root / "highlight_score_report.json")
    final_video = _load_json(root / "final_video_manifest.json")

    lines: list[str] = [
        "# NarratoCut Package Report",
        "",
        "## Summary",
        f"- Run ID: {_value(run_manifest, 'run_id', root.name)}",
        f"- Workflow: {_value(run_manifest, 'workflow', 'unknown')}",
        f"- Package ID: {_value(package, 'package_id', 'unknown')}",
        f"- Package status: {_value(package, 'status', 'unknown')}",
        f"- Review status: {_value(review, 'status', 'missing')}",
        f"- Quality status: {_value(quality, 'status', 'missing')}",
        f"- Final duration: {_duration(final_video)}",
        "",
        "## Final Assets",
    ]
    lines.extend(_asset_lines(package))
    lines.extend(["", "## Selected Clips"])
    lines.extend(_clip_lines(clip_plan, score_report))
    lines.extend(["", "## Rejected Candidates"])
    lines.extend(_rejected_candidate_lines(score_report))
    lines.extend(["", "## Quality Gates"])
    lines.extend(_quality_lines(quality, review))
    return "\n".join(lines).rstrip() + "\n"


def write_package_report(run_dir: str | Path, report_name: str = PACKAGE_REPORT) -> Path:
    root = Path(run_dir)
    output_path = root / report_name
    output_path.write_text(build_package_report(root), encoding="utf-8")
    return output_path


def _asset_lines(package: dict[str, Any] | None) -> list[str]:
    assets = package.get("assets") if package else None
    if not isinstance(assets, list) or not assets:
        return ["- No assets declared."]
    lines: list[str] = []
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        role = asset.get("role", "unknown")
        path = asset.get("path", "missing")
        exists = asset.get("exists", False)
        size = asset.get("size_bytes")
        size_text = f", {size} bytes" if isinstance(size, int) else ""
        lines.append(f"- {role}: `{path}` ({'exists' if exists else 'missing'}{size_text})")
    return lines or ["- No assets declared."]


def _clip_lines(clip_plan: dict[str, Any] | None, score_report: dict[str, Any] | None) -> list[str]:
    segments = clip_plan.get("segments") if clip_plan else None
    if not isinstance(segments, list) or not segments:
        return ["- No selected clips found."]
    score_index = _score_index(score_report)
    lines: list[str] = []
    for index, segment in enumerate(segments, start=1):
        if not isinstance(segment, dict):
            continue
        metadata = segment.get("metadata") if isinstance(segment.get("metadata"), dict) else {}
        candidate_id = metadata.get("candidate_id")
        scored = score_index.get(candidate_id) if candidate_id else None
        start = _float(segment.get("start_sec"))
        end = _float(segment.get("end_sec"))
        duration = end - start if start is not None and end is not None else None
        lines.extend(
            [
                f"### Clip {index}",
                f"- Source time: {_time_range(start, end)}",
                f"- Duration: {_seconds(duration)}",
                f"- Candidate ID: `{candidate_id or 'missing'}`",
                f"- Score: {_score(scored)}",
                f"- Reasons: {_reasons(scored)}",
                f"- Text: {segment.get('text') or '(empty)'}",
                "",
            ]
        )
    return lines[:-1] if lines and lines[-1] == "" else lines


def _rejected_candidate_lines(score_report: dict[str, Any] | None) -> list[str]:
    candidates = score_report.get("candidates") if score_report else None
    if not isinstance(candidates, list):
        candidates = score_report.get("ranked_candidates") if score_report else None
    if not isinstance(candidates, list):
        return ["- No score report available."]
    selected_ids = _selected_candidate_ids(score_report)
    rejected = [
        candidate
        for candidate in candidates
        if isinstance(candidate, dict)
        and (candidate.get("decision") == "rejected" or str(candidate.get("candidate_id")) not in selected_ids)
    ]
    if not rejected:
        return ["- No rejected candidates recorded."]
    lines: list[str] = []
    for candidate in rejected[:10]:
        reasons = candidate.get("rejection_reasons")
        reason_text = ", ".join(str(item) for item in reasons) if isinstance(reasons, list) else "unknown"
        lines.append(
            f"- `{candidate.get('candidate_id', 'unknown')}` "
            f"{_time_range(_float(candidate.get('start_sec')), _float(candidate.get('end_sec')))}: {reason_text}"
        )
    if len(rejected) > 10:
        lines.append(f"- ... {len(rejected) - 10} more rejected candidates")
    return lines


def _quality_lines(quality: dict[str, Any] | None, review: dict[str, Any] | None) -> list[str]:
    lines = [
        f"- inspect-run: {_value(quality, 'status', 'missing')}",
        f"- review-run: {_value(review, 'status', 'missing')}",
    ]
    quality_warnings = quality.get("warnings") if quality else None
    if isinstance(quality_warnings, list) and quality_warnings:
        lines.append("- quality warnings:")
        lines.extend(f"  - {warning}" for warning in quality_warnings)
    review_summary = review.get("summary") if review else None
    if isinstance(review_summary, dict):
        lines.append(
            "- review checks: "
            f"{review_summary.get('passed', 0)} passed / "
            f"{review_summary.get('failed', 0)} failed / "
            f"{review_summary.get('warnings', 0)} warnings"
        )
    return lines


def _score_index(score_report: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    candidates = score_report.get("candidates") if score_report else None
    if not isinstance(candidates, list):
        candidates = score_report.get("ranked_candidates") if score_report else None
    if not isinstance(candidates, list):
        return {}
    return {
        str(candidate["candidate_id"]): candidate
        for candidate in candidates
        if isinstance(candidate, dict) and candidate.get("candidate_id")
    }


def _selected_candidate_ids(score_report: dict[str, Any] | None) -> set[str]:
    selected = score_report.get("selected_candidate_ids") if score_report else None
    if isinstance(selected, list):
        return {str(candidate_id) for candidate_id in selected}
    candidates = score_report.get("candidates") if score_report else None
    if isinstance(candidates, list):
        return {
            str(candidate["candidate_id"])
            for candidate in candidates
            if isinstance(candidate, dict) and candidate.get("decision") == "selected" and candidate.get("candidate_id")
        }
    return set()


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _duration(final_video: dict[str, Any] | None) -> str:
    if not final_video:
        return "unknown"
    return _seconds(_float(final_video.get("duration_sec")))


def _value(payload: dict[str, Any] | None, key: str, default: str) -> str:
    if not payload:
        return default
    value = payload.get(key)
    return str(value) if value is not None else default


def _reasons(candidate: dict[str, Any] | None) -> str:
    if not candidate:
        return "missing"
    reasons = candidate.get("reasons")
    if isinstance(reasons, list) and reasons:
        return ", ".join(str(reason) for reason in reasons)
    return "none"


def _score(candidate: dict[str, Any] | None) -> str:
    if not candidate:
        return "missing"
    score = _float(candidate.get("total_score"))
    return f"{score:.3f}" if score is not None else "missing"


def _time_range(start: float | None, end: float | None) -> str:
    if start is None or end is None:
        return "unknown"
    return f"{start:.2f}s - {end:.2f}s"


def _seconds(value: float | None) -> str:
    return f"{value:.2f}s" if value is not None else "unknown"


def _float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
