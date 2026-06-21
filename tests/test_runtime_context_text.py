from apps.api.runtime_context_text import provider_prompt_from_bundle
from apps.api.runtime_context_text import text_channel


def test_reference_localized_edit_prompt_leads_with_requested_delta() -> None:
    bundle = {
        "reference_image_channel": [{"asset_id": "img_base", "role": "subject_reference"}],
        "text_channel": {
            "visible_prompt": (
                "Add exactly one subtle diagonal scar on Lin Wan's left eyebrow. "
                "Preserve the same person, hair, wardrobe, background, framing, and lighting."
            ),
            "asset_identity_segment": (
                "Lin Wan: black shoulder-length short hair, beige trench coat, "
                "soft gray portrait background; no scar in base asset. "
                "Locks: keep black short hair; keep beige trench coat."
            ),
            "scene_director_segment": "",
            "upstream_summary_segment": "",
            "preference_segment": "",
        },
    }

    prompt = provider_prompt_from_bundle(bundle)

    assert prompt.startswith("Requested change / preserve policy")
    assert prompt.index("Add exactly one subtle diagonal scar") < prompt.index("no scar in base asset")
    assert "Reference/base descriptors are anchors, not instructions to undo the requested change." in prompt


def test_non_edit_fixed_asset_generation_keeps_identity_first() -> None:
    bundle = {
        "reference_image_channel": [{"asset_id": "img_base", "role": "subject_reference"}],
        "text_channel": {
            "visible_prompt": "Create a cinematic portrait of Lin Wan walking through rain.",
            "asset_identity_segment": "Lin Wan: black shoulder-length short hair. Locks: keep identity.",
            "scene_director_segment": "Scene: night rain alley.",
            "upstream_summary_segment": "",
            "preference_segment": "",
        },
    }

    prompt = provider_prompt_from_bundle(bundle)

    assert prompt.startswith("Lin Wan: black shoulder-length short hair")
    assert "Requested change / preserve policy" not in prompt


def test_reference_localized_edit_detects_modify_only_language() -> None:
    bundle = {
        "reference_image_channel": [{"asset_id": "img_base", "role": "subject_reference"}],
        "text_channel": {
            "visible_prompt": (
                "Modify only the key light to be warmer around the eyebrow area. "
                "Keep identity, hair, wardrobe, background, framing, and motion unchanged."
            ),
            "asset_identity_segment": "Lin Wan: black shoulder-length short hair. Locks: keep cool gray lighting.",
            "scene_director_segment": "",
            "upstream_summary_segment": "",
            "preference_segment": "",
        },
    }

    prompt = provider_prompt_from_bundle(bundle)

    assert prompt.startswith("Requested change / preserve policy")
    assert prompt.index("Modify only the key light") < prompt.index("keep cool gray lighting")


def test_animal_prompt_sanitizes_legacy_character_asset_signature() -> None:
    channel = text_channel(
        "optimize",
        "根据上游节点的狸花猫,生成这只猫在房间里跳舞的图片",
        [
            (
                {
                    "label": "Cute tabby cat reclining in a",
                    "signature": "Cute tabby cat reclining in a reference character, pending human confirmation",
                    "asset_type": "character",
                },
                "signature",
            )
        ],
        set(),
    )

    segment = channel["asset_signature_segment"]
    assert "reference animal subject" in segment
    assert "pending human confirmation" not in segment
    assert "reference character" not in segment
