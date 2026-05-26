from __future__ import annotations

import json

from typer.testing import CliRunner

from apps.cli.main import app


IMAGE_ENV_VARS = [
    "NARRATOCUT_ALLOW_REMOTE_IMAGE",
    "NARRATOCUT_IMAGE_PROVIDER",
    "NARRATOCUT_IMAGE_BASE_URL",
    "NARRATOCUT_IMAGE_API_KEY",
    "NARRATOCUT_IMAGE_MODEL",
]


def test_alpha_smoke_cli_reports_blocked_posterflow_without_provider_env(monkeypatch) -> None:
    for name in IMAGE_ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    result = CliRunner().invoke(app, ["alpha-smoke"])

    assert result.exit_code == 0, result.output
    assert "Alpha smoke readiness: blocked" in result.output
    assert "narratostudio_handoff      pass" in result.output
    assert "narratocut_package         pass" in result.output
    assert "posterflow_live_smoke      blocked" in result.output
    assert "Remote image provider is not enabled" in result.output
    assert "docs/alpha_readiness_report.md" in result.output


def test_alpha_smoke_cli_json_output_is_machine_readable(monkeypatch) -> None:
    for name in IMAGE_ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    result = CliRunner().invoke(app, ["alpha-smoke", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "blocked"
    assert payload["claim_boundary"] == "engineering_readiness_only"
    assert payload["remote_provider_policy"]["image"] == "disabled_by_default"
    assert [check["id"] for check in payload["checks"]] == [
        "narratostudio_handoff",
        "narratocut_package",
        "posterflow_live_smoke",
    ]
    assert payload["checks"][2]["status"] == "blocked"
    assert payload["checks"][2]["provider_env"]["NARRATOCUT_ALLOW_REMOTE_IMAGE"] == "unset"
