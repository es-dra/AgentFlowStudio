from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import struct
import sys
import tempfile
import wave
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentflow_studio.production.episode_delivery import assemble_episode, sha256_file
from agentflow_studio.production.episode_media_quality import run_episode_technical_qa


SHOT_COUNT = 12
SHOT_SECONDS = 11
EPISODE_SECONDS = SHOT_COUNT * SHOT_SECONDS
COLORS = (
    (27, 38, 59), (52, 78, 112), (117, 76, 98), (170, 92, 72),
    (203, 139, 78), (190, 175, 112), (106, 151, 135), (65, 126, 145),
    (63, 93, 138), (86, 73, 126), (126, 78, 113), (74, 74, 82),
)


def write_controlled_episode_fixture(root: str | Path) -> Path:
    runtime = Path(root).resolve()
    assets = runtime / "inputs"
    assets.mkdir(parents=True, exist_ok=True)
    shots: list[dict[str, Any]] = []
    for index in range(SHOT_COUNT):
        shot_number = index + 1
        shot_id = f"shot-{shot_number:03d}"
        asset_id = f"visual-{shot_number:03d}"
        revision_id = f"{asset_id}-rev-001"
        relative = f"inputs/{shot_id}.ppm"
        _write_ppm(runtime / relative, COLORS[index])
        asset = _asset(asset_id, revision_id, relative, runtime)
        shots.append(
            {
                "shot_id": shot_id,
                "scene_id": f"scene-{index // 3 + 1:02d}",
                "start_seconds": index * SHOT_SECONDS,
                "end_seconds": (index + 1) * SHOT_SECONDS,
                "visual_asset": asset,
                "lineage": {
                    "project_id": "afs-provider-free-proof",
                    "episode_id": "episode-001",
                    "scene_id": f"scene-{index // 3 + 1:02d}",
                    "shot_id": shot_id,
                    "asset_id": asset_id,
                    "revision_id": revision_id,
                },
            }
        )
    audio_ref = "inputs/episode-audio.wav"
    subtitle_ref = "inputs/episode-subtitles.srt"
    _write_wave(runtime / audio_ref, EPISODE_SECONDS)
    _write_subtitles(runtime / subtitle_ref)
    spec = {
        "schema_version": "0.1.0",
        "project_id": "afs-provider-free-proof",
        "episode_id": "episode-001",
        "duration_seconds": EPISODE_SECONDS,
        "frame_rate": 6,
        "provider_calls_started": 0,
        "shots": shots,
        "audio_asset": _asset("episode-audio", "episode-audio-rev-001", audio_ref, runtime),
        "subtitle_asset": _asset("episode-subtitles", "episode-subtitles-rev-001", subtitle_ref, runtime),
    }
    spec_path = runtime / "episode_spec.json"
    _write_json(spec_path, spec)
    return spec_path


def run_harness(
    runtime_root: str | Path,
    *,
    ffmpeg_executable: str = "ffmpeg",
    ffprobe_executable: str = "ffprobe",
) -> dict[str, Any]:
    root = Path(runtime_root).resolve()
    spec_path = write_controlled_episode_fixture(root)
    output = root / "delivery"
    delivery = assemble_episode(spec_path, output, ffmpeg_executable=ffmpeg_executable)
    qa = run_episode_technical_qa(
        delivery["episode"], delivery["manifest"],
        ffprobe_executable=ffprobe_executable, ffmpeg_executable=ffmpeg_executable,
    )
    qa_path = output / "technical_qa.json"
    _write_json(qa_path, qa)
    manifest = json.loads(delivery["manifest"].read_text(encoding="utf-8"))
    return {
        "status": "pass" if qa["status"] == "pass" else "fail",
        "runtime_root": str(root),
        "cleanup_state": "retained_for_independent_evaluation",
        "episode_path": str(delivery["episode"]),
        "manifest_path": str(delivery["manifest"]),
        "manifest_sha256": sha256_file(delivery["manifest"]),
        "technical_qa_path": str(qa_path),
        "episode_sha256": manifest["episode_sha256"],
        "duration_seconds": manifest["duration_seconds"],
        "stream_types": sorted({stream.get("codec_type") for stream in qa["probe"].get("streams", [])}),
        "shot_count": len(manifest["shot_timeline"]),
        "provider_calls_started": 0,
        "technical_qa": qa["status"],
        "evidence_layers": {
            "runtime_media_structure": "verified" if qa["status"] == "pass" else "failed",
            "technical_media_qa": qa["status"],
            "creative_media_quality": "not_evaluated",
            "human_acceptance": "not_evaluated",
            "business_validation": "not_evaluated",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a provider-free 132 second episode delivery proof.")
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--ffprobe", default="ffprobe")
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args(argv)
    root = args.runtime_root or Path(tempfile.mkdtemp(prefix="afs-episode-delivery-"))
    result = run_harness(root, ffmpeg_executable=args.ffmpeg, ffprobe_executable=args.ffprobe)
    if args.cleanup:
        shutil.rmtree(root)
        result["cleanup_state"] = "cleaned_after_verification"
        result["runtime_root"] = None
        result["episode_path"] = None
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


def _asset(asset_id: str, revision_id: str, relative: str, root: Path) -> dict[str, str]:
    return {
        "asset_id": asset_id,
        "revision_id": revision_id,
        "current_revision_id": revision_id,
        "path": relative,
        "sha256": sha256_file(root / relative),
    }


def _write_ppm(path: Path, color: tuple[int, int, int]) -> None:
    width, height = 320, 180
    header = f"P6\n{width} {height}\n255\n".encode("ascii")
    path.write_bytes(header + bytes(color) * width * height)


def _write_wave(path: Path, seconds: int) -> None:
    sample_rate = 8000
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(sample_rate)
        frames = bytearray()
        for index in range(seconds * sample_rate):
            phase = index / sample_rate
            frequency = 196 + 24 * int(phase // SHOT_SECONDS % 4)
            sample = int(3200 * math.sin(2 * math.pi * frequency * phase))
            frames.extend(struct.pack("<h", sample))
        stream.writeframes(frames)


def _write_subtitles(path: Path) -> None:
    blocks = []
    for index in range(SHOT_COUNT):
        start, end = index * SHOT_SECONDS, (index + 1) * SHOT_SECONDS
        blocks.append(f"{index + 1}\n{_srt_time(start)} --> {_srt_time(end)}\nEpisode proof shot {index + 1:02d}\n")
    path.write_text("\n".join(blocks), encoding="utf-8")


def _srt_time(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},000"


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
