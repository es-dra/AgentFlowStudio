from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow_studio.memory_advantage_demo_012_content import (
    ASPECT_RATIO,
    MODEL_NAME,
    build_asset_and_card,
    demo_012_evaluation_rubric,
    demo_012_experiment_card,
    demo_012_image_budget,
    demo_012_image_requests,
    demo_012_scenes,
)
from agentflow_studio.memory_advantage_demo_012_review import ImageRunner, run_i2i_keyframes
from agentflow_studio.memory_advantage_demo_012_review import VideoRunner, run_i2v_storyboards
from agentflow_studio.model_gateway.company_secrets import CompanyProviderSecrets
from agentflow_studio.model_gateway.minimax_image_smoke import build_minimax_image_request_plan
from agentflow_studio.utils import write_json


DEMO_ID = "AFS-MEMORY-ADVANTAGE-DEMO-012"
DEFAULT_OUTPUT_DIR = Path("data/processed/runs/memory_advantage_demo_012/asset_i2i_i2v_consistency/plan")
DEFAULT_RUN_ROOT = Path("data/processed/runs/memory_advantage_demo_012/asset_i2i_i2v_consistency")


def build_demo_012_package(
    store: CompanyProviderSecrets,
    *,
    subject_reference_image_ref: str,
    image_service_id: str = "minimax_image",
    i2v_service_id: str = "kling_i2v",
) -> dict[str, Any]:
    asset, card = build_asset_and_card()
    scenes = demo_012_scenes()

    def provider_plan_builder(*, prompt: str, seed: int) -> dict[str, Any]:
        plan = build_minimax_image_request_plan(
            store,
            service_id=image_service_id,
            prompt=prompt,
            aspect_ratio=ASPECT_RATIO,
            candidate_count=1,
            model_name_override=MODEL_NAME,
            subject_reference_image_ref=subject_reference_image_ref,
        )
        plan["create_request"]["json"]["seed"] = seed
        plan["create_request"]["json"]["prompt_optimizer"] = False
        return _provider_plan_summary(plan)

    image_requests = demo_012_image_requests(scenes, card, provider_plan_builder)
    return {
        "schema_version": "memory_advantage_demo_012_package.v1",
        "demo_id": DEMO_ID,
        "theme": {
            "id": "asset_driven_i2i_i2v_consistency",
            "title": "Fixed character reference I2I keyframe and I2V consistency demo",
            "style": "3D anime cinematic character consistency",
            "audience": "competition demo and roadshow proof case",
        },
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "quality_improvement_claim": "not_claimed",
        "human_acceptance": "asset_reference_provided_by_user_only",
        "business_validation": "not_validated",
        "accepted_character_asset": asset,
        "visual_memory_asset_card": card,
        "scene_stress_tests": scenes,
        "image_budget": demo_012_image_budget(),
        "image_requests": image_requests,
        "provider_route": {
            "primary_route": "fixed_asset_reference_to_i2i_keyframes_then_i2v",
            "image_service_id": image_service_id,
            "i2v_service_id": i2v_service_id,
            "image_model": MODEL_NAME,
            "aspect_ratio": ASPECT_RATIO,
            "duration_sec": 5,
            "runtime_scope": "six_i2i_keyframes_first_then_selective_i2v",
        },
        "evaluation_rubric": demo_012_evaluation_rubric(),
        "experiment_card": demo_012_experiment_card(),
        "claim_boundaries": {
            "structure_verification": "this_package_only",
            "provider_smoke": "not_started",
            "creative_quality": "not_reviewed",
            "human_acceptance": "asset_reference_only_not_scene_acceptance",
            "business_validation": "not_validated",
            "durable_memory_runtime": "not_implemented",
            "quality_improvement_claim": "not_claimed",
        },
    }


def write_demo_012_package(package: dict[str, Any], output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> list[Path]:
    output_root = Path(output_dir)
    paths = [
        write_json(output_root / "accepted_character_asset.json", _wrap(package, "accepted_character_asset")),
        write_json(output_root / "visual_memory_asset_card.json", _wrap(package, "visual_memory_asset_card")),
        write_json(output_root / "scene_stress_tests.json", _wrap(package, "scene_stress_tests")),
        write_json(output_root / "image_requests.json", {"demo_id": DEMO_ID, "requests": package["image_requests"]}),
        write_json(output_root / "evaluation_rubric.json", _wrap(package, "evaluation_rubric")),
        write_json(
            output_root / "run_plan.json",
            {
                "demo_id": DEMO_ID,
                "provider_calls_started": False,
                "image_budget": package["image_budget"],
                "provider_route": package["provider_route"],
                "experiment_card": package["experiment_card"],
                "claim_boundaries": package["claim_boundaries"],
            },
        ),
    ]
    report_path = output_root / "demo_012_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_demo_012_report(package), encoding="utf-8")
    paths.append(report_path)
    return paths


def run_demo_012_i2i_keyframes(
    store: CompanyProviderSecrets,
    run_root: str | Path = DEFAULT_RUN_ROOT,
    *,
    subject_reference_image_path: str | Path,
    image_runner: ImageRunner | None = None,
    image_service_id: str = "minimax_image",
) -> dict[str, Any]:
    reference_path = Path(subject_reference_image_path)
    package = build_demo_012_package(
        store,
        subject_reference_image_ref=reference_path.name,
        image_service_id=image_service_id,
    )
    kwargs: dict[str, Any] = {}
    if image_runner is not None:
        kwargs["image_runner"] = image_runner
    return run_i2i_keyframes(
        store,
        package,
        run_root,
        subject_reference_image_path=reference_path,
        image_service_id=image_service_id,
        **kwargs,
    )


def run_demo_012_i2v_storyboards(
    store: CompanyProviderSecrets,
    run_root: str | Path = DEFAULT_RUN_ROOT,
    *,
    video_runner: VideoRunner | None = None,
    i2v_service_id: str = "kling_i2v",
    duration: str = "5",
    mode: str = "pro",
    poll_interval_sec: float = 5.0,
    max_polls: int = 120,
    transport: str = "httpx",
) -> dict[str, Any]:
    package = build_demo_012_package(
        store,
        subject_reference_image_ref="existing_i2i_keyframes",
        i2v_service_id=i2v_service_id,
    )
    kwargs: dict[str, Any] = {}
    if video_runner is not None:
        kwargs["video_runner"] = video_runner
    return run_i2v_storyboards(
        store,
        package,
        run_root,
        i2v_service_id=i2v_service_id,
        duration=duration,
        mode=mode,
        poll_interval_sec=poll_interval_sec,
        max_polls=max_polls,
        transport=transport,
        **kwargs,
    )


def render_demo_012_report(package: dict[str, Any]) -> str:
    scenes = "\n".join(
        f"- {scene['scene_id']}: {scene['stressor']} ({scene['duration_sec']} seconds)"
        for scene in package["scene_stress_tests"]
    )
    criteria = "\n".join(
        f"- {item['id']}: {item['question']}" for item in package["evaluation_rubric"]["criteria"]
    )
    return "\n".join(
        [
            f"# {DEMO_ID}",
            "",
            "## Boundary",
            "",
            "- Provider calls started: false",
            "- Scope: 3 scenes x 2 lanes = 6 keyframes",
            "- writes durable Memory runtime: not implemented",
            "- human acceptance: asset reference only, scene outputs not reviewed",
            "- business validation: not validated",
            "- Do not claim memory advantage before side-by-side scene review.",
            "",
            "## Comparison",
            "",
            "- baseline: same fixed reference image plus normal professional prompt",
            "- memory_assisted: same fixed reference image plus Visual Memory Asset Card Yiqi v1",
            "- fairness: same provider, same model, same aspect ratio, same seed per scene",
            "",
            "## Scene Stress Tests",
            "",
            scenes,
            "",
            "## Review Rubric",
            "",
            criteria,
            "",
        ]
    )


def _provider_plan_summary(plan: dict[str, Any]) -> dict[str, Any]:
    request_json = plan["create_request"]["json"]
    summary = {
        "service_id": plan["service_id"],
        "provider": plan["provider"],
        "api_family": plan["api_family"],
        "capability": plan["capability"],
        "required_gate": plan["required_gate"],
        "gate_status": plan["gate_status"],
        "live_call_authorized": plan["live_call_authorized"],
        "model_name": request_json.get("model_name") or request_json.get("model"),
        "subject_reference": plan.get("subject_reference"),
        "claim_boundary": plan["claim_boundary"],
    }
    return summary


def _wrap(package: dict[str, Any], key: str) -> dict[str, Any]:
    return {"demo_id": DEMO_ID, key: package[key]}
