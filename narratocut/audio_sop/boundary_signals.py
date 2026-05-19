from __future__ import annotations

import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from narratocut.utils import write_json


BOUNDARY_SIGNAL_MANIFEST = "boundary_signal_manifest.json"


@dataclass(frozen=True)
class AudioBoundarySignalConfig:
    window_sec: float = 0.5
    low_energy_ratio: float = 0.18
    peak_energy_ratio: float = 0.75

    def __post_init__(self) -> None:
        if self.window_sec <= 0:
            raise ValueError("window_sec must be greater than 0")
        if not 0 <= self.low_energy_ratio <= 1:
            raise ValueError("low_energy_ratio must be between 0 and 1")
        if not 0 <= self.peak_energy_ratio <= 1:
            raise ValueError("peak_energy_ratio must be between 0 and 1")


def analyze_audio_boundary_signals(
    audio_path: str | Path,
    output_dir: str | Path,
    *,
    config: AudioBoundarySignalConfig | None = None,
) -> dict[str, Any]:
    resolved_config = config or AudioBoundarySignalConfig()
    source = Path(audio_path)
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    if not source.is_file():
        return _write_manifest(
            root,
            _failed_manifest(
                source,
                f"audio_path_missing: {source}",
                resolved_config,
            ),
        )

    try:
        windows, metadata = _read_energy_windows(source, resolved_config)
    except (wave.Error, EOFError, OSError, ValueError) as exc:
        return _write_manifest(
            root,
            _failed_manifest(
                source,
                f"audio_boundary_analysis_failed: {exc}",
                resolved_config,
            ),
        )

    max_rms = max((window["rms"] for window in windows), default=0.0)
    low_energy_windows = [
        window for window in windows if max_rms <= 0 or window["normalized_energy"] <= resolved_config.low_energy_ratio
    ]
    peak_windows = [
        window for window in windows if max_rms > 0 and window["normalized_energy"] >= resolved_config.peak_energy_ratio
    ]
    manifest = {
        "schema_version": "0.1",
        "status": "succeeded",
        "source": "local_audio_boundary_signals",
        "audio_path": str(source),
        "duration_sec": metadata["duration_sec"],
        "sample_rate": metadata["sample_rate"],
        "channels": metadata["channels"],
        "sample_width": metadata["sample_width"],
        "window_sec": resolved_config.window_sec,
        "window_count": len(windows),
        "energy_windows": windows,
        "low_energy_windows": low_energy_windows,
        "peak_windows": peak_windows,
        "boundary_points": _boundary_points(low_energy_windows),
        "warnings": [],
        "errors": [],
        "manifest_path": BOUNDARY_SIGNAL_MANIFEST,
    }
    return _write_manifest(root, manifest)


def _read_energy_windows(
    audio_path: Path,
    config: AudioBoundarySignalConfig,
) -> tuple[list[dict[str, float]], dict[str, float | int]]:
    with wave.open(str(audio_path), "rb") as wav:
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        sample_rate = wav.getframerate()
        frame_count = wav.getnframes()
        if sample_width not in {1, 2, 3, 4}:
            raise ValueError(f"unsupported_sample_width: {sample_width}")
        frames_per_window = max(1, int(round(sample_rate * config.window_sec)))
        duration = frame_count / sample_rate if sample_rate > 0 else 0.0
        windows: list[dict[str, float]] = []
        start_frame = 0
        while start_frame < frame_count:
            requested = min(frames_per_window, frame_count - start_frame)
            chunk = wav.readframes(requested)
            if not chunk:
                break
            rms = _rms(chunk, sample_width)
            windows.append(
                {
                    "start_sec": round(start_frame / sample_rate, 6),
                    "end_sec": round((start_frame + requested) / sample_rate, 6),
                    "rms": round(rms, 6),
                    "normalized_energy": 0.0,
                }
            )
            start_frame += requested
    max_rms = max((window["rms"] for window in windows), default=0.0)
    if max_rms > 0:
        for window in windows:
            window["normalized_energy"] = round(float(window["rms"]) / max_rms, 6)
    return windows, {
        "duration_sec": round(duration, 6),
        "sample_rate": sample_rate,
        "channels": channels,
        "sample_width": sample_width,
    }


def _boundary_points(low_energy_windows: list[dict[str, float]]) -> list[dict[str, float | str]]:
    if not low_energy_windows:
        return []
    points: list[dict[str, float | str]] = []
    group_start = low_energy_windows[0]
    previous = low_energy_windows[0]
    for window in low_energy_windows[1:]:
        if abs(float(window["start_sec"]) - float(previous["end_sec"])) > 0.000001:
            points.extend(_group_boundary_points(group_start, previous))
            group_start = window
        previous = window
    points.extend(_group_boundary_points(group_start, previous))
    return points


def _rms(chunk: bytes, sample_width: int) -> float:
    if not chunk:
        return 0.0
    sample_count = len(chunk) // sample_width
    if sample_count <= 0:
        return 0.0
    square_sum = 0.0
    for index in range(0, sample_count * sample_width, sample_width):
        sample = int.from_bytes(chunk[index : index + sample_width], byteorder="little", signed=True)
        square_sum += float(sample * sample)
    return (square_sum / sample_count) ** 0.5


def _group_boundary_points(
    first: dict[str, float],
    last: dict[str, float],
) -> list[dict[str, float | str]]:
    confidence = _silence_confidence(first, last)
    return [
        {"time_sec": first["start_sec"], "kind": "silence_start", "confidence": confidence},
        {"time_sec": last["end_sec"], "kind": "silence_end", "confidence": confidence},
    ]


def _silence_confidence(first: dict[str, float], last: dict[str, float]) -> float:
    energy = min(float(first["normalized_energy"]), float(last["normalized_energy"]))
    return round(max(0.0, min(1.0, 1.0 - energy)), 6)


def _failed_manifest(
    audio_path: Path,
    error: str,
    config: AudioBoundarySignalConfig,
) -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "status": "failed",
        "source": "local_audio_boundary_signals",
        "audio_path": str(audio_path),
        "duration_sec": None,
        "window_sec": config.window_sec,
        "window_count": 0,
        "energy_windows": [],
        "low_energy_windows": [],
        "peak_windows": [],
        "boundary_points": [],
        "warnings": [],
        "errors": [error],
        "manifest_path": BOUNDARY_SIGNAL_MANIFEST,
    }


def _write_manifest(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    write_json(root / BOUNDARY_SIGNAL_MANIFEST, manifest)
    return manifest
