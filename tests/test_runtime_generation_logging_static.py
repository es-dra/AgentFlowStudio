from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_keyframe_generation_logs_route_and_provider_timing() -> None:
    routes = _read("apps/api/runtime_keyframe_routes.py")
    generation = _read("apps/api/runtime_keyframes.py")
    polling = _read("apps/api/runtime_keyframe_async.py")

    assert "keyframe_generation_submit_started" in routes
    assert "keyframe_generation_poll_completed" in routes
    assert '"provider_call"' in generation
    assert '"submitted"' in generation
    assert '"succeeded"' in generation
    assert "provider_elapsed_ms" in generation
    assert "elapsed_ms" in generation
    assert '"poll_provider_call"' in polling
    assert "poll_running" in polling
    assert "poll_succeeded" in polling
    assert "provider_elapsed_ms" in polling


def test_video_generation_logs_route_and_provider_timing() -> None:
    routes = _read("apps/api/runtime_video_routes.py")
    dispatch = _read("apps/api/runtime_video_dispatch.py")

    assert "video_generation_submit_started" in routes
    assert "video_generation_poll_completed" in routes
    assert "elapsed_ms=_elapsed_ms(started)" in routes
    assert '"provider_prompt_built"' in dispatch
    assert "provider_prompt_sha256" in dispatch
    assert "provider_prompt_risk_terms" in dispatch
    assert '"provider_call"' in dispatch
    assert "provider_started = time.perf_counter()" in dispatch
    assert "provider_elapsed_ms = _elapsed_ms(provider_started)" in dispatch
    assert "provider_elapsed_ms=provider_elapsed_ms" in dispatch
    assert "poll_elapsed_ms" in dispatch


def test_prompt_optimization_logs_each_major_step() -> None:
    routes = _read("apps/api/runtime_prompt_memory_routes.py")
    builder = _read("apps/api/runtime_prompt_memory.py")
    llm = _read("apps/api/runtime_llm_enhancement.py")

    for marker in [
        "build_start",
        "state_loaded",
        "context_assembled",
        "context_bundle_resolved",
        "llm_enhancement_done",
        "background_context_extracted",
        "prompt_finalized",
        "script_plan_built",
        "payloads_built",
        "payloads_validated",
        "memory_state_written",
        "artifacts_written",
        "build_complete",
    ]:
        assert marker in builder

    for marker in [
        "llm_decision",
        "provider_call_start",
        "provider_call_done",
        "response_validate_start",
        "response_validate_done",
        "specificity_validate_start",
        "llm_applied",
    ]:
        assert marker in llm

    for marker in [
        "artifact_collection_start",
        "artifact_collection_done",
        "trace_write_start",
        "trace_write_done",
        "trace_register_start",
        "trace_register_done",
        "job_write_start",
        "job_write_done",
    ]:
        assert marker in routes
