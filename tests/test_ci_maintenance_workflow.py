from __future__ import annotations

from pathlib import Path


WORKFLOW_PATH = Path(".github/workflows/maintenance.yml")


def test_github_maintenance_workflow_exists_with_required_gates() -> None:
    source = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert 'python-version: "3.12"' in source
    assert 'python -m pip install -e ".[dev]"' in source
    assert "python -m apps.cli.main --help" in source
    assert "python -m apps.cli.main version" in source
    assert "python tools/maintenance_audit.py" in source
    assert "python -m pytest" in source
    assert "git diff --check" in source


def test_github_maintenance_workflow_does_not_enable_live_providers() -> None:
    source = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "AFS_ALLOW_REMOTE_LLM: true" not in source
    assert "AFS_ALLOW_REMOTE_ASR: true" not in source
    assert "AFS_ALLOW_REMOTE_IMAGE: true" not in source
    assert "AFS_ALLOW_REMOTE_VIDEO: true" not in source
