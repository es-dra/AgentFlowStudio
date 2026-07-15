from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "apps" / "studio_episode_candidate"


def _read(name: str) -> str:
    return (CANDIDATE / name).read_text(encoding="utf-8")


def _ref(entity_type: str, entity_id: str, version_id: str | None = None) -> dict[str, str]:
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "version_id": version_id or f"{entity_id}-v1",
    }


def _version(entity_type: str, entity_id: str, **extra: object) -> dict[str, object]:
    return {
        **_ref(entity_type, entity_id),
        "revision": 1,
        "lifecycle_state": "candidate",
        "review_state": "needs_review",
        **extra,
    }


def build_projection(shot_count: int = 15, *, recovery_at_shot_11: bool = False) -> dict[str, object]:
    scene_count = 3 if shot_count == 15 else 6
    scenes = [
        _version("scene", f"scene-{number:02d}", sequence=number, title=f"场景 {number}")
        for number in range(1, scene_count + 1)
    ]
    shots: list[dict[str, object]] = []
    projection_shots: list[dict[str, object]] = []
    for number in range(1, shot_count + 1):
        # The representative task deliberately starts with Shot 6 assigned to
        # the wrong scene. This lives only in test evidence, never product JS.
        scene_number = min(scene_count, max(1, (number - 1) // max(1, shot_count // scene_count) + 1))
        if shot_count == 15 and number == 6:
            scene_number = 1
        scene_ref = _ref("scene", f"scene-{scene_number:02d}")
        shot = _version(
            "shot",
            f"shot-{number:03d}",
            sequence=number,
            scene_ref=scene_ref,
            duration_seconds=9 if shot_count == 15 else 6,
        )
        shots.append(shot)
        projection_shots.append(
            {
                "ref": _ref("shot", f"shot-{number:03d}"),
                "scene_ref": scene_ref,
                "sequence": number,
                "duration_seconds": shot["duration_seconds"],
                "lifecycle_state": "candidate",
                "review_state": "needs_review" if number in {7, 10} else "not_requested",
                "production_state": "rework" if number == 6 else "draft",
                "selection_state": "selected" if number == 9 else "none",
                "ai_check_state": "passed" if number in {8, 11, 12, 13, 14, 15} else "pending",
                "blocking": number in {6, 7},
                "script": {"visual_action": f"镜头 {number} 的可见脚本", "dialogue": []},
                "facts": (
                    [
                        {"label": "角色", "value": "林遥", "status": "ok"},
                        {"label": "提灯扣", "value": "铜制提灯扣在右肩", "status": "conflict" if number == 7 else "ok"},
                        {"label": "面部特征", "value": "左眉疤不可镜像", "status": "conflict" if number == 7 else "ok"},
                    ]
                    if number in {7, 8}
                    else []
                ),
                "continuity_issue": (
                    {"summary": "提灯扣与眉疤方向不一致", "declared_impact_count": 2, "applied_count": 0}
                    if number == 7
                    else None
                ),
                "candidates": (
                    [
                        {"label": "第 1 版", "status_label": "当前", "summary": "记忆校验"},
                        {"label": "第 2 版", "status_label": "候选", "summary": "共同守护"},
                    ]
                    if number == 11
                    else []
                ),
                "allowed_actions": (
                    [
                        {
                            "action": "adopt_candidate",
                            "enabled": True,
                            "blocked_by": [_ref("shot", "shot-006"), _ref("shot", "shot-007")],
                            "reason": "请先完成镜头 6 与镜头 7 的前置问题。",
                        }
                    ]
                    if number == 11
                    else []
                ),
            }
        )

    next_ref = _ref("shot", "shot-011" if recovery_at_shot_11 else "shot-006")
    return {
        "schema_version": "afs_episode_workspace_projection.v0.1",
        "aggregate": {
            "schema_version": "afs_episode_production_aggregate.v0.1",
            "aggregate_version": 9,
            "evaluated_at": "2026-07-15T12:00:00+08:00",
            "scope": {"org_id": "org-test", "project_id": "project-test", "actor_id": "creator-test"},
            "projects": [
                _version(
                    "project",
                    "project-test",
                    title="雨灯纪事",
                    data_policy={
                        "visibility": "private",
                        "training_use": "denied_by_default",
                        "product_improvement_use": "denied_by_default",
                    },
                )
            ],
            "episodes": [_version("episode", "episode-test", title="第 1 集 · 雨夜档案塔")],
            "scenes": scenes,
            "shots": shots,
        },
        "workspace": {
            "evidence_environment": "test",
            "episode_ref": _ref("episode", "episode-test"),
            "scenes": [{"ref": _ref("scene", f"scene-{number:02d}"), "sequence": number, "title": f"场景 {number}"} for number in range(1, scene_count + 1)],
            "shots": projection_shots,
            "next_action": {"label": "修正镜头 6 的场景", "subject_ref": next_ref},
            "recovery": {
                "label": "8 项影响确认" if recovery_at_shot_11 else "待处理的场景问题",
                "active_shot_ref": next_ref,
                "mode": "storyboard",
                "scroll_to_active": True,
                "focus_active": True,
                "reconfirmed_count": 3 if recovery_at_shot_11 else 0,
                "reconfirmed_total": 8,
            },
            "truth": {
                "shot_count": shot_count,
                "duration_seconds": 135 if shot_count == 15 else shot_count * 6,
                "missing_asset_count": 25,
                "generation_dispatch_count": 0,
                "playable_preview_available": False,
            },
            "delivery": {
                "status": "blocked_missing_assets",
                "missing_asset_count": 25,
                "playable_preview_available": False,
            },
        },
    }


def run_state_script(script: str, projection: dict[str, object]) -> dict[str, object]:
    module_uri = (CANDIDATE / "state.mjs").resolve().as_uri()
    source = f"""
      import fs from "node:fs";
      import * as state from {json.dumps(module_uri)};
      const payload = JSON.parse(fs.readFileSync(0, "utf8"));
      {script}
    """
    result = subprocess.run(
        ["node", "--input-type=module", "-e", source],
        cwd=ROOT,
        check=True,
        capture_output=True,
        input=json.dumps(projection, ensure_ascii=False),
        text=True,
        encoding="utf-8",
    )
    return json.loads(result.stdout)


def test_candidate_is_isolated_contract_backed_and_has_no_local_persistence() -> None:
    index = _read("index.html")
    app = _read("app.mjs")
    api = _read("api-client.mjs")
    state = _read("state.mjs")
    all_product_source = "\n".join([index, app, api, state, _read("styles.css")])

    assert 'EPISODE_AGGREGATE_ROUTE = "/projects/{project_id}/episode-production-aggregate"' in api
    assert 'credentials: "include"' in api
    assert "EPISODE_COMMAND_ROUTE" not in api
    assert "submitEpisodeCommand" not in api + app
    assert "/episode-production-aggregate/commands" not in api + app
    assert "localStorage" not in all_product_source
    assert "sessionStorage" not in all_product_source
    assert "afs_episode_workspace_projection.v0.1" in state
    assert "afs_episode_production_aggregate.v0.1" in state
    assert "测试证据环境" in app
    assert "无限画布" not in app
    assert "Timeline" not in app


def test_product_javascript_does_not_embed_representative_episode_facts() -> None:
    product_js = "\n".join(_read(name) for name in ("app.mjs", "state.mjs", "api-client.mjs"))
    for forbidden in (
        "林遥",
        "小祈",
        "铜制提灯扣在右肩",
        "左眉疤不可镜像",
        "shot-006",
        "shot-007",
        "shot-011",
        "雨灯失窃案",
    ):
        assert forbidden not in product_js


def test_representative_projection_restores_active_to_next_and_preserves_truth() -> None:
    result = run_state_script(
        """
        const model = state.buildWorkspaceModel(payload);
        const ui = state.createInitialUiState(model);
        console.log(JSON.stringify({
          shotCount: model.shots.length,
          sceneCount: model.scenes.length,
          duration: model.truth.duration_seconds,
          missing: model.truth.missing_asset_count,
          dispatches: model.truth.generation_dispatch_count,
          playable: model.truth.playable_preview_available,
          active: state.activeShot(model, ui).sequence,
          next: state.nextShot(model, ui).sequence,
          checkpoint: model.recovery.reconfirmed_count,
        }));
        """,
        build_projection(),
    )
    assert result == {
        "shotCount": 15,
        "sceneCount": 3,
        "duration": 135,
        "missing": 25,
        "dispatches": 0,
        "playable": False,
        "active": 6,
        "next": 6,
        "checkpoint": 0,
    }


def test_three_of_eight_reload_checkpoint_recovers_shot_mode_and_next_together() -> None:
    result = run_state_script(
        """
        const model = state.buildWorkspaceModel(payload);
        const ui = state.createInitialUiState(model);
        console.log(JSON.stringify({
          active: state.activeShot(model, ui).sequence,
          next: state.nextShot(model, ui).sequence,
          mode: ui.mode,
          checkpoint: model.recovery.reconfirmed_count,
          checkpointTotal: model.recovery.reconfirmed_total,
          scroll: model.recovery.scroll_to_active,
          focus: model.recovery.focus_active,
        }));
        """,
        build_projection(recovery_at_shot_11=True),
    )
    assert result == {
        "active": 11,
        "next": 11,
        "mode": "storyboard",
        "checkpoint": 3,
        "checkpointTotal": 8,
        "scroll": True,
        "focus": True,
    }


def test_free_inspection_keeps_next_action_and_state_gates_shot_11_mutation() -> None:
    result = run_state_script(
        """
        const model = state.buildWorkspaceModel(payload);
        let ui = state.createInitialUiState(model);
        const shot11 = model.shots.find((shot) => shot.sequence === 11);
        ui = state.inspectShot(ui, shot11.ref);
        const action = state.availableAction(shot11, "adopt_candidate");
        const reviewUi = state.selectMode(ui, "review");
        const deliveryUi = state.selectMode(reviewUi, "delivery");
        console.log(JSON.stringify({
          active: state.activeShot(model, ui).sequence,
          next: state.nextShot(model, ui).sequence,
          differs: state.shouldShowCurrentVersusNext(ui),
          adoptEnabled: action.enabled,
          blockerCount: action.blockedBy.length,
          reviewShot: state.activeShot(model, reviewUi).sequence,
          deliveryShot: state.activeShot(model, deliveryUi).sequence,
        }));
        """,
        build_projection(),
    )
    assert result == {
        "active": 11,
        "next": 6,
        "differs": True,
        "adoptEnabled": False,
        "blockerCount": 2,
        "reviewShot": 11,
        "deliveryShot": 11,
    }


def test_projection_fails_closed_when_visible_shot_is_not_an_exact_aggregate_fact() -> None:
    projection = build_projection()
    projection["workspace"]["shots"][0]["ref"]["version_id"] = "shot-001-unknown"
    module_uri = (CANDIDATE / "state.mjs").resolve().as_uri()
    source = f"""
      import fs from "node:fs";
      import {{ buildWorkspaceModel }} from {json.dumps(module_uri)};
      const payload = JSON.parse(fs.readFileSync(0, "utf8"));
      try {{ buildWorkspaceModel(payload); console.log(JSON.stringify({{ blocked: false }})); }}
      catch (error) {{ console.log(JSON.stringify({{ blocked: true, message: error.message }})); }}
    """
    result = subprocess.run(
        ["node", "--input-type=module", "-e", source],
        cwd=ROOT,
        check=True,
        capture_output=True,
        input=json.dumps(projection, ensure_ascii=False),
        text=True,
        encoding="utf-8",
    )
    evidence = json.loads(result.stdout)
    assert evidence["blocked"] is True
    assert "不一致" in evidence["message"]


def test_sixty_shot_stress_projection_filters_without_changing_active_identity() -> None:
    projection = build_projection(60)
    result = run_state_script(
        """
        const model = state.buildWorkspaceModel(payload);
        let ui = state.createInitialUiState(model);
        const scene = model.scenes[4];
        ui = state.selectSceneFilter(ui, scene.ref);
        const sceneCount = state.visibleShots(model, ui).length;
        ui = state.selectStatusFilter(ui, "blocking");
        const blockingInScene = state.visibleShots(model, ui).length;
        console.log(JSON.stringify({
          shots: model.shots.length,
          scenes: model.scenes.length,
          sceneCount,
          blockingInScene,
          active: state.activeShot(model, ui).sequence,
          next: state.nextShot(model, ui).sequence,
        }));
        """,
        projection,
    )
    assert result == {
        "shots": 60,
        "scenes": 6,
        "sceneCount": 10,
        "blockingInScene": 0,
        "active": 6,
        "next": 6,
    }


def test_reset_is_a_native_confirmation_and_current_get_only_wave_cannot_mutate() -> None:
    app = _read("app.mjs")
    assert '<dialog class="confirm-dialog"' in app
    assert 'data-action="reset-recovery"' in app
    assert 'resetDialog.showModal()' in app
    assert '<button class="danger-button" value="confirm" disabled>' in app
    assert "本页当前只读" in app
    assert "已恢复 · 当前只读" in app
    assert "sendCommand" not in app


def test_get_only_dependency_matches_current_route_and_openapi_boundary() -> None:
    api = _read("api-client.mjs")
    readme = _read("README.md")
    openapi_path = ROOT / "docs" / "openapi" / "afs-runtime-service.openapi.json"
    openapi = json.loads(openapi_path.read_text(encoding="utf-8"))
    documented_paths = openapi.get("paths", {})

    assert 'method: "GET"' in api
    assert 'method: "POST"' not in api
    assert "This Wave is GET-only" in readme
    assert "does not prove a production vertical slice" in readme
    assert not any(path.endswith("/episode-production-aggregate/commands") for path in documented_paths)
    aggregate_methods = set(
        documented_paths.get("/projects/{project_id}/episode-production-aggregate", {})
    )
    assert aggregate_methods == {"get", "put"}

    api_route_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "apps" / "api").glob("*.py")
    )
    assert '"/projects/{project_id}/episode-production-aggregate"' in api_route_sources
    assert "episode-production-aggregate/commands" not in api_route_sources


def test_candidate_sources_have_no_common_utf8_mojibake_sequences() -> None:
    source = "\n".join(_read(name) for name in ("index.html", "app.mjs", "api-client.mjs", "state.mjs"))
    for corrupted in ("\ufffd", "娴嬭瘯", "鏈", "鍘熷瀷", "锛屾", "銆傛", "Ã", "â€"):
        assert corrupted not in source


def test_mobile_layout_is_card_and_detail_based_without_wide_table() -> None:
    styles = _read("styles.css")
    app = _read("app.mjs")
    assert "@media (max-width: 760px)" in styles
    assert ".shot-card { grid-template-columns: 120px 1fr;" in styles
    assert ".workspace-layout { display: block;" in styles
    assert 'data-action="back-to-shots"' in app
    assert 'data-action="open-mobile-nav"' in app
    assert "<table" not in app.lower()
    assert "overflow-x: auto" not in styles
