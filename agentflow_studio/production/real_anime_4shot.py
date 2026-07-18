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
        llm_service_id="server_codex",
        script_candidate_id="script-v3",
        script_contract_id="adaptive_canvas_script_v3",
        title="Neon Courier Pact",
        logline=(
            "Two young couriers carry a glowing city charter across a vertical neon skyline before "
            "the dawn archive closes."
        ),
        style_bible="clean anime drama, crisp linework, expressive faces, cinematic vertical framing, consistent wardrobe",
        characters=(
            {
                "name": "Mira",
                "continuity": "short black hair, red courier scarf, cream jacket, determined expression",
                "role": "charter carrier",
            },
            {
                "name": "Ren",
                "continuity": "silver hair, green messenger sling, navy cropped coat, protective posture",
                "role": "route finder",
            },
        ),
        scenes=(
            {
                "name": "suspended night market",
                "visual_mood": "neon magenta, cyan signage, warm lanterns, glass railings",
                "story_function": "the charter is discovered and the race begins",
            },
            {
                "name": "dawn archive platform",
                "visual_mood": "gold sunrise, white stone, holographic clock glyphs",
                "story_function": "the charter is delivered and the city stabilizes",
            },
        ),
        shots=(
            AdaptiveShotSpec(
                shot_id="shot-001",
                summary="Mira and Ren discover the glowing charter in a suspended night market.",
                location="suspended night market",
                characters=("Mira", "Ren"),
                action="Mira lifts the folded charter while Ren watches the skyline clocks flicker.",
                camera="slow push-in from lantern stalls to the charter glow",
                duration_sec=15.0,
                generation_strategy="image_to_video",
                strategy_reason="recurring characters and the charter prop need a shared visual identity anchor",
                continuity_in="night market lanterns, both couriers together",
                continuity_out="they sprint toward the glass transit bridge with charter in Mira's satchel",
            ),
            AdaptiveShotSpec(
                shot_id="shot-002",
                summary="They cross a glass bridge while clock shadows sweep behind them.",
                location="glass transit bridge",
                characters=("Mira", "Ren"),
                action="The pair run in sync as luminous clock shadows chase across the glass floor.",
                camera="tracking side shot with the city rushing below",
                duration_sec=15.0,
                generation_strategy="image_to_video",
                strategy_reason="character continuity matters during fast movement across a new location",
                continuity_in="Mira carries the charter from the market",
                continuity_out="Ren points to an arriving sky train and they leap toward it",
            ),
            AdaptiveShotSpec(
                shot_id="shot-003",
                summary="On a sky train roof, Ren shields Mira while she seals the charter ribbon.",
                location="sky train roof",
                characters=("Mira", "Ren"),
                action="Wind snaps their scarves as Ren steadies Mira and the charter ribbon locks with blue light.",
                camera="low angle on the train roof with the city sliding past",
                duration_sec=15.0,
                generation_strategy="image_to_video",
                strategy_reason="the moving train scene still needs stable faces, wardrobe, and charter continuity",
                continuity_in="they leap from the bridge to the train roof",
                continuity_out="the train reaches the dawn archive platform",
            ),
            AdaptiveShotSpec(
                shot_id="shot-004",
                summary="At dawn, they deliver the charter and the city clocks stabilize.",
                location="dawn archive platform",
                characters=("Mira", "Ren"),
                action="Mira places the charter into the archive beacon, and the skyline clocks bloom into sunrise.",
                camera="wide reveal from hands at the beacon to the sunrise skyline",
                duration_sec=15.0,
                generation_strategy="image_to_video",
                strategy_reason="final delivery must preserve both couriers and the charter prop from earlier shots",
                continuity_in="the sealed charter arrives from the train roof",
                continuity_out="the city is saved; both couriers share a relieved look",
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
