from __future__ import annotations

import json

from fastapi.testclient import TestClient

from apps.api.runtime_asset_extraction import normalize_asset_refs_with_diagnostics, principal_asset_refs_with_diagnostics
from apps.api.runtime_models import StoryboardBreakdownRequest
from apps.api.runtime_service import create_runtime_app
from apps.api.runtime_storyboard_breakdown import build_storyboard_breakdown
from apps.api.runtime_storyboard_local import local_storyboard_shots
from apps.api.runtime_storyboard_provider_parse import shots_from_provider_text


def test_critical_prop_requires_explicit_evidence_and_background_prop_stays_held() -> None:
    refs, dropped = normalize_asset_refs_with_diagnostics(
        [
            {
                "label": "金箍棒",
                "asset_type": "prop",
                "source": "candidate",
                "evidence_text": "孙悟空手持金箍棒向前压低身形。",
            },
            {
                "label": "路灯",
                "asset_type": "prop",
                "source": "candidate",
                "evidence_text": "街道背景里有远处路灯。",
            },
        ],
        context="孙悟空手持金箍棒向前压低身形。街道背景里有远处路灯。",
    )

    principal, dropped = principal_asset_refs_with_diagnostics(refs, dropped)
    by_label = {item["label"]: item for item in principal}

    assert "金箍棒" in by_label
    assert "character_possession_or_handoff" in by_label["金箍棒"]["critical_prop_evidence"]
    assert "路灯" not in by_label
    assert any(item["display_name"] == "路灯" and item["reason"] == "prop_requires_critical_evidence_or_manual_asset_entry" for item in dropped)


def test_manual_same_name_ref_overrides_inferred_candidate_with_exact_provenance() -> None:
    refs, dropped = normalize_asset_refs_with_diagnostics(
        [
            {
                "label": "Future Robot",
                "asset_type": "character",
                "source": "candidate",
                "confidence": 0.82,
                "evidence_text": "Future Robot stands on the rooftop.",
            },
            {
                "label": "Future Robot",
                "asset_type": "character",
                "source": "manual",
                "status": "approved",
                "asset_id": "manual_future_robot",
                "confidence": 0.97,
                "evidence_text": "Manual approved Future Robot asset.",
            },
        ],
        context="Future Robot stands on the rooftop.",
        include_inferred=True,
    )

    assert dropped == []
    assert len([item for item in refs if item["label"] == "Future Robot"]) == 1
    robot = next(item for item in refs if item["label"] == "Future Robot")
    assert robot["source"] == "manual"
    assert robot["status"] == "approved"
    assert robot["asset_id"] == "manual_future_robot"
    assert robot["confidence"] == 0.97


def test_fixed_visual_asset_replaces_same_name_inferred_ref_and_confidence(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_LLM", raising=False)
    request = StoryboardBreakdownRequest(
        node_id="story_001",
        script_text="Future Robot stands on a city rooftop and checks the glowing map in hand.",
        target_platform="short_video",
        style="cinematic",
        generated_at="2026-07-16T00:00:00+00:00",
    )

    result = build_storyboard_breakdown(
        "proj_fixed_override",
        request,
        tmp_path,
        fixed_visual_assets=[
            {
                "asset_id": "vas_future_robot_fixed",
                "asset_type": "character",
                "label": "Future Robot",
                "status": "fixed",
                "signature": "approved angular chrome robot reference",
            }
        ],
    )

    shot_robot = next(ref for ref in result["shots"][0]["asset_refs"] if ref["label"] == "Future Robot")
    graph_robot = next(asset for asset in result["asset_graph"]["assets"] if asset["label"] == "Future Robot")

    assert shot_robot["source"] == "fixed_visual_asset_reuse"
    assert shot_robot["status"] == "fixed"
    assert shot_robot["asset_id"] == "vas_future_robot_fixed"
    assert shot_robot["confidence"] == 0.9
    assert graph_robot["asset_id"] == "vas_future_robot_fixed"
    assert graph_robot["confidence"] == 0.9
    assert result["provider_calls_started"] is False


def test_scene_identity_normalizes_action_location_phrase_to_stable_location() -> None:
    source_script = "小明蹲在老城区巷口的青石台阶上，指尖沾着猫粮碎屑。"
    payload = {
        "shots": [
            {
                "shot_id": "shot_01",
                "index": 1,
                "duration": "5s",
                "description": "@小明 @小明蹲在老城区巷口。小明蹲在老城区巷口的青石台阶上。",
                "shot_size": "中景",
                "light_atmosphere": "夕阳侧光",
                "camera_motion": "固定机位",
                "dialogue": "无明确对白",
                "sound": "环境底噪",
                "source_span": {"text": source_script},
                "asset_refs": [
                    {"label": "小明", "asset_type": "character", "status": "mentioned", "source": "explicit"},
                    {"label": "小明蹲在老城区巷口", "asset_type": "scene", "status": "mentioned", "source": "explicit"},
                ],
            }
        ]
    }

    shots = shots_from_provider_text(json.dumps(payload, ensure_ascii=False), source_script_text=source_script)
    scene_refs = [ref for ref in shots[0]["asset_refs"] if ref["asset_type"] == "scene"]

    assert [ref["label"] for ref in scene_refs] == ["老城区巷口"]
    assert all("蹲在" not in ref["label"] for ref in scene_refs)


def test_local_fallback_scopes_future_props_to_current_shot_and_resolves_animal_alias() -> None:
    script = (
        "小明蹲在老城区巷口的青石台阶上，怀里橘猫“煤球”正用肉垫按他手腕。"
        "暴雨如注，古战场泥泞翻涌，沈砚单膝陷在泥中，死攥半截断戟。"
        "他喉结剧烈滚动。"
        "沈砚翻转一枚青铜虎符，虎符反射雷光。"
    )

    shots = local_storyboard_shots(script, shot_count_hint=4)
    first_refs = {ref["label"]: ref for ref in shots[0]["asset_refs"]}
    shot2_labels = {(ref["label"], ref["asset_type"]) for ref in shots[1]["asset_refs"]}
    shot4_labels = {(ref["label"], ref["asset_type"]) for ref in shots[3]["asset_refs"]}

    assert first_refs["煤球"]["character_subtype"] == "animal"
    assert ("断戟", "prop") in shot2_labels
    assert ("青铜虎符", "prop") not in shot2_labels
    assert ("青铜虎符", "prop") in shot4_labels


def test_provider_off_storyboard_fallback_is_visible_and_provider_zero(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_LLM", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    client.post("/projects", json={"project_id": "proj_provider_zero", "goal": "Storyboard provider zero"})

    response = client.post(
        "/projects/proj_provider_zero/storyboard-breakdowns",
        json={
            "node_id": "story_001",
            "script_text": "Future Robot stands on a city rooftop and checks the glowing map in hand.",
            "target_platform": "short_video",
            "style": "cinematic",
            "generated_at": "2026-07-16T00:00:00+00:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider_calls_started"] is False
    assert payload["fallback_visible_to_user"] is True
    assert payload["fallback_reason"] == "llm_gate_blocked"
    assert payload["safe_manifest"]["fallback_visible_to_user"] is True
    assert payload["safe_manifest"]["provider_calls_started"] is False
