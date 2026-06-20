from __future__ import annotations

from apps.api.runtime_jobs import job_progress


def test_running_job_progress_is_indeterminate_not_fake_halfway() -> None:
    progress = job_progress("keyframe_generation", "running")

    assert progress["mode"] == "indeterminate"
    assert progress["percent"] is None
    assert progress["terminal"] is False


def test_terminal_job_progress_remains_complete() -> None:
    progress = job_progress("keyframe_generation", "succeeded")

    assert "mode" not in progress
    assert progress["percent"] == 100
    assert progress["terminal"] is True
