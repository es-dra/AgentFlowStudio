from __future__ import annotations

import json
import wave
from pathlib import Path

from agentflow_studio.audio_sop import AudioBoundarySignalConfig, analyze_audio_boundary_signals
from agentflow_studio.workflow_engine.definitions import WorkflowStepDefinition
from agentflow_studio.workflow_engine.transcription_nodes import analyze_audio_boundary_signals_node
from agentflow_studio.workflow_engine.context import WorkflowContext


def test_analyze_audio_boundary_signals_detects_low_energy_boundaries(tmp_path: Path) -> None:
    audio_path = tmp_path / "audio.wav"
    _write_mono_wav(audio_path, amplitudes=[9000, 9000, 0, 0, 9000, 9000], sample_rate=100)

    manifest = analyze_audio_boundary_signals(
        audio_path,
        output_dir=tmp_path / "run",
        config=AudioBoundarySignalConfig(window_sec=1.0, low_energy_ratio=0.2),
    )

    assert manifest["status"] == "succeeded"
    assert manifest["audio_path"] == str(audio_path)
    assert manifest["duration_sec"] == 6.0
    assert manifest["window_count"] == 6
    assert manifest["low_energy_windows"] == [
        {"start_sec": 2.0, "end_sec": 3.0, "rms": 0.0, "normalized_energy": 0.0},
        {"start_sec": 3.0, "end_sec": 4.0, "rms": 0.0, "normalized_energy": 0.0},
    ]
    assert manifest["boundary_points"] == [
        {"time_sec": 2.0, "kind": "silence_start", "confidence": 1.0},
        {"time_sec": 4.0, "kind": "silence_end", "confidence": 1.0},
    ]
    assert (tmp_path / "run" / "boundary_signal_manifest.json").is_file()


def test_analyze_audio_boundary_signals_node_writes_manifest(tmp_path: Path) -> None:
    audio_path = tmp_path / "audio.wav"
    _write_mono_wav(audio_path, amplitudes=[8000, 0, 8000], sample_rate=100)
    context = WorkflowContext(
        run_id="run_001",
        workflow_name="test",
        output_dir=tmp_path / "run",
        artifacts={"audio": str(audio_path)},
    )

    artifacts = analyze_audio_boundary_signals_node(
        WorkflowStepDefinition(
            id="analyze_audio_boundary_signals",
            type="analyze_audio_boundary_signals",
            inputs={"audio": "audio", "boundary_window_sec": 1.0},
            outputs={"boundary_signal_manifest": "boundary_signal_manifest.json"},
        ),
        context,
    )

    assert artifacts == ["boundary_signal_manifest.json"]
    assert context.artifacts["boundary_signal_manifest"] == "boundary_signal_manifest.json"
    manifest = json.loads((tmp_path / "run" / "boundary_signal_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "succeeded"
    assert manifest["boundary_points"][0]["time_sec"] == 1.0


def test_analyze_audio_boundary_signals_node_preserves_explicit_zero_threshold(tmp_path: Path) -> None:
    audio_path = tmp_path / "audio.wav"
    _write_mono_wav(audio_path, amplitudes=[8000, 0, 8000], sample_rate=100)
    context = WorkflowContext(
        run_id="run_001",
        workflow_name="test",
        output_dir=tmp_path / "run",
        artifacts={"audio": str(audio_path)},
    )

    analyze_audio_boundary_signals_node(
        WorkflowStepDefinition(
            id="analyze_audio_boundary_signals",
            type="analyze_audio_boundary_signals",
            inputs={
                "audio": "audio",
                "boundary_window_sec": 1.0,
                "boundary_low_energy_ratio": 0,
                "boundary_peak_energy_ratio": 0,
            },
            outputs={"boundary_signal_manifest": "boundary_signal_manifest.json"},
        ),
        context,
    )

    manifest = json.loads((tmp_path / "run" / "boundary_signal_manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["peak_windows"]) == 3


def _write_mono_wav(path: Path, *, amplitudes: list[int], sample_rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        frames = bytearray()
        for amplitude in amplitudes:
            for _ in range(sample_rate):
                frames.extend(int(amplitude).to_bytes(2, byteorder="little", signed=True))
        wav.writeframes(bytes(frames))
