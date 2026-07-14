from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import math
import struct
import sys
import wave
import zlib
from io import BytesIO
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from agentflow_studio.production.representative_episode_media import derive_authoritative_inventory
from apps.api.runtime_service import create_runtime_app
from tools.studio_production_delivery_browser_qa import (
    QA_EMAIL,
    QA_PASSWORD,
    _qa_environment,
    prepare_provider_free_delivery_qa,
)


def build_provider_free_media_admissions(binding: dict[str, Any]) -> list[dict[str, Any]]:
    admissions: list[dict[str, Any]] = []
    for slot in derive_authoritative_inventory(binding):
        if slot["category"] == "audio":
            payload = _wav_bytes(220 + slot["ordinal"] * 7)
            media_kind, mime_type = "audio", "audio/wav"
        else:
            payload = _pattern_png(640, 360, slot["ordinal"])
            media_kind, mime_type = "image", "image/png"
        admissions.append(
            {
                "asset_id": slot["asset_id"],
                "revision_id": slot["revision_id"],
                "media_kind": media_kind,
                "mime_type": mime_type,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "data_base64": base64.b64encode(payload).decode("ascii"),
            }
        )
    return admissions


def prepare_provider_free_media_delivery(runtime_root: str | Path, *, assemble: bool = True) -> dict[str, Any]:
    root = Path(runtime_root).resolve()
    seed = prepare_provider_free_delivery_qa(root)
    with _qa_environment(), TestClient(create_runtime_app(runtime_root=root)) as client:
        login = client.post("/auth/login", json={"email": QA_EMAIL, "password": QA_PASSWORD})
        login.raise_for_status()
        headers = {"Authorization": f"Bearer {login.json()['session_token']}"}
        run_route = f"/projects/{seed['project_id']}/production-runs/{seed['run_id']}"
        run = client.get(run_route, headers=headers).json()["production_run"]
        binding = run["representative_episode_binding"]
        admissions = build_provider_free_media_admissions(binding)
        intake = client.post(
            f"{run_route}/representative-episode-media/intake",
            headers=headers,
            json={
                "schema_version": "afs_representative_episode_media_intake.v0.1",
                "idempotency_key": "rainlight-provider-free-media-intake-v2",
                "expected_checkpoint_version": run["checkpoint"]["version"],
                "expected_binding_digest": binding["binding_digest"],
                "expected_episode_version_id": binding["episode_version_id"],
                "assets": admissions,
            },
        )
        intake.raise_for_status()
        media_run = intake.json()["production_run"]
        if assemble:
            media = media_run["representative_episode_media"]
            assembled = client.post(
                f"{run_route}/representative-episode-media/assemble",
                headers=headers,
                json={
                    "schema_version": "afs_representative_episode_media_assembly.v0.1",
                    "idempotency_key": "rainlight-provider-free-technical-assembly-v2",
                    "expected_checkpoint_version": media_run["checkpoint"]["version"],
                    "expected_binding_digest": binding["binding_digest"],
                    "expected_media_manifest_sha256": media["manifest_sha256"],
                },
            )
            assembled.raise_for_status()
            media_run = assembled.json()["production_run"]
        return {
            **seed,
            "media_manifest_sha256": media_run["representative_episode_media"]["manifest_sha256"],
            "media_accepted_count": len(media_run["representative_episode_media"]["assets"]),
            "assembly_complete": (
                media_run["representative_episode_media"].get("assembly_status")
                == "technical_qa_passed"
            ),
            "provider_calls_started": False,
            "evidence_label": "canonical_media_delivery_bridge_pass" if assemble else "media_intake_mechanics_pass",
            "representative_content_proof": "not_started",
        }


def _pattern_png(width: int, height: int, seed: int) -> bytes:
    signature = b"\x89PNG\r\n\x1a\n"
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            rows.extend(
                (
                    (x * 3 + seed * 29 + y) % 256,
                    (y * 5 + seed * 17 + x // 3) % 256,
                    ((x + y) * 2 + seed * 11) % 256,
                )
            )
    payload = zlib.compress(bytes(rows), level=6)
    return signature + _png_chunk(b"IHDR", header) + _png_chunk(b"IDAT", payload) + _png_chunk(b"IEND", b"")


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    checksum = binascii.crc32(kind + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", checksum)


def _wav_bytes(frequency: int) -> bytes:
    rate = 48_000
    stream = BytesIO()
    with wave.open(stream, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        second = b"".join(
            struct.pack("<h", int(32767 * 0.14 * math.sin(2 * math.pi * frequency * index / rate)))
            for index in range(rate)
        )
        wav.writeframes(second * 135)
    return stream.getvalue()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare provider-free canonical media delivery evidence.")
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--intake-only", action="store_true")
    args = parser.parse_args(argv)
    print(json.dumps(
        prepare_provider_free_media_delivery(args.runtime_root, assemble=not args.intake_only),
        ensure_ascii=False,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
