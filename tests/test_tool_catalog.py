from __future__ import annotations

from pathlib import Path

import yaml


CATALOG_PATH = Path("configs/tool_catalog.yaml")
DOCS_PATH = Path("docs/tool_contracts.md")
EXPECTED_TOOLS = {
    "analyze_hooks",
    "generate_scripts",
    "generate_clip_plans",
    "mock_slice",
    "build_ffmpeg_command_contract",
    "slice_real",
    "probe_video_metadata",
    "validate_clip_plan",
    "real_slice_video",
    "load_real_slice_manifest",
    "generate_assembly_plan",
    "concat_clips",
    "probe_final_video",
    "load_video",
    "extract_audio",
    "transcribe_audio_mock",
    "transcribe_audio_openai_compatible",
    "write_transcript",
    "write_subtitles",
    "inspect_run",
}
FORBIDDEN_TOOLS = {
    "autonomous_agent",
    "list_skills",
    "skill_registry",
}


def _load_catalog() -> dict:
    return yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))


def test_tool_catalog_declares_current_static_tools() -> None:
    catalog = _load_catalog()

    assert catalog["project"] == "NarratoCut"
    assert catalog["version"] == 1
    assert catalog["catalog_kind"] == "static_tool_contracts"
    assert {tool["name"] for tool in catalog["tools"]} == EXPECTED_TOOLS


def test_tool_catalog_tools_have_required_contract_fields() -> None:
    catalog = _load_catalog()

    for tool in catalog["tools"]:
        assert tool["description"]
        assert tool["category"]
        assert isinstance(tool["input_artifacts"], list)
        assert isinstance(tool["output_artifacts"], list)
        assert isinstance(tool["failure_modes"], list)
        assert isinstance(tool["quality_checks"], list)
        assert set(tool["requires"]) == {"ffmpeg", "network", "model_provider", "api_key"}
        assert set(tool["agent_usage"]) == {
            "safe_for_auto_execute",
            "requires_human_review",
            "mutates_workflow",
            "executes_external_process",
        }


def test_tool_catalog_keeps_phase_7_5b_safety_boundary() -> None:
    catalog = _load_catalog()
    names = {tool["name"] for tool in catalog["tools"]}

    assert names.isdisjoint(FORBIDDEN_TOOLS)
    for tool in catalog["tools"]:
        if tool["name"] == "transcribe_audio_openai_compatible":
            continue
        assert tool["requires"]["network"] is False
        assert tool["requires"]["api_key"] is False
        assert tool["agent_usage"]["mutates_workflow"] is False

    ffmpeg_contract = next(
        tool for tool in catalog["tools"] if tool["name"] == "build_ffmpeg_command_contract"
    )
    assert ffmpeg_contract["requires"]["ffmpeg"] is False
    assert ffmpeg_contract["agent_usage"]["executes_external_process"] is False

    slice_real = next(tool for tool in catalog["tools"] if tool["name"] == "slice_real")
    assert slice_real["requires"]["ffmpeg"] is True
    assert slice_real["agent_usage"]["safe_for_auto_execute"] is False
    assert slice_real["agent_usage"]["requires_human_review"] is True
    assert slice_real["agent_usage"]["executes_external_process"] is True


def test_tool_contract_docs_cover_catalog_tools() -> None:
    catalog = _load_catalog()
    docs = DOCS_PATH.read_text(encoding="utf-8")

    assert "Phase 7.5B" in docs
    assert "no runtime registry" in docs
    for tool in catalog["tools"]:
        assert f"### `{tool['name']}`" in docs
