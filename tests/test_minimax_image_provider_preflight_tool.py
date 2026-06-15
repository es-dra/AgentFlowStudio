from __future__ import annotations

import json

from tools import minimax_image_provider_preflight


def test_minimax_image_preflight_reports_ready_rest_api_without_secrets(tmp_path, monkeypatch, capsys) -> None:
    config_path = tmp_path / "providers.local.json"
    config_path.write_text(json.dumps(_minimax_rest_config()), encoding="utf-8")
    monkeypatch.setenv("AFS_PROVIDER_CONFIG", str(config_path))
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")

    exit_code = minimax_image_provider_preflight.main()

    assert exit_code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "ready"
    assert report["config_source"] == "AFS_PROVIDER_CONFIG"
    assert report["checks"]["service_present"] is True
    assert report["checks"]["execution_backend"] == "rest_api"
    assert report["checks"]["gate"] == {"env": "AFS_ALLOW_REMOTE_IMAGE", "enabled": True}
    assert report["checks"]["credential_presence"]["api_key_present"] is True
    assert report["checks"]["plan"]["api_family"] == "t2i"
    assert report["checks"]["plan"]["model"] == "image-01"
    assert report["secrets_printed"] is False
    serialized = json.dumps(report, ensure_ascii=False).lower()
    assert str(config_path).lower() not in serialized
    assert "fake-minimax-key" not in serialized
    assert "bearer " not in serialized


def test_minimax_image_preflight_reports_gate_closed_before_live_retry(tmp_path, monkeypatch, capsys) -> None:
    config_path = tmp_path / "providers.local.json"
    config_path.write_text(json.dumps(_minimax_rest_config()), encoding="utf-8")
    monkeypatch.setenv("AFS_PROVIDER_CONFIG", str(config_path))
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)

    exit_code = minimax_image_provider_preflight.main()

    assert exit_code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "gate_closed"
    assert report["checks"]["block_id"] == "image_gate_closed"
    assert report["checks"]["credential_presence"]["api_key_present"] is True
    assert report["secrets_printed"] is False


def _minimax_rest_config() -> dict:
    return {
        "schema_version": "company_provider_secrets.local.v2",
        "accounts": {
            "minimax": {
                "auth_type": "api_key",
                "base_url": "https://api.minimax.io/v1",
                "api_key": "fake-minimax-key",
                "default_models": {"image": "image-01"},
            }
        },
        "services": {
            "minimax_image": {
                "provider": "minimax",
                "account_ref": "minimax",
                "capability": "image",
                "required_gate": "NARRATOCUT_ALLOW_REMOTE_IMAGE",
                "descriptor": {
                    "schema_version": "provider_descriptor.v0.1",
                    "modality": "image",
                    "execution_mode": "sync",
                    "capabilities": ["image"],
                    "reference_image_slots": 1,
                    "supported_aspect_ratios": ["1:1", "4:3", "3:4", "16:9", "9:16"],
                    "prompt_char_limit": 1500,
                    "seed_supported": True,
                    "cost_hint": "test only",
                    "rate_limit_hint": "test only",
                    "required_gate": "NARRATOCUT_ALLOW_REMOTE_IMAGE",
                },
            }
        },
    }
