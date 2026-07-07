from __future__ import annotations

from pathlib import Path


API_ROOT = Path("apps/api")


def test_llm_enhancement_keeps_runtime_helpers_split() -> None:
    route_path = API_ROOT / "runtime_llm_enhancement.py"
    helper_names = [
        "runtime_llm_enhancement_constants.py",
        "runtime_llm_enhancement_gate.py",
        "runtime_llm_enhancement_safety.py",
        "runtime_llm_enhancement_instructions.py",
        "runtime_llm_enhancement_fallback.py",
        "runtime_llm_enhancement_salvage.py",
        "runtime_llm_enhancement_dispatch.py",
        "runtime_originalize_prompt_templates.py",
        "runtime_reference_intent.py",
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
    assert "def salvage_prompt_from_llm_article" in sources["runtime_llm_enhancement_salvage.py"]
    assert "def dispatch_llm_with_fallback" in sources["runtime_llm_enhancement_dispatch.py"]
    assert "def deterministic_originalize_i2i_fallback_prompt" in sources["runtime_originalize_prompt_templates.py"]
    assert "def reference_transform_mode_for_request" in sources["runtime_reference_intent.py"]

    assert len(route_source.splitlines()) <= 300
    for name, source in sources.items():
        assert "\ufffd" not in source
        assert len(source.splitlines()) <= 300, f"{name} exceeded the maintenance line threshold"

    constants = sources["runtime_llm_enhancement_constants.py"]
    for label in ("意图", "角色/主体", "场景/美术", "连续性", "负面约束"):
        assert label in constants

    for name in ("runtime_llm_enhancement_instructions.py", "runtime_llm_enhancement_fallback.py"):
        assert "原始提示词" in sources[name] or "意图" in sources[name]


def test_originalize_reference_mode_changes_llm_instruction_and_fallback() -> None:
    from apps.api.runtime_llm_enhancement_fallback import deterministic_chinese_fallback_prompt
    from apps.api.runtime_llm_enhancement_instructions import enhancement_instruction
    from apps.api.runtime_models import PromptOptimizationRequest

    request = PromptOptimizationRequest(
        node_id="asset_ref_originalize",
        node_type="image",
        prompt_text="根据参考图原创重生一个适合项目使用的角色资产",
        generation_target="keyframe",
        target_platform="short_video",
        style="cinematic",
        asset_refs=["img_ref_001"],
        node_parameters={
            "reference_transform_mode": "originalize_ip_safe",
            "uploaded_images": [{"asset_id": "img_ref_001", "filename": "famous-warrior.png"}],
        },
        generated_at="2026-07-07T10:00:00+08:00",
    )

    instruction = enhancement_instruction(request, {})
    fallback = deterministic_chinese_fallback_prompt(request, {"selected_slots": {}})

    assert "原创重生 / 降 IP 风险" in instruction
    assert "不能写成保守局部修图" in instruction
    assert "参考图只作为灵感证据" in fallback
    assert "不要复制已知角色" in fallback
