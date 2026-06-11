from __future__ import annotations

import base64
import json

from agentflow_studio.model_gateway import minimax_image_cli_runtime, minimax_image_runtime
from agentflow_studio.model_gateway.errors import ModelProviderError
from agentflow_studio.model_gateway.minimax_image_smoke import run_minimax_image_smoke
from tests.minimax_image_test_helpers import store as _store


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


def test_minimax_image_smoke_reads_api_key_from_env(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    monkeypatch.setenv("MINIMAX_API_KEY", "fk-env-mm-key")
    store = _store(tmp_path, use_env_key=True)
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        captured["headers"] = dict(request.header_items())
        return FakeResponse(
            {
                "id": "minimax_env_task_001",
                "data": {"image_base64": [PNG_B64]},
                "base_resp": {"status_code": 0, "status_msg": "success"},
            }
        )

    monkeypatch.setattr(minimax_image_runtime.urllib.request, "urlopen", fake_urlopen)

    manifest = run_minimax_image_smoke(
        store,
        service_id="minimax_image",
        prompt="env based keyframe",
        output_dir=tmp_path / "run",
    )

    assert captured["headers"]["Authorization"] == "Bearer fk-env-mm-key"
    assert manifest["status"] == "succeeded"
    serialized = json.dumps(manifest, ensure_ascii=False)
    assert "fk-env-mm-key" not in serialized


def test_minimax_image_smoke_exposes_safe_status_message(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    store = _store(tmp_path)

    def fake_urlopen(request, timeout):
        return FakeResponse(
            {
                "data": {"image_base64": []},
                "base_resp": {"status_code": 2049, "status_msg": "invalid API Key"},
            }
        )

    monkeypatch.setattr(minimax_image_runtime.urllib.request, "urlopen", fake_urlopen)

    try:
        run_minimax_image_smoke(
            store,
            service_id="minimax_image",
            prompt="env based keyframe",
            output_dir=tmp_path / "run",
        )
    except ModelProviderError as exc:
        assert str(exc) == "MiniMax image response status_code 2049: invalid API Key"
    else:  # pragma: no cover
        raise AssertionError("expected MiniMax status failure")


def test_minimax_image_smoke_can_use_mmx_cli_backend(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    store = _store(tmp_path, use_mmx_cli=True)
    reference_path = tmp_path / "front_reference.png"
    reference_path.write_bytes(PNG_BYTES)
    captured: dict[str, object] = {}

    def fake_which(command):
        return f"C:/fake/{command}.cmd"

    def fake_run(command, **kwargs):
        captured["command"] = command
        image_dir = tmp_path / "run" / "image_candidates"
        image_dir.mkdir(parents=True, exist_ok=True)
        (image_dir / "candidate_001.jpg").write_bytes(b"\xff\xd8fake-jpg")

        class Result:
            returncode = 0
            stdout = '{"saved":["candidate_001.jpg"]}'
            stderr = ""

        return Result()

    monkeypatch.setattr(minimax_image_cli_runtime.shutil, "which", fake_which)
    monkeypatch.setattr(minimax_image_cli_runtime.subprocess, "run", fake_run)
    monkeypatch.setattr(
        minimax_image_runtime.urllib.request,
        "urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("REST API should not be called")),
    )

    manifest = run_minimax_image_smoke(
        store,
        service_id="minimax_image",
        prompt="token plan keyframe",
        output_dir=tmp_path / "run",
        aspect_ratio="9:16",
        seed=120501,
        subject_reference_image_path=reference_path,
    )

    assert str(captured["command"][0]).replace("\\", "/").endswith("/mmx.cmd")
    assert captured["command"][1:3] == ["image", "generate"]
    assert "--region" in captured["command"]
    assert "cn" in captured["command"]
    assert "--seed" in captured["command"]
    assert "--subject-ref" in captured["command"]
    assert any(str(item).startswith("type=character,image=") for item in captured["command"])
    assert manifest["execution_backend"] == "mmx_cli"
    assert manifest["api_family"] == "i2i"
    assert manifest["input_image"]["path_persisted"] is False
    assert manifest["outputs"][0]["image_path"] == "image_candidates/candidate_001.jpg"
    serialized = json.dumps(manifest, ensure_ascii=False).lower()
    assert "fk-mm-key" not in serialized
    assert "bearer " not in serialized
    assert "api.minimax.io" not in serialized
