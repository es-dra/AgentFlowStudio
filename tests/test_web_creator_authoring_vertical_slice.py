from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "apps" / "studio" / "episode-workspace"


def _read(name: str) -> str:
    return (WORKSPACE / name).read_text(encoding="utf-8")


def _run_model(expression: str) -> object:
    module_uri = (WORKSPACE / "authoring-model.mjs").resolve().as_uri()
    result = subprocess.run(
        [
            "node",
            "--input-type=module",
            "-e",
            f'import * as subject from {json.dumps(module_uri)}; console.log(JSON.stringify({expression}));',
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(result.stdout)


def test_creator_workspace_is_project_first_and_legacy_episode_route_still_exists() -> None:
    app = _read("app.mjs")
    html = _read("index.html")

    assert 'projectId && !episodeId && !episodeVersionId' in app
    assert 'import("./authoring-app.mjs?creator=v05")' in app
    assert "hydrate();" in app
    assert "单集制作工作区 · 长篇创作" in html


def test_storyboard_and_canvas_render_one_model_and_send_one_typed_command_path() -> None:
    app = _read("authoring-app.mjs")
    api = _read("authoring-api-client.mjs")
    runtime_client = (ROOT / "apps" / "studio" / "src" / "runtime-client.js").read_text(
        encoding="utf-8"
    )
    commands = _read("authoring-commands.mjs")
    source = "\n".join((app, api, commands, _read("authoring-model.mjs")))

    assert 'ui.mode === "canvas" ? renderCanvas() : renderStoryboard()' in app
    assert "shotsForScene(model, scene.ref)" in app
    assert "data-shot=" in app
    assert "reviseShotCommand" in app
    assert 'action: "shot.revise_intent"' in commands
    assert "/episode-production-aggregate/commands" in runtime_client
    assert '"Idempotency-Key": idempotencyKey' in runtime_client
    assert "localStorage" not in source
    assert "sessionStorage" not in source
    assert "shot-006" not in source


def test_pending_command_envelope_is_server_persisted_and_malformed_state_fails_closed() -> None:
    app = _read("authoring-app.mjs")
    api = _read("authoring-api-client.mjs")

    assert "saveStudioState" in api
    assert "creator_authoring" in app
    assert "pendingCommand" in app
    assert "validPendingEnvelope" in app
    assert "runCommand(pending.command, pending.idempotency_key)" in app
    assert "工作台没有覆盖" in app
    assert _run_model("subject.validPendingEnvelope({pending: true})") is False
    assert (
        _run_model(
            "subject.validPendingEnvelope({idempotency_key:'creator-1',status:'pending',"
            "schema_version:'afs_creator_pending_command.v0.1',"
            "command:{action:'shot.revise_intent',expected_aggregate_version:2}})"
        )
        is True
    )


def test_default_creator_surface_hides_internal_runtime_and_provider_noise() -> None:
    app = _read("authoring-app.mjs")
    default_surface = app.split("function renderNavigation", maxsplit=1)[0]

    for forbidden in (
        "reference_set_id",
        "provider",
        "runtime",
        "8790",
        "8791",
        "8793",
        "internal trial",
        "Stage Gate",
    ):
        assert forbidden not in default_surface
    assert "故事板" in app
    assert "同源画布" in app
    assert "仅项目成员可见" in app


def test_creator_styles_have_desktop_three_column_and_mobile_single_column_contracts() -> None:
    css = _read("styles.css")

    assert ".creator-layout" in css
    assert "grid-template-columns: 272px minmax(520px, 1fr) 370px" in css
    assert "@media (max-width: 760px)" in css
    assert ".creator-nav { display: none; }" in css
    assert ".creator-inspector.mobile-open" in css
    assert ".canvas-node.selected" in css
