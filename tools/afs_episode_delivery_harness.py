from __future__ import annotations

import argparse
import json
import math
import shutil
import struct
import subprocess
import sys
import tempfile
import wave
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentflow_studio.production.episode_delivery import assemble_episode, sha256_file
from agentflow_studio.production.episode_media_quality import run_episode_technical_qa


SHOT_COUNT = 15
SHOT_SECONDS = 9
EPISODE_SECONDS = SHOT_COUNT * SHOT_SECONDS
WIDTH = 640
HEIGHT = 360
FRAME_RATE = 12
SAMPLE_RATE = 16_000


def write_controlled_episode_fixture(
    root: str | Path,
    *,
    ffmpeg_executable: str = "ffmpeg",
) -> Path:
    runtime = Path(root).resolve()
    assets = runtime / "inputs"
    assets.mkdir(parents=True, exist_ok=True)
    image_ref = "inputs/synthetic-pattern.ppm"
    video_ref = "inputs/synthetic-moving-pattern.mp4"
    _write_pattern_ppm(runtime / image_ref)
    _write_moving_pattern_video(runtime / video_ref, ffmpeg_executable)

    shots: list[dict[str, Any]] = []
    for index in range(SHOT_COUNT):
        shot_number = index + 1
        shot_id = f"shot-{shot_number:03d}"
        media_type = "image" if index % 3 == 0 else "video"
        asset_id = f"visual-{shot_number:03d}-{media_type}"
        revision_id = f"{asset_id}-rev-001"
        relative = image_ref if media_type == "image" else video_ref
        asset = _asset(asset_id, revision_id, relative, runtime, media_type=media_type)
        shots.append(
            {
                "shot_id": shot_id,
                "scene_id": f"scene-{index // 5 + 1:02d}",
                "start_seconds": index * SHOT_SECONDS,
                "end_seconds": (index + 1) * SHOT_SECONDS,
                "source_start_seconds": 0,
                "visual_asset": asset,
                "lineage": {
                    "project_id": "afs-provider-free-engine-proof",
                    "episode_id": "episode-engine-001",
                    "scene_id": f"scene-{index // 5 + 1:02d}",
                    "shot_id": shot_id,
                    "asset_id": asset_id,
                    "revision_id": revision_id,
                },
            }
        )

    dialogue_ref = "inputs/dialogue-stem.wav"
    music_ref = "inputs/music-stem.wav"
    sfx_ref = "inputs/sfx-stem.wav"
    subtitle_ref = "inputs/episode-subtitles.srt"
    _write_stem(runtime / dialogue_ref, "dialogue")
    _write_stem(runtime / music_ref, "music")
    _write_stem(runtime / sfx_ref, "sfx")
    _write_subtitles(runtime / subtitle_ref)
    spec = {
        "schema_version": "0.2.0",
        "contract": "agentflow_studio.production.episode_delivery.v0.1",
        "project_id": "afs-provider-free-engine-proof",
        "episode_id": "episode-engine-001",
        "duration_seconds": EPISODE_SECONDS,
        "shot_count": SHOT_COUNT,
        "frame_rate": FRAME_RATE,
        "width": WIDTH,
        "height": HEIGHT,
        "minimum_video_bitrate": 150_000,
        "provider_calls_started": 0,
        "shots": shots,
        "audio_stems": {
            "dialogue": _asset("dialogue-stem", "dialogue-stem-rev-001", dialogue_ref, runtime),
            "music": _asset("music-stem", "music-stem-rev-001", music_ref, runtime),
            "sfx": _asset("sfx-stem", "sfx-stem-rev-001", sfx_ref, runtime),
        },
        "subtitle_asset": _asset("episode-subtitles", "episode-subtitles-rev-001", subtitle_ref, runtime),
        "mix": {"target_lufs": -16, "true_peak_db": -1, "music_duck_db": 5},
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
    spec_path = write_controlled_episode_fixture(root, ffmpeg_executable=ffmpeg_executable)
    output = root / "delivery"
    delivery = assemble_episode(
        spec_path,
        output,
        ffmpeg_executable=ffmpeg_executable,
        ffprobe_executable=ffprobe_executable,
    )
    qa = run_episode_technical_qa(
        delivery["episode"], delivery["manifest"],
        ffprobe_executable=ffprobe_executable, ffmpeg_executable=ffmpeg_executable,
    )
    qa_path = output / "technical_qa.json"
    _write_json(qa_path, qa)
    manifest = json.loads(delivery["manifest"].read_text(encoding="utf-8"))
    media_types = sorted({shot["media_type"] for shot in manifest["shot_timeline"]})
    qa_details = {check["name"]: check.get("details", {}) for check in qa["checks"]}
    return {
        "status": "pass" if qa["status"] == "pass" else "fail",
        "evidence_label": "representative_episode_assembly_engine_pass" if qa["status"] == "pass" else "technical_media_qa_fail",
        "runtime_root": str(root),
        "cleanup_state": "retained_for_independent_evaluation",
        "episode_path": str(delivery["episode"]),
        "manifest_path": str(delivery["manifest"]),
        "manifest_sha256": sha256_file(delivery["manifest"]),
        "technical_qa_path": str(qa_path),
        "episode_sha256": manifest["episode_sha256"],
        "episode_bytes": manifest["episode_bytes"],
        "duration_seconds": manifest["duration_seconds"],
        "stream_types": sorted({stream.get("codec_type") for stream in qa["probe"].get("streams", [])}),
        "shot_count": len(manifest["shot_timeline"]),
        "visual_input_types": media_types,
        "audio_stems": sorted(manifest["audio_stem_lineage"]),
        "provider_calls_started": 0,
        "technical_qa": qa["status"],
        "output_profile": manifest["output_profile"],
        "mix": manifest["mix"],
        "technical_signals": {
            name: qa_details.get(name, {})
            for name in (
                "video_bitrate_floor", "no_long_black_segments", "no_long_frozen_segments",
                "audio_integrated_loudness_bound", "audio_true_peak_bound", "no_long_audio_silence",
                "subtitle_bounds_and_shot_sync", "shot_cut_keyframes_match_plan",
            )
        },
        "evidence_layers": {
            "technical_media_assembly": "verified" if qa["status"] == "pass" else "failed",
            "technical_media_qa": qa["status"],
            "representative_content_proof": "not_evaluated",
            "creative_media_quality": "not_evaluated",
            "human_acceptance": "not_evaluated",
            "business_validation": "not_evaluated",
            "release_evidence": "not_evaluated",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a provider-free 135 second mixed-media assembly engine proof.")
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--ffprobe", default="ffprobe")
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args(argv)
    root = args.runtime_root or Path(tempfile.mkdtemp(prefix="afs-episode-engine-"))
    result = run_harness(root, ffmpeg_executable=args.ffmpeg, ffprobe_executable=args.ffprobe)
    if args.cleanup:
        shutil.rmtree(root)
        result["cleanup_state"] = "cleaned_after_verification"
        result["runtime_root"] = None
        result["episode_path"] = None
        result["manifest_path"] = None
        result["technical_qa_path"] = None
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


def _asset(
    asset_id: str,
    revision_id: str,
    relative: str,
    root: Path,
    *,
    media_type: str | None = None,
) -> dict[str, str]:
    value = {
        "asset_id": asset_id,
        "revision_id": revision_id,
        "current_revision_id": revision_id,
        "path": relative,
        "sha256": sha256_file(root / relative),
    }
    if media_type:
        value["media_type"] = media_type
    return value


def _write_pattern_ppm(path: Path) -> None:
    header = f"P6\n{WIDTH} {HEIGHT}\n255\n".encode("ascii")
    pixels = bytearray()
    for y in range(HEIGHT):
        for x in range(WIDTH):
            checker = 45 if (x // 32 + y // 32) % 2 else 0
            pixels.extend(((x * 255 // WIDTH + checker) % 256, (y * 255 // HEIGHT + 35) % 256, (x + y + 80) % 256))
    path.write_bytes(header + pixels)


def _write_moving_pattern_video(path: Path, executable: str) -> None:
    command = [
        executable, "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", f"testsrc2=size={WIDTH}x{HEIGHT}:rate={FRAME_RATE}:duration=12",
        "-vf", r"drawbox=x=mod(t*90\,w+120)-120:y=40:w=120:h=80:color=yellow@0.75:t=fill",
        "-an", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-threads", "1", "-map_metadata", "-1", "-metadata", "creation_time=2000-01-01T00:00:00Z",
        str(path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"synthetic moving pattern generation failed: {(result.stderr or '').strip()[-1000:]}")


def _write_stem(path: Path, stem: str) -> None:
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(SAMPLE_RATE)
        chunk = bytearray()
        for index in range(EPISODE_SECONDS * SAMPLE_RATE):
            time = index / SAMPLE_RATE
            if stem == "dialogue":
                active = (time % SHOT_SECONDS) < 5.8
                sample = 7600 * math.sin(2 * math.pi * (210 + int(time // SHOT_SECONDS) * 3) * time) if active else 0
            elif stem == "music":
                sample = 3600 * (
                    math.sin(2 * math.pi * 110 * time) + 0.45 * math.sin(2 * math.pi * 165 * time)
                )
            else:
                pulse = time % SHOT_SECONDS
                sample = 6200 * math.sin(2 * math.pi * 520 * time) * math.exp(-5 * pulse) if pulse < 1.2 else 0
            chunk.extend(struct.pack("<h", max(-32768, min(32767, int(sample)))))
            if len(chunk) >= 128 * 1024:
                stream.writeframesraw(chunk)
                chunk.clear()
        if chunk:
            stream.writeframesraw(chunk)


def _write_subtitles(path: Path) -> None:
    blocks = []
    for index in range(SHOT_COUNT):
        start, end = index * SHOT_SECONDS, (index + 1) * SHOT_SECONDS
        blocks.append(f"{index + 1}\n{_srt_time(start)} --> {_srt_time(end)}\nSynthetic engine proof shot {index + 1:02d}\n")
    path.write_text("\n".join(blocks), encoding="utf-8")


def _srt_time(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},000"


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
