from __future__ import annotations

from pathlib import Path


def test_studio_state_route_keeps_sanitizer_and_context_helpers_split() -> None:
    api_root = Path("apps/api")
    route_source = (api_root / "runtime_studio_state.py").read_text(encoding="utf-8")
    sanitizer_path = api_root / "runtime_studio_state_sanitizer.py"
    context_path = api_root / "runtime_studio_state_context.py"
    assets_path = api_root / "runtime_studio_state_assets.py"
    params_path = api_root / "runtime_studio_state_params.py"
    param_values_path = api_root / "runtime_studio_state_param_values.py"
    preview_path = api_root / "runtime_studio_state_preview.py"
    feedback_policy_path = api_root / "runtime_studio_state_feedback_policy.py"

    assert sanitizer_path.is_file()
    assert context_path.is_file()
    assert assets_path.is_file()
    assert params_path.is_file()
    assert param_values_path.is_file()
    assert preview_path.is_file()
    assert feedback_policy_path.is_file()
    assert "from apps.api.runtime_studio_state_sanitizer import sanitize_studio_state" in route_source
    for helper_name in (
        "sanitize_studio_state",
        "_nodes",
        "_node_params",
        "_context_bundle",
        "_bundle_asset_list",
        "_preview_url",
    ):
        assert f"def {helper_name}" not in route_source

    sanitizer_source = sanitizer_path.read_text(encoding="utf-8")
    context_source = context_path.read_text(encoding="utf-8")
    assets_source = assets_path.read_text(encoding="utf-8")
    params_source = params_path.read_text(encoding="utf-8")
    param_values_source = param_values_path.read_text(encoding="utf-8")
    preview_source = preview_path.read_text(encoding="utf-8")
    feedback_policy_source = feedback_policy_path.read_text(encoding="utf-8")
    assert "def sanitize_studio_state" in sanitizer_source
    assert "sanitize_assets" in sanitizer_source
    assert "sanitize_node_params" in sanitizer_source
    assert "sanitize_context_bundle" in params_source
    assert "def sanitize_node_params" in params_source
    assert "assetCardDraft" in params_source
    assert "assetCardRevision" in params_source
    assert "keyframeLayer" in params_source
    assert "def asset_card_draft" in param_values_source
    assert "def asset_card_revision" in param_values_source
    assert "def keyframe_layer" in param_values_source
    assert "safe_preview_url" in sanitizer_source
    assert "def sanitize_context_bundle" in context_source
    assert "bundle_feedback_overlay_prompt_policy" in context_source
    assert "def bundle_feedback_overlay_prompt_policy" in feedback_policy_source
    assert "def _bundle_prompt_provider_gate" in feedback_policy_source
    assert "def sanitize_assets" in assets_source
    assert "def safe_preview_url" in preview_source
    assert "SAFE_PREVIEW_URL_PATTERN" not in sanitizer_source
    assert len(route_source.splitlines()) <= 300
    assert len(sanitizer_source.splitlines()) <= 300
    assert len(context_source.splitlines()) <= 300
    assert len(assets_source.splitlines()) <= 300
    assert len(params_source.splitlines()) <= 300
    assert len(param_values_source.splitlines()) <= 300
    assert len(preview_source.splitlines()) <= 300
    assert len(feedback_policy_source.splitlines()) <= 300
