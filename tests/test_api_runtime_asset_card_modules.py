from __future__ import annotations

from pathlib import Path


def test_asset_card_draft_route_keeps_visual_observation_helpers_split() -> None:
    api_root = Path("apps/api")
    route_source = (api_root / "runtime_asset_card_drafts.py").read_text(encoding="utf-8")
    observation_source_path = api_root / "runtime_asset_card_observation.py"
    artifacts_source_path = api_root / "runtime_asset_card_artifacts.py"

    assert observation_source_path.is_file()
    assert artifacts_source_path.is_file()
    assert "from apps.api.runtime_asset_card_observation import" in route_source
    assert "from apps.api.runtime_asset_card_artifacts import" in route_source
    for helper_name in (
        "_dispatch_visual_inspection",
        "_provider_observation_for_asset_card",
        "_draft_prompt_from_observation",
        "_write_asset_card_artifacts",
        "_draft_input_refs",
        "_vision_provider_constraints",
    ):
        assert f"def {helper_name}" not in route_source
    observation_source = observation_source_path.read_text(encoding="utf-8")
    for helper_name in (
        "dispatch_visual_inspection",
        "provider_observation_for_asset_card",
        "draft_prompt_from_observation",
        "vision_provider_constraints",
    ):
        assert f"def {helper_name}" in observation_source
    artifacts_source = artifacts_source_path.read_text(encoding="utf-8")
    for helper_name in ("write_asset_card_artifacts", "draft_input_refs", "vision_gate_state"):
        assert f"def {helper_name}" in artifacts_source
    assert len(route_source.splitlines()) <= 300
    assert len(observation_source.splitlines()) <= 300
    assert len(artifacts_source.splitlines()) <= 300
