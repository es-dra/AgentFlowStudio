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


def test_llm_enhancement_keeps_runtime_helpers_split() -> None:
    route_path = API_ROOT / "runtime_llm_enhancement.py"
    helper_names = [
        "runtime_llm_enhancement_constants.py",
        "runtime_llm_enhancement_gate.py",
        "runtime_llm_enhancement_safety.py",
        "runtime_llm_enhancement_instructions.py",
        "runtime_llm_enhancement_fallback.py",
        "runtime_llm_enhancement_dispatch.py",
    ]

    route_source = route_path.read_text(encoding="utf-8")
    sources = {}
    for name in helper_names:
        path = API_ROOT / name
        assert path.is_file(), f"missing split LLM enhancement helper module: {name}"
        sources[name] = path.read_text(encoding="utf-8")

    assert "def maybe_enhance_prompt_with_llm" in route_source
    for helper in (
        "_enhancement_instruction",
        "_visual_enhancement_instruction",
        "_strict_format_retry_instruction",
        "_salvage_prompt_from_llm_article",
        "_dispatch_llm_with_fallback",
        "_provider_candidates",
        "_normalize_enhancement_sections",
        "_parse_section_line",
    ):
        assert f"def {helper}" not in route_source

    assert "def llm_provider_gate" in sources["runtime_llm_enhancement_gate.py"]
    assert "def provider_text_requested" in sources["runtime_llm_enhancement_gate.py"]
    assert "def sanitize_enhanced_prompt" in sources["runtime_llm_enhancement_safety.py"]
    assert "def sections_from_canonical" in sources["runtime_llm_enhancement_safety.py"]
    assert "def enhancement_instruction" in sources["runtime_llm_enhancement_instructions.py"]
    assert "def strict_format_retry_instruction" in sources["runtime_llm_enhancement_instructions.py"]
    assert "def deterministic_chinese_fallback_prompt" in sources["runtime_llm_enhancement_fallback.py"]
    assert "def salvage_prompt_from_llm_article" in sources["runtime_llm_enhancement_fallback.py"]
    assert "def dispatch_llm_with_fallback" in sources["runtime_llm_enhancement_dispatch.py"]

    _assert_source_size_matches_maintenance_policy("apps/api/runtime_llm_enhancement.py", route_source)
    for name, source in sources.items():
        assert "\ufffd" not in source
        _assert_source_size_matches_maintenance_policy(f"apps/api/{name}", source)

    constants = sources["runtime_llm_enhancement_constants.py"]
    for label in ("意图", "角色/主体", "场景/美术", "连续性", "负面约束"):
        assert label in constants

    for name in ("runtime_llm_enhancement_instructions.py", "runtime_llm_enhancement_fallback.py"):
        assert "原始提示词" in sources[name] or "意图" in sources[name]
