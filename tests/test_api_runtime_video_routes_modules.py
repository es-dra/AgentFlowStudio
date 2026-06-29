from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from tools.maintenance_audit import build_maintenance_audit


REPO_ROOT = Path(".").resolve()
API_ROOT = REPO_ROOT / "apps/api"


@lru_cache(maxsize=1)
def _oversized_findings() -> dict[str, dict]:
    report = build_maintenance_audit(REPO_ROOT)
    checks = {check["check_id"]: check for check in report["checks"]}
    oversized = checks["oversized_files"]
    assert oversized["status"] == "warning"
    return {finding["path"]: finding for finding in oversized["findings"]}


def _assert_source_size_matches_maintenance_policy(relative_path: str, source: str) -> None:
    line_count = len(source.splitlines())
    if line_count <= 300:
        return

    findings = _oversized_findings()
    assert relative_path in findings
    assert findings[relative_path]["detail"].startswith(f"{line_count} lines")


def test_video_routes_keep_runtime_helpers_split() -> None:
    route_path = API_ROOT / "runtime_video_routes.py"
    helper_names = [
        "runtime_video_constants.py",
        "runtime_video_gate.py",
        "runtime_video_candidates.py",
        "runtime_video_manifest.py",
        "runtime_video_task_state.py",
        "runtime_video_prompt.py",
        "runtime_video_dispatch.py",
    ]

    route_source = route_path.read_text(encoding="utf-8")
    sources = {}
    for name in helper_names:
        path = API_ROOT / name
        assert path.is_file(), f"missing split video helper module: {name}"
        sources[name] = path.read_text(encoding="utf-8")

    assert "def register_runtime_video_routes" in route_source
    for helper in (
        "_submit_video_generation",
        "_poll_video_generation",
        "_safe_manifest",
        "_safe_outputs",
        "_provider_task_for_state",
        "_daily_submit_count",
    ):
        assert f"def {helper}" not in route_source

    assert "submit_video_generation" in route_source
    assert "poll_video_generation" in route_source
    assert "def submit_video_generation" in sources["runtime_video_dispatch.py"]
    assert "def poll_video_generation" in sources["runtime_video_dispatch.py"]
    assert "def safe_manifest" in sources["runtime_video_manifest.py"]
    assert "def safe_outputs" in sources["runtime_video_candidates.py"]
    assert "def provider_task_for_state" in sources["runtime_video_task_state.py"]
    assert "def video_gate" in sources["runtime_video_gate.py"]
    assert "def video_provider_prompt" in sources["runtime_video_prompt.py"]

    _assert_source_size_matches_maintenance_policy("apps/api/runtime_video_routes.py", route_source)
    for name, source in sources.items():
        _assert_source_size_matches_maintenance_policy(f"apps/api/{name}", source)
