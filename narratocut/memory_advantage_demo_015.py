from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from narratocut.memory_advantage_demo_015_content import (
    DEFAULT_DURATION,
    DEFAULT_MODE,
    MAX_KLING_PROMPT_CHARS,
    SCENE_ID,
    build_memory_inputs,
    generation_projections,
    protocol_card,
    scorecard_rubric,
)
from narratocut.model_gateway.company_secrets import CompanyProviderSecrets
from narratocut.model_gateway.kling_plan import build_kling_request_plan
from narratocut.model_gateway.kling_video_smoke import run_kling_i2v_smoke
from narratocut.memory_advantage_demo_015_review import write_demo_015_i2v_review
from narratocut.utils import write_json


DEMO_ID = "AFS-MEMORY-ADVANTAGE-DEMO-015"
DEFAULT_OUTPUT_DIR = Path(
    "data/processed/runs/memory_advantage_demo_015/memory_backed_desert_recovery_i2v/plan"
)
DEFAULT_RUN_ROOT = Path("data/processed/runs/memory_advantage_demo_015/memory_backed_desert_recovery_i2v")
VideoRunner = Callable[..., dict[str, Any]]


def build_demo_015_package(
    store: CompanyProviderSecrets,
    *,
    source_keyframe_ref: str = "demo_012_memory_desert_candidate_001.jpg",
    i2v_service_id: str = "kling_i2v",
    duration: str = DEFAULT_DURATION,
    mode: str = DEFAULT_MODE,
) -> dict[str, Any]:
    memory_inputs = build_memory_inputs()
    projections = generation_projections(memory_inputs)
    requests = [
        _request(
            store,
            projection,
            source_keyframe_ref=source_keyframe_ref,
            i2v_service_id=i2v_service_id,
            duration=duration,
            mode=mode,
        )
        for projection in projections
    ]
    return {
        "schema_version": "memory_advantage_demo_015_package.v1",
        "demo_id": DEMO_ID,
        "theme": {
            "id": "memory_backed_desert_recovery_i2v",
            "title": "Memory-backed production protocol for fixed-keyframe desert I2V",
            "style": "3D anime cinematic character and scene continuity",
            "audience": "competition demo and roadshow proof case",
        },
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "human_acceptance": "not_reviewed",
        "business_validation": "not_validated",
        "quality_improvement_claim": "not_claimed",
        "source_keyframe": {
            "role": "same_existing_keyframe_for_both_lanes",
            "display_ref": source_keyframe_ref,
            "path_persisted": False,
        },
        "protocol_card": protocol_card(),
        "memory_inputs": memory_inputs,
        "generation_projections": projections,
        "video_requests": requests,
        "scorecard_rubric": scorecard_rubric(),
        "claim_boundaries": {
            "structure_verification": "protocol_package_only",
            "provider_smoke": "not_started",
            "creative_quality": "not_reviewed",
            "human_acceptance": "not_reviewed",
            "business_validation": "not_validated",
            "durable_memory_runtime": "not_implemented",
            "quality_improvement_claim": "not_claimed",
        },
    }


def write_demo_015_package(package: dict[str, Any], output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> list[Path]:
    output_root = Path(output_dir)
    paths = [
        write_json(output_root / "protocol_card.json", _wrap(package, "protocol_card")),
        write_json(output_root / "memory_inputs.json", _wrap(package, "memory_inputs")),
        write_json(output_root / "generation_projections.json", _wrap(package, "generation_projections")),
        write_json(output_root / "video_requests.json", {"demo_id": DEMO_ID, "requests": package["video_requests"]}),
        write_json(output_root / "scorecard_rubric.json", _wrap(package, "scorecard_rubric")),
        write_json(
            output_root / "run_plan.json",
            {
                "demo_id": DEMO_ID,
                "provider_calls_started": False,
                "source_keyframe": package["source_keyframe"],
                "protocol_card": package["protocol_card"],
                "claim_boundaries": package["claim_boundaries"],
            },
        ),
    ]
    report_path = output_root / "demo_015_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_demo_015_report(package), encoding="utf-8")
    paths.append(report_path)
    return paths


def run_demo_015_i2v_protocol(
    store: CompanyProviderSecrets,
    run_root: str | Path = DEFAULT_RUN_ROOT,
    *,
    source_keyframe_path: str | Path,
    video_runner: VideoRunner | None = None,
    i2v_service_id: str = "kling_i2v",
    duration: str = DEFAULT_DURATION,
    mode: str = DEFAULT_MODE,
    poll_interval_sec: float = 5.0,
    max_polls: int = 120,
    transport: str = "httpx",
) -> dict[str, Any]:
    source_path = Path(source_keyframe_path)
    if not source_path.is_file():
        raise FileNotFoundError(f"DEMO-015 source keyframe not found: {source_path}")
    root = Path(run_root)
    package = build_demo_015_package(
        store,
        source_keyframe_ref=source_path.name,
        i2v_service_id=i2v_service_id,
        duration=duration,
        mode=mode,
    )
    runner = video_runner or run_kling_i2v_smoke
    for request in package["video_requests"]:
        output_dir = root / "live" / str(request["lane"]) / SCENE_ID / "i2v"
        runner(
            store,
            service_id=i2v_service_id,
            prompt=str(request["video_prompt"]),
            image_path=source_path,
            output_dir=output_dir,
            duration=duration,
            mode=mode,
            poll_interval_sec=poll_interval_sec,
            max_polls=max_polls,
            transport=transport,
        )
    review_path, html_path = write_demo_015_i2v_review(package, root, source_path)
    summary = {
        "schema_version": "memory_advantage_demo_015_i2v_runtime_summary.v1",
        "demo_id": DEMO_ID,
        "status": "memory_backed_production_i2v_provider_smoke_succeeded",
        "provider_calls_started": True,
        "writes_long_term_memory": False,
        "generated_video_count": len(package["video_requests"]),
        "review_path": _display_ref(root, review_path),
        "html_path": _display_ref(root, html_path),
        "claim_boundary": "provider_runtime_only_not_creative_quality_or_business_validation",
    }
    write_json(root / "i2v_runtime_summary.json", summary)
    return summary


def render_demo_015_report(package: dict[str, Any]) -> str:
    request_lines = "\n".join(
        f"- {item['lane']}: {item['production_mode']} ({item['duration']}s {item['mode']})"
        for item in package["video_requests"]
    )
    return "\n".join(
        [
            f"# {DEMO_ID}",
            "",
            "## Boundary",
            "",
            "- Provider calls started: false",
            "- Source keyframe: same existing keyframe for both lanes",
            "- User task: same short task for both lanes",
            "- Baseline: stateless generation",
            "- Memory-backed: automatic asset, scene, and feedback memory reuse",
            "- Durable Memory runtime: not implemented",
            "- Human acceptance: not reviewed",
            "- Business validation: not validated",
            "- Do not present this as a prompt-length test.",
            "",
            "## Video Requests",
            "",
            request_lines,
            "",
        ]
    )


def _request(
    store: CompanyProviderSecrets,
    projection: dict[str, Any],
    *,
    source_keyframe_ref: str,
    i2v_service_id: str,
    duration: str,
    mode: str,
) -> dict[str, Any]:
    prompt = str(projection["video_prompt"])
    if len(prompt) > MAX_KLING_PROMPT_CHARS:
        raise ValueError(f"DEMO-015 prompt too long for lane {projection['lane']}: {len(prompt)}")
    plan = build_kling_request_plan(
        store,
        service_id=i2v_service_id,
        prompt=prompt,
        image_ref=source_keyframe_ref,
        duration=duration,
        mode=mode,
        require_live_gate=False,
    )
    return {
        "request_id": f"{projection['lane']}_{SCENE_ID}",
        "lane": projection["lane"],
        "scene_id": SCENE_ID,
        "production_mode": projection["production_mode"],
        "user_task": projection["user_task"],
        "memory_sources_loaded": projection["memory_sources_loaded"],
        "source_keyframe_role": "same_existing_keyframe_for_both_lanes",
        "duration": duration,
        "mode": mode,
        "video_prompt": prompt,
        "provider_plan": _provider_plan_summary(plan),
    }


def _provider_plan_summary(plan: dict[str, Any]) -> dict[str, Any]:
    request_json = plan["create_request"]["json"]
    return {
        "service_id": plan["service_id"],
        "provider": plan["provider"],
        "api_family": plan["api_family"],
        "capability": plan["capability"],
        "required_gate": plan["required_gate"],
        "gate_status": plan["gate_status"],
        "live_call_authorized": plan["live_call_authorized"],
        "model_name": request_json.get("model_name"),
        "source_image": "same_existing_keyframe_ref",
        "claim_boundary": plan["claim_boundary"],
    }


def _wrap(package: dict[str, Any], key: str) -> dict[str, Any]:
    return {"demo_id": DEMO_ID, key: package[key]}


def _display_ref(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()
