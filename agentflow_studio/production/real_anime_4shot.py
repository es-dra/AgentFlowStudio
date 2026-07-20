from __future__ import annotations

from pathlib import Path
from typing import Literal

from agentflow_studio.production.adaptive_canvas_v2 import (
    AdaptiveProductionProfile,
    AdaptiveRunOptions,
    AdaptiveShotSpec,
    run_adaptive_canvas_production,
)


PROJECT_TYPE = "real_anime_4shot_paid_v1"


def real_anime_4shot_paid_profile() -> AdaptiveProductionProfile:
    """The paid test profile. The adaptive executor itself is not four-shot specific."""
    return AdaptiveProductionProfile(
        project_type=PROJECT_TYPE,
        llm_service_id="disabled_agent_authored",
        script_candidate_id="agent-authored-script-v1",
        script_contract_id=None,
        script_source_type="agent_authored_test_input",
        script_decision_source="OWNER_DECISION_A_AGENT_AUTHORED_SCRIPT_RELEASED",
        title="Lantern Seed at Dawn",
        logline=(
            "A young rooftop gardener and her fox-spirit companion must carry the city's last lantern seed "
            "across the adjacent observatory bridge before a dawn storm extinguishes it."
        ),
        style_bible="clean anime drama, crisp linework, expressive faces, cinematic vertical framing, consistent wardrobe",
        characters=(
            {
                "character_id": "aoi",
                "name": "Aoi",
                "continuity": "short black hair, red scarf, cream field jacket, teal seed satchel, determined expression",
                "role": "core lantern gardener",
            },
            {
                "character_id": "nori",
                "name": "Nori",
                "continuity": "small white fox spirit, cyan tail ribbon, amber eyes, soft blue glow",
                "role": "companion and path guide",
            },
        ),
        scenes=(
            {
                "scene_id": "rooftop-lantern-garden",
                "name": "rooftop lantern garden",
                "visual_mood": "indigo night, warm paper lanterns, wet leaves, distant neon skyline",
                "story_function": "establish the last seed, the goal, and the storm obstacle",
            },
            {
                "scene_id": "dawn-observatory-bridge",
                "name": "dawn observatory bridge",
                "visual_mood": "windy glass bridge, pale gold horizon, white stone seed beacon",
                "story_function": "stage the reversal and emotional resolution beside the garden",
            },
        ),
        shots=(
            AdaptiveShotSpec(
                shot_id="shot-001",
                summary="Aoi lifts the city's last lantern seed while Nori reveals the observatory beacon across the roof.",
                location="rooftop lantern garden",
                characters=("Aoi", "Nori"),
                action="Aoi secures the glowing seed in her teal satchel as Nori points its luminous tail toward the beacon.",
                camera="slow push-in from swaying lanterns to Aoi, Nori, and the seed glow",
                duration_sec=15.0,
                generation_strategy="image_to_video",
                strategy_reason="the recurring gardener, fox spirit, seed, and rooftop palette need one shared identity anchor",
                continuity_in="night garden before the storm, Aoi and Nori together beside the seed cradle",
                continuity_out="Aoi runs toward the adjacent bridge with Nori at her heel and the seed glowing in her satchel",
            ),
            AdaptiveShotSpec(
                shot_id="shot-002",
                summary="The dawn storm tears loose the garden bridge panels and the lantern seed begins to dim.",
                location="rooftop lantern garden",
                characters=("Aoi", "Nori"),
                action="Aoi shields the satchel from rain while a broken bridge panel blocks the only direct path.",
                camera="tracking side shot that ends on the dark gap between garden and observatory",
                duration_sec=15.0,
                generation_strategy="image_to_video",
                strategy_reason="the obstacle shot must preserve Aoi's wardrobe, Nori's glow, and the same seed state",
                continuity_in="Aoi and Nori arrive at the bridge edge with the seed still bright",
                continuity_out="Nori leaps into the storm and lights a chain of floating lantern petals across the gap",
            ),
            AdaptiveShotSpec(
                shot_id="shot-003",
                summary="Nori's lantern-petal path lets Aoi cross the broken span and relight the failing seed.",
                location="dawn observatory bridge",
                characters=("Aoi", "Nori"),
                action="Aoi bounds across the glowing petals, catches Nori, and raises the seed into the first sunrise ray.",
                camera="low tracking angle across the gap, rising with Aoi into the gold horizon",
                duration_sec=15.0,
                generation_strategy="image_to_video",
                strategy_reason="the action reversal needs stable faces, companion scale, seed glow, and cross-shot motion anchors",
                continuity_in="Nori's floating lantern petals continue directly from the broken garden bridge",
                continuity_out="Aoi reaches the observatory beacon holding Nori and a brightly relit seed",
            ),
            AdaptiveShotSpec(
                shot_id="shot-004",
                summary="Aoi plants the lantern seed at the observatory and the rooftop garden wakes in sunrise light.",
                location="dawn observatory bridge",
                characters=("Aoi", "Nori"),
                action="Aoi places the seed into the white stone beacon; lanterns bloom behind them as Nori rests against her shoulder.",
                camera="wide reveal from Aoi's hands at the beacon to the restored garden and sunrise skyline",
                duration_sec=15.0,
                generation_strategy="image_to_video",
                strategy_reason="the emotional close must preserve Aoi, Nori, the seed, and the adjacent garden established earlier",
                continuity_in="the relit seed arrives in Aoi's hands with Nori safe beside her",
                continuity_out="the garden is restored; Aoi and Nori share a quiet relieved look in the dawn",
            ),
        ),
        provider_supported_video_durations_sec=(10, 5),
        reference_sheet_required=True,
        max_paid_attempts=20,
    )


def alternate_no_provider_profile() -> AdaptiveProductionProfile:
    return AdaptiveProductionProfile(
        project_type="adaptive_canvas_v2_counterexample",
        title="Glass Orchard Oath",
        logline="A lone apprentice maps a glass orchard through three uneven beats before the moon gate closes.",
        style_bible="soft anime fantasy, glass fruit reflections, pale moonlight, calm suspense",
        characters=({"name": "Sora", "continuity": "amber bob hair, teal vest, white gloves", "role": "apprentice"},),
        scenes=(
            {"name": "glass orchard", "visual_mood": "clear trees and moonlit fruit", "story_function": "search begins"},
            {"name": "moon gate", "visual_mood": "silver arch and drifting pollen", "story_function": "resolution"},
        ),
        shots=(
            AdaptiveShotSpec(
                shot_id="shot-001",
                summary="Sora enters the glass orchard and hears the moon gate chime.",
                location="glass orchard",
                characters=("Sora",),
                action="Sora steps between transparent trees and raises a small compass.",
                camera="wide establishing drift",
                duration_sec=8.0,
                generation_strategy="text_to_video",
                strategy_reason="single character establishing shot can be generated directly from text",
                continuity_in="orchard entrance",
                continuity_out="compass points deeper inside",
            ),
            AdaptiveShotSpec(
                shot_id="shot-002",
                summary="Sora follows floating glass fruit to a hidden path.",
                location="glass orchard",
                characters=("Sora",),
                action="Glass fruit pulses one by one, revealing a zigzag path.",
                camera="over-shoulder tracking",
                duration_sec=12.0,
                generation_strategy="image_to_video",
                strategy_reason="the compass and character silhouette should stay anchored for the longer movement",
                continuity_in="compass points deeper inside",
                continuity_out="the hidden path opens toward the moon gate",
            ),
            AdaptiveShotSpec(
                shot_id="shot-003",
                summary="Sora reaches the moon gate and places the compass into the lock.",
                location="moon gate",
                characters=("Sora",),
                action="The gate unlocks as moonlight pours over the orchard.",
                camera="slow tilt from compass lock to open sky",
                duration_sec=16.0,
                generation_strategy="image_to_video",
                strategy_reason="final prop action and location continuity need an image anchor",
                continuity_in="the hidden path opens toward the moon gate",
                continuity_out="the gate opens and the oath is kept",
            ),
        ),
        provider_supported_video_durations_sec=(10, 5),
        reference_sheet_required=True,
        max_paid_attempts=20,
    )


def run_real_anime_4shot_paid_v1(
    *,
    runtime_root: Path,
    project_id: str,
    run_id: str,
    mode: Literal["real", "fake"] = "real",
    provider_config_path: Path | None = None,
    video_poll_interval_sec: float = 15.0,
    video_poll_timeout_sec: float = 5400.0,
):
    return run_adaptive_canvas_production(
        AdaptiveRunOptions(
            runtime_root=runtime_root,
            project_id=project_id,
            run_id=run_id,
            profile=real_anime_4shot_paid_profile(),
            mode=mode,
            provider_config_path=provider_config_path,
            video_poll_interval_sec=video_poll_interval_sec,
            video_poll_timeout_sec=video_poll_timeout_sec,
        )
    )


__all__ = [
    "PROJECT_TYPE",
    "alternate_no_provider_profile",
    "real_anime_4shot_paid_profile",
    "run_real_anime_4shot_paid_v1",
]
