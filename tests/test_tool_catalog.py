from __future__ import annotations

from pathlib import Path

import yaml

from agentflow_studio.workflow_engine.tool_catalog import load_tool_catalog_contract


CATALOG_PATH = Path("configs/tool_catalog.yaml")
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
    "analyze_audio_boundary_signals",
    "transcribe_audio_mock",
    "transcribe_audio_openai_compatible",
    "transcribe_audio_faster_whisper",
    "write_transcript",
    "build_ocr_transcript",
    "write_ocr_transcript",
    "generate_candidate_windows",
    "score_candidate_windows",
    "write_highlight_score_report",
    "write_selection_diagnostics",
    "write_subtitles",
    "burn_subtitles",
    "probe_subtitle_burn",
    "export_cover",
    "mix_bgm",
    "probe_bgm_mix",
    "write_finished_package",
    "write_package_report",
    "delivery_readiness",
    "inspect_run",
}
FORBIDDEN_TOOLS = {
    "autonomous_agent",
    "list_skills",
    "skill_registry",
}


def _load_catalog() -> dict:
    return load_tool_catalog_contract(CATALOG_PATH)


def test_tool_catalog_uses_split_index_contract() -> None:
    index = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))

    assert index["catalog_kind"] == "static_tool_contracts"
    assert "tool_catalog_parts" in index
    assert "tools" not in index
    for relative_part in index["tool_catalog_parts"]:
        assert (CATALOG_PATH.parent / relative_part).is_file()


def test_tool_catalog_declares_current_static_tools() -> None:
    catalog = _load_catalog()

    assert catalog["project"] == "AgentFlow Studio"
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


def test_tool_contract_docs_point_to_split_catalog_as_source_of_truth() -> None:
    docs = Path("docs/tool_contracts.md").read_text(encoding="utf-8")

    assert "configs/tool_catalog.yaml" in docs
    assert "configs/tool_catalog/*.yaml" in docs
    assert "不再逐项复制工具条目" in docs
