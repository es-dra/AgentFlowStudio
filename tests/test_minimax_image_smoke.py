from __future__ import annotations

import base64
import json

from typer.testing import CliRunner

from apps.cli.main import app
from agentflow_studio.model_gateway import ModelProviderError
from agentflow_studio.model_gateway.company_secrets import (
    COMPANY_PROVIDER_CONFIG_ENV,
    load_company_provider_secrets,
)
from agentflow_studio.model_gateway.minimax_image_smoke import (
    build_minimax_image_request_plan,
    run_minimax_image_smoke,
)
from agentflow_studio.production.posterflow import minimax_provider


PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)
PNG_B64 = base64.b64encode(PNG_BYTES).decode("ascii")


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_minimax_image_smoke_gate_disabled_fails_before_network(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    store = _store(tmp_path)

    def fake_urlopen(*args, **kwargs):  # pragma: no cover - must not call provider
        raise AssertionError("network should not be called when image gate is disabled")

    monkeypatch.setattr(minimax_provider.urllib.request, "urlopen", fake_urlopen)

    try:
        run_minimax_image_smoke(
            store,
            service_id="minimax_image",
            prompt="memory architecture demo keyframe",
            output_dir=tmp_path / "run",
        )
    except ModelProviderError as exc:
        assert "AFS_ALLOW_REMOTE_IMAGE" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected disabled gate failure")

    assert not (tmp_path / "run" / "minimax_image_smoke_manifest.json").exists()


def test_minimax_image_smoke_normalizes_account_base_url_and_falls_back_model(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    store = _store(tmp_path)
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["headers"] = dict(request.header_items())
        captured["timeout"] = timeout
        return FakeResponse(
            {
                "id": "minimax_task_001",
                "data": {"image_base64": [PNG_B64]},
                "base_resp": {"status_code": 0, "status_msg": "success"},
            }
        )

    monkeypatch.setattr(minimax_provider.urllib.request, "urlopen", fake_urlopen)

    manifest = run_minimax_image_smoke(
        store,
        service_id="minimax_image",
        prompt="memory architecture demo keyframe",
        output_dir=tmp_path / "run",
        aspect_ratio="9:16",
        timeout_sec=7.5,
    )

    assert captured["url"] == "https://api.minimaxi.com/v1/image_generation"
    assert captured["payload"] == {
        "model": "image-01",
        "prompt": "memory architecture demo keyframe",
        "aspect_ratio": "9:16",
        "response_format": "base64",
        "n": 1,
        "prompt_optimizer": False,
    }
    assert captured["headers"]["Authorization"] == "Bearer fk-mm-key"
    assert captured["timeout"] == 7.5
    assert manifest["status"] == "succeeded"
    assert manifest["model"] == "image-01"
    assert manifest["provider"] == "minimax_image"
    assert manifest["outputs"][0]["image_path"] == "image_candidates/candidate_001.png"
    assert (tmp_path / "run" / "image_candidates" / "candidate_001.png").read_bytes() == PNG_BYTES

    serialized = json.dumps(json.loads((tmp_path / "run" / "minimax_image_smoke_manifest.json").read_text()), ensure_ascii=False)
    assert "fk-mm-key" not in serialized
    assert "Bearer " not in serialized
    assert "api.minimaxi.com" not in serialized
    assert "minimax_task_001" not in serialized


def test_minimax_image_smoke_model_override_and_candidate_count(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    store = _store(tmp_path)
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse(
            {
                "id": "minimax_task_002",
                "data": {"image_base64": [PNG_B64, PNG_B64]},
                "base_resp": {"status_code": 0, "status_msg": "success"},
            }
        )

    monkeypatch.setattr(minimax_provider.urllib.request, "urlopen", fake_urlopen)

    manifest = run_minimax_image_smoke(
        store,
        service_id="minimax_image",
        prompt="memory architecture demo keyframe",
        output_dir=tmp_path / "run",
        model_name_override="image-01",
        candidate_count=2,
    )

    assert captured["payload"]["model"] == "image-01"
    assert captured["payload"]["n"] == 2
    assert manifest["candidate_count"] == 2
    assert len(manifest["outputs"]) == 2


def test_minimax_i2i_request_plan_uses_subject_reference_placeholder(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    store = _store(tmp_path)

    plan = build_minimax_image_request_plan(
        store,
        service_id="minimax_image",
        prompt="asset-driven desert keyframe",
        aspect_ratio="9:16",
        subject_reference_image_ref="yiqi_reference.png",
    )

    assert plan["api_family"] == "i2i"
    assert plan["create_request"]["json"]["subject_reference"] == [
        {"type": "character", "image_file": "<runtime_subject_reference_data_url>"}
    ]
    assert plan["subject_reference"] == {
        "image_ref": "yiqi_reference.png",
        "type": "character",
        "image_file_persisted": False,
    }
    serialized = json.dumps(plan, ensure_ascii=False)
    assert "data:image/" not in serialized
    assert "fk-mm-key" not in serialized


def test_minimax_i2i_smoke_sends_subject_reference_data_url_without_persisting_input(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    store = _store(tmp_path)
    reference_path = tmp_path / "yiqi_reference.png"
    reference_path.write_bytes(PNG_BYTES)
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse(
            {
                "id": "minimax_i2i_task_001",
                "data": {"image_base64": [PNG_B64]},
                "base_resp": {"status_code": 0, "status_msg": "success"},
            }
        )

    monkeypatch.setattr(minimax_provider.urllib.request, "urlopen", fake_urlopen)

    manifest = run_minimax_image_smoke(
        store,
        service_id="minimax_image",
        prompt="asset-driven desert keyframe",
        output_dir=tmp_path / "run",
        aspect_ratio="9:16",
        subject_reference_image_path=reference_path,
    )

    payload = captured["payload"]
    assert payload["subject_reference"][0]["type"] == "character"
    assert payload["subject_reference"][0]["image_file"].startswith("data:image/png;base64,")
    assert payload["subject_reference"][0]["image_file"].endswith(PNG_B64)
    assert manifest["api_family"] == "i2i"
    assert manifest["input_image"] == {
        "path_persisted": False,
        "byte_count": len(PNG_BYTES),
        "sha256": "sha256:" + __import__("hashlib").sha256(PNG_BYTES).hexdigest(),
        "mime_type": "image/png",
    }

    serialized = json.dumps(
        json.loads((tmp_path / "run" / "minimax_image_smoke_manifest.json").read_text()),
        ensure_ascii=False,
    )
    assert str(reference_path) not in serialized
    assert "data:image/" not in serialized
    assert PNG_B64 not in serialized
    assert "fk-mm-key" not in serialized
    assert "Bearer " not in serialized
    assert "api.minimaxi.com" not in serialized
    assert "minimax_i2i_task_001" not in serialized


def test_minimax_image_smoke_passes_seed_to_provider_payload(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    store = _store(tmp_path)
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse(
            {
                "id": "minimax_seed_task_001",
                "data": {"image_base64": [PNG_B64]},
                "base_resp": {"status_code": 0, "status_msg": "success"},
            }
        )

    monkeypatch.setattr(minimax_provider.urllib.request, "urlopen", fake_urlopen)

    run_minimax_image_smoke(
        store,
        service_id="minimax_image",
        prompt="seeded keyframe",
        output_dir=tmp_path / "run",
        seed=120401,
    )

    assert captured["payload"]["seed"] == 120401


def test_minimax_image_smoke_cli_exposes_command() -> None:
    result = CliRunner().invoke(app, ["minimax-image-smoke", "--help"])

    assert result.exit_code == 0, result.output
    assert "Run a gated MiniMax image smoke" in result.output
    assert "--provider-config" in result.output
    assert COMPANY_PROVIDER_CONFIG_ENV in result.output


def test_minimax_i2i_smoke_cli_exposes_reference_image_option() -> None:
    result = CliRunner().invoke(app, ["minimax-i2i-smoke", "--help"])

    assert result.exit_code == 0, result.output
    assert "Run a gated MiniMax image-to-image smoke" in result.output
    assert "--subject-reference-image" in result.output
    assert "--provider-config" in result.output
    assert COMPANY_PROVIDER_CONFIG_ENV in result.output


def test_minimax_image_smoke_cli_gate_failure_is_clean(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    config_path = tmp_path / "providers.local.json"
    config_path.write_text(json.dumps(_provider_config()), encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "minimax-image-smoke",
            "--prompt",
            "memory architecture demo keyframe",
            "--provider-config",
            str(config_path),
            "--output",
            str(tmp_path / "run"),
        ],
    )

    assert result.exit_code == 1
    assert "MiniMax image smoke failed" in result.output
    assert "AFS_ALLOW_REMOTE_IMAGE" in result.output
    assert "Traceback" not in result.output
    assert "fk-mm-key" not in result.output


def _store(tmp_path):
    config_path = tmp_path / "providers.local.json"
    config_path.write_text(json.dumps(_provider_config()), encoding="utf-8")
    return load_company_provider_secrets(config_path)


def _provider_config() -> dict:
    return {
        "schema_version": "company_provider_secrets.local.v2",
        "accounts": {
            "minimax": {
                "auth_type": "api_key",
                "base_url": "https://api.minimaxi.com/anthropic",
                "api_key": "fk-mm-key",
                "default_models": {"image": ""},
            }
        },
        "services": {
            "minimax_image": {
                "provider": "minimax",
                "account_ref": "minimax",
                "capability": "image",
                "api_family": "t2i",
                "required_gate": "AFS_ALLOW_REMOTE_IMAGE",
            },
        },
    }
