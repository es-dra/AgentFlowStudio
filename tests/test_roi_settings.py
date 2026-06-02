from __future__ import annotations

import pytest

from agentflow_studio.schemas import ROISettings


def test_roi_settings_defaults_to_advisory_validation() -> None:
    settings = ROISettings(
        target_platform="douyin",
        target_audience="college students",
        content_goal="increase_completion_rate",
        min_clip_duration=8,
        max_clip_duration=30,
        target_clip_count=3,
        min_clip_count=1,
        max_clip_count=5,
        risk_tolerance="low",
        priority=["hook_strength", "clarity"],
    )

    assert settings.validation_policy == "advisory"
    assert settings.target_clip_count == 3


def test_roi_settings_rejects_invalid_ranges() -> None:
    with pytest.raises(ValueError, match="max_clip_duration"):
        ROISettings(
            target_platform="douyin",
            target_audience="students",
            content_goal="completion",
            min_clip_duration=30,
            max_clip_duration=8,
        )

    with pytest.raises(ValueError, match="max_clip_count"):
        ROISettings(
            target_platform="douyin",
            target_audience="students",
            content_goal="completion",
            min_clip_count=5,
            max_clip_count=1,
        )
