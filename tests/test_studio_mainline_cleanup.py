from __future__ import annotations

from pathlib import Path


def test_runtime_and_studio_do_not_add_new_legacy_memory_imports() -> None:
    offenders = []
    for root in (Path("apps/api"), Path("apps/studio")):
        for path in root.rglob("*"):
            if path.suffix not in {".py", ".js"}:
                continue
            if "agentflow.memory" in path.read_text(encoding="utf-8"):
                offenders.append(path.as_posix())

    assert offenders == []


def test_only_tracked_sop_cleanup_target_was_compliance_stub() -> None:
    tracked_sop_roots = [
        Path("agentflow_studio/assembly_sop"),
        Path("agentflow_studio/bgm_sop"),
        Path("agentflow_studio/cover_sop"),
        Path("agentflow_studio/package_sop"),
        Path("agentflow_studio/subtitle_sop"),
        Path("agentflow_studio/subtitle_burn_sop"),
    ]

    for root in tracked_sop_roots:
        tracked_files = [path for path in root.rglob("*") if path.is_file() and "__pycache__" not in path.parts]
        assert tracked_files == []
