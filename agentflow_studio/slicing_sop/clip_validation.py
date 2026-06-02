from __future__ import annotations

from pathlib import PurePath

from agentflow_studio.schemas import (
    ClipPlan,
    ClipPlanValidationReport,
    ROISettings,
    ValidationCheck,
    ValidationIssue,
    VideoMetadata,
)


def validate_clip_plan(
    clip_plan: ClipPlan,
    roi_settings: ROISettings,
    video_metadata: VideoMetadata,
    ffmpeg_available: bool,
) -> ClipPlanValidationReport:
    checks: list[ValidationCheck] = []
    hard_errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []

    _check_ffmpeg_available(ffmpeg_available, checks, hard_errors)
    _check_video_metadata(video_metadata, checks, hard_errors)
    _check_segments(clip_plan, video_metadata, checks, hard_errors)
    _check_output_name(clip_plan, checks, hard_errors)
    _check_roi_constraints(clip_plan, roi_settings, checks, hard_errors, warnings)

    if hard_errors:
        status = "failed"
    elif warnings:
        status = "passed_with_warnings"
    else:
        status = "passed"
    return ClipPlanValidationReport(
        status=status,
        hard_errors=hard_errors,
        warnings=warnings,
        checks=checks,
    )


def _check_ffmpeg_available(
    available: bool,
    checks: list[ValidationCheck],
    hard_errors: list[ValidationIssue],
) -> None:
    if available:
        checks.append(ValidationCheck(name="ffmpeg_available", status="passed"))
        return
    issue = ValidationIssue(
        code="ffmpeg_unavailable",
        message="FFmpeg is required for real slicing.",
    )
    hard_errors.append(issue)
    checks.append(
        ValidationCheck(
            name="ffmpeg_available",
            status="failed",
            message=issue.message,
        )
    )


def _check_video_metadata(
    metadata: VideoMetadata,
    checks: list[ValidationCheck],
    hard_errors: list[ValidationIssue],
) -> None:
    if metadata.probe_status == "succeeded" and metadata.duration_sec is not None:
        checks.append(ValidationCheck(name="video_duration_available", status="passed"))
        return
    issue = ValidationIssue(
        code="video_duration_unavailable",
        message="Video duration could not be confirmed before slicing.",
        details={"probe_status": metadata.probe_status, "errors": metadata.errors},
    )
    hard_errors.append(issue)
    checks.append(
        ValidationCheck(
            name="video_duration_available",
            status="failed",
            message=issue.message,
            details=issue.details,
        )
    )


def _check_segments(
    clip_plan: ClipPlan,
    metadata: VideoMetadata,
    checks: list[ValidationCheck],
    hard_errors: list[ValidationIssue],
) -> None:
    if not clip_plan.segments:
        issue = ValidationIssue(
            code="clip_plan_empty",
            message="ClipPlan must contain at least one segment.",
        )
        hard_errors.append(issue)
        checks.append(ValidationCheck(name="clip_plan_segments", status="failed", message=issue.message))
        return

    checks.append(
        ValidationCheck(
            name="clip_plan_segments",
            status="passed",
            details={"count": len(clip_plan.segments)},
        )
    )
    duration = metadata.duration_sec
    if duration is None:
        return

    for segment in clip_plan.segments:
        if segment.end_sec > duration:
            issue = ValidationIssue(
                code="segment_exceeds_video_duration",
                message=f"Segment {segment.segment_id or ''} exceeds source video duration.",
                details={
                    "segment_id": segment.segment_id,
                    "end_sec": segment.end_sec,
                    "video_duration_sec": duration,
                },
            )
            hard_errors.append(issue)
            checks.append(
                ValidationCheck(
                    name="segment_within_video_duration",
                    status="failed",
                    message=issue.message,
                    details=issue.details,
                )
            )
            return
    checks.append(ValidationCheck(name="segment_within_video_duration", status="passed"))


def _check_output_name(
    clip_plan: ClipPlan,
    checks: list[ValidationCheck],
    hard_errors: list[ValidationIssue],
) -> None:
    output_name = clip_plan.output_name
    if not output_name:
        checks.append(ValidationCheck(name="safe_output_name", status="passed"))
        return

    path = PurePath(output_name)
    unsafe = path.is_absolute() or len(path.parts) != 1 or any(part == ".." for part in path.parts)
    if not unsafe:
        checks.append(ValidationCheck(name="safe_output_name", status="passed"))
        return

    issue = ValidationIssue(
        code="unsafe_output_name",
        message="ClipPlan output_name must be a file name, not a path.",
        details={"output_name": output_name},
    )
    hard_errors.append(issue)
    checks.append(
        ValidationCheck(
            name="safe_output_name",
            status="failed",
            message=issue.message,
            details=issue.details,
        )
    )


def _check_roi_constraints(
    clip_plan: ClipPlan,
    roi: ROISettings,
    checks: list[ValidationCheck],
    hard_errors: list[ValidationIssue],
    warnings: list[ValidationIssue],
) -> None:
    clip_count = len(clip_plan.segments)
    if roi.max_clip_count is not None and clip_count > roi.max_clip_count:
        issue = ValidationIssue(
            code="clip_count_exceeds_roi_max",
            message="Clip count exceeds ROI max_clip_count.",
            details={"clip_count": clip_count, "max_clip_count": roi.max_clip_count},
        )
        hard_errors.append(issue)
        checks.append(ValidationCheck(name="roi_max_clip_count", status="failed", message=issue.message))
    else:
        checks.append(ValidationCheck(name="roi_max_clip_count", status="passed"))

    if roi.min_clip_count is not None and clip_count < roi.min_clip_count:
        _add_warning(warnings, checks, "roi_min_clip_count", "clip_count_below_roi_min")
    if roi.target_clip_count is not None and clip_count != roi.target_clip_count:
        _add_warning(warnings, checks, "roi_target_clip_count", "clip_count_differs_from_roi_target")

    for segment in clip_plan.segments:
        duration = segment.end_sec - segment.start_sec
        if roi.max_clip_duration is not None and duration > roi.max_clip_duration:
            if roi.validation_policy == "strict":
                issue = ValidationIssue(
                    code="clip_duration_exceeds_roi_max",
                    message="Clip duration exceeds ROI max_clip_duration.",
                    details={"duration_sec": duration, "max_clip_duration": roi.max_clip_duration},
                )
                hard_errors.append(issue)
                checks.append(ValidationCheck(name="roi_max_duration", status="failed", message=issue.message))
            else:
                _add_warning(warnings, checks, "roi_max_duration", "clip_duration_exceeds_roi_max")
            return
        if roi.min_clip_duration is not None and duration < roi.min_clip_duration:
            _add_warning(warnings, checks, "roi_min_duration", "clip_duration_below_roi_min")
            return
    checks.append(ValidationCheck(name="roi_duration_constraints", status="passed"))


def _add_warning(
    warnings: list[ValidationIssue],
    checks: list[ValidationCheck],
    check_name: str,
    code: str,
) -> None:
    issue = ValidationIssue(code=code, message=f"{check_name} produced an advisory warning.")
    warnings.append(issue)
    checks.append(ValidationCheck(name=check_name, status="warning", message=issue.message))
