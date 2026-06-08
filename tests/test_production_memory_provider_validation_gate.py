from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import agentflow.memory.production_asset_provider_validation_gate as provider_gate
from agentflow.memory.production_asset_provider_validation_gate import run_provider_validation_gate

EXAMPLE_SEED = Path("examples/agentflow/production_memory_asset_profile_seed.example.json")
GENERATED_AT = "2026-06-04T02:00:00+08:00"


def test_provider_validation_gate_defaults_to_blocked_without_remote_call(tmp_path: Path) -> None:
    result = run_provider_validation_gate(
        asset_profile_seed_path=EXAMPLE_SEED,
        output_dir=tmp_path,
        generated_at=GENERATED_AT,
    )

    assert result["status"] == "blocked"
    assert result["provider_calls_started"] is False
    assert result["writes_long_term_memory"] is False
    assert result["writes_company_kb"] is False
    assert {item["blocker_id"] for item in result["blockers"]} == {"provider_validation_not_requested"}
    assert "not human acceptance" in result["non_claims"]
    assert "not business validation" in result["non_claims"]

    for name in (
        "provider_validation_plan.json",
        "provider_validation_result.json",
        "provider_safe_manifest.json",
        "provider_validation_report.md",
    ):
        assert (tmp_path / name).exists(), name

    safe = _read_json(tmp_path / "provider_safe_manifest.json")
    assert safe["artifact_type"] == "agentflow_provider_safe_manifest"
    assert safe["status"] == "blocked"
    assert safe["request_summary"]["private_paths_persisted"] is False
    assert safe["request_summary"]["media_bytes_persisted"] is False
    assert safe["provider_calls_started"] is False


def test_provider_validation_gate_cli_smoke(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "asset-provider-validation-gate",
            "--asset-profile-seed",
            str(EXAMPLE_SEED),
            "--generated-at",
            GENERATED_AT,
            "--output",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Provider validation gate: blocked" in result.stdout
    assert "Provider calls: not started" in result.stdout
    assert "Business validation: not claimed" in result.stdout
    assert (tmp_path / "provider_validation_report.md").exists()


def test_provider_validation_gate_preserves_live_failure_blockers(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(provider_gate, "provider_validation_blockers", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        provider_gate,
        "execute_provider_validation",
        lambda *args, **kwargs: {
            "kind": "agentflow_provider_validation_result",
            "artifact_type": "agentflow_provider_validation_result",
            "schema_version": "production-memory-loop/v1",
            "status": "failed",
            "provider_calls_started": True,
            "safe_error": "Kling video request failed: ConnectError",
            "blockers": [
                {
                    "blocker_id": "provider_validation_failed",
                    "message": "Kling video request failed: ConnectError",
                }
            ],
        },
    )

    result = provider_gate.run_provider_validation_gate(
        asset_profile_seed_path=EXAMPLE_SEED,
        output_dir=tmp_path,
        generated_at=GENERATED_AT,
        run_provider_validation=True,
        provider_config_path=tmp_path / "providers.local.json",
        character_reference_image_path=tmp_path / "character.png",
    )

    assert result["status"] == "failed"
    assert result["provider_calls_started"] is True
    assert {item["blocker_id"] for item in result["blockers"]} == {"provider_validation_failed"}

    safe = _read_json(tmp_path / "provider_safe_manifest.json")
    assert safe["status"] == "failed"
    assert {item["blocker_id"] for item in safe["blockers"]} == {"provider_validation_failed"}
    assert "provider_validation_failed" in (tmp_path / "provider_validation_report.md").read_text(encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
