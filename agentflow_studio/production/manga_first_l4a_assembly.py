from __future__ import annotations

import json
import subprocess
from decimal import Decimal
from pathlib import Path
from typing import Any

from agentflow_studio.production.manga_first_l4a_schema import (
    TARGET_MAX_SECONDS,
    TARGET_MIN_SECONDS,
    MangaFirstError,
    decimal_string,
    json_digest,
    read_json_object,
    sha256_file,
    variable_schedule,
    write_json_atomic,
)


def compose_legacy_fixture_silent_assembly(
    *,
    l1_root: str | Path,
    l3_root: str | Path,
    output_dir: str | Path,
    target_duration_seconds: Decimal | int | str = Decimal("120.000"),
    ffmpeg_executable: str = "ffmpeg",
    ffprobe_executable: str = "ffprobe",
) -> dict[str, Any]:
    l1 = Path(l1_root)
    l3 = Path(l3_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    target = Decimal(str(target_duration_seconds)).quantize(Decimal("0.001"))
    source_videos = tuple(l1 / "media" / "videos" / f"shot-{index:03d}.mp4" for index in range(1, 14))
    missing = [str(path) for path in source_videos if not path.is_file()]
    if missing:
        raise MangaFirstError(f"legacy fixture videos are missing: {missing[:3]}")
    schedule = variable_schedule(
        count=len(source_videos),
        target_seconds=target,
        source_max_seconds=Decimal("10.041667"),
    )
    episode_path = out / "manga_first_l4a_fixture_silent_assembly.mp4"
    result = subprocess.run(
        _silent_concat_command(source_videos, schedule, episode_path, ffmpeg_executable=ffmpeg_executable),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "ffmpeg failed")[-3000:])
    probe = _ffprobe(episode_path, ffprobe_executable)
    video_streams = [item for item in probe.get("streams", []) if item.get("codec_type") == "video"]
    audio_streams = [item for item in probe.get("streams", []) if item.get("codec_type") == "audio"]
    if len(video_streams) != 1 or audio_streams:
        raise MangaFirstError("silent assembly must contain exactly one video stream and no audio")
    duration = Decimal(str(probe.get("format", {}).get("duration", "0"))).quantize(Decimal("0.001"))
    if duration < TARGET_MIN_SECONDS or duration > TARGET_MAX_SECONDS:
        raise MangaFirstError("silent assembly duration must stay inside 90 to 120 seconds")
    p1 = _l3_p1_findings(l3)
    timeline = _fixture_timeline(source_videos, schedule)
    manifest = _assembly_manifest(episode_path, duration, timeline, p1)
    manifest_path = out / "lineage_manifest.json"
    timeline_path = out / "timeline_manifest.json"
    qa_path = out / "technical_qa.json"
    projection_path = out / "studio_demo_projection.json"
    write_json_atomic(manifest_path, manifest)
    write_json_atomic(timeline_path, {"timeline": timeline, "timeline_sha256": json_digest(timeline)})
    write_json_atomic(
        qa_path,
        {
            "schema_version": "afs.manga_first_l4a.technical_qa.v0.1",
            "ffprobe": probe,
            "full_ffmpeg_decode_ok": _decode_ok(episode_path, ffmpeg_executable),
            "no_audio": True,
            "episode_sha256": manifest["episode_sha256"],
            "lineage_manifest_sha256": sha256_file(manifest_path),
            "provider_dispatch_count": 0,
        },
    )
    write_json_atomic(projection_path, _fixture_studio_projection(episode_path, manifest, p1))
    return {
        "episode_path": episode_path,
        "episode_sha256": manifest["episode_sha256"],
        "manifest_path": manifest_path,
        "manifest_sha256": sha256_file(manifest_path),
        "timeline_path": timeline_path,
        "technical_qa_path": qa_path,
        "studio_projection_path": projection_path,
        "duration_seconds": manifest["duration_seconds"],
        "p1_count": len(p1),
        "provider_dispatch_count": 0,
    }


def _fixture_timeline(
    source_videos: tuple[Path, ...],
    schedule: tuple[tuple[Decimal, Decimal], ...],
) -> list[dict[str, Any]]:
    return [
        {
            "shot_id": f"shot-{index + 1:03d}",
            "source_path": str(source_videos[index]),
            "source_sha256": sha256_file(source_videos[index]),
            "start_seconds": decimal_string(start),
            "end_seconds": decimal_string(end),
            "duration_seconds": decimal_string(end - start),
            "source_in_seconds": "0.000",
            "source_out_seconds": decimal_string(end - start),
        }
        for index, (start, end) in enumerate(schedule)
    ]


def _assembly_manifest(
    episode_path: Path,
    duration: Decimal,
    timeline: list[dict[str, Any]],
    p1: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "schema_version": "afs.manga_first_l4a.silent_fixture_assembly.v0.1",
        "artifact_type": "provider_free_silent_fixture_regression",
        "episode_path": str(episode_path),
        "episode_sha256": sha256_file(episode_path),
        "episode_bytes": episode_path.stat().st_size,
        "duration_seconds": decimal_string(duration),
        "shot_count": len(timeline),
        "provider_dispatch_count": 0,
        "audio_stream_count": 0,
        "manual_editing_required": False,
        "timeline": timeline,
        "lineage_manifest_contract": "afs.lineage-manifest.v0.1",
        "p1_preserved": p1,
        "verdict": "fixture_regression_only_p1_open",
        "non_claims": [
            "not_final_manga_first_delivery",
            "not_visual_creative_qa_pass",
            "not_human_acceptance",
            "not_business_validation",
        ],
    }


def _fixture_studio_projection(episode_path: Path, manifest: dict[str, Any], p1: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "schema_version": "afs.manga_first_l4a.studio_demo_projection.v0.1",
        "project_id": "real-story-20260717T143658Z-6ea4fbee",
        "truth_source": "legacy_recovery_fixture_regression_only",
        "final_demo": {
            "status": "technical_silent_assembly_ready",
            "preview_artifact": {
                "artifact_type": "provider_free_silent_fixture_regression",
                "filename": episode_path.name,
                "sha256": manifest["episode_sha256"],
                "role": "silent_fixture_regression_preview",
            },
            "sha256": manifest["episode_sha256"],
            "duration_seconds": manifest["duration_seconds"],
            "audio_status": "no_audio",
        },
        "qa": {
            "technical_QA": "passed",
            "visual_creative_QA": "P1_open_from_L3",
            "p1_count": len(p1),
            "p1_findings": p1,
        },
        "non_claims": manifest["non_claims"],
    }


def _l3_p1_findings(l3: Path) -> list[dict[str, str]]:
    l3_eval = read_json_object(l3 / "visual_creative_evaluation.json")
    return [
        {"id": item["id"], "title": item["title"]}
        for item in l3_eval.get("findings", [])
        if item.get("severity") == "P1"
    ]


def _silent_concat_command(
    source_videos: tuple[Path, ...],
    schedule: tuple[tuple[Decimal, Decimal], ...],
    output_path: Path,
    *,
    ffmpeg_executable: str,
) -> list[str]:
    command = [ffmpeg_executable, "-hide_banner", "-loglevel", "error", "-y"]
    filters: list[str] = []
    labels: list[str] = []
    for index, (path, (start, end)) in enumerate(zip(source_videos, schedule)):
        duration = end - start
        command.extend(["-ss", "0", "-t", decimal_string(duration), "-i", str(path)])
        label = f"v{index}"
        filters.append(
            f"[{index}:v]scale=1280:720:force_original_aspect_ratio=increase,"
            f"crop=1280:720,fps=24,trim=duration={decimal_string(duration)},"
            f"setpts=PTS-STARTPTS,setsar=1,format=yuv420p[{label}]"
        )
        labels.append(f"[{label}]")
    filters.append(f"{''.join(labels)}concat=n={len(labels)}:v=1:a=0[outv]")
    command.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[outv]",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "22",
            "-pix_fmt",
            "yuv420p",
            "-r",
            "24",
            "-threads",
            "1",
            "-map_metadata",
            "-1",
            "-map_chapters",
            "-1",
            "-metadata",
            "creation_time=2000-01-01T00:00:00Z",
            str(output_path),
        ]
    )
    return command


def _ffprobe(path: Path, ffprobe_executable: str) -> dict[str, Any]:
    result = subprocess.run(
        [
            ffprobe_executable,
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=index,codec_type,codec_name,avg_frame_rate,nb_frames,width,height",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "ffprobe failed")[-1000:])
    return json.loads(result.stdout)


def _decode_ok(path: Path, ffmpeg_executable: str) -> bool:
    result = subprocess.run(
        [ffmpeg_executable, "-v", "error", "-i", str(path), "-f", "null", "-"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0
