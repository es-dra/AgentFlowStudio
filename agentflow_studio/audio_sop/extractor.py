from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from agentflow_studio.audio_sop.metadata import AUDIO_MANIFEST, AudioArtifact
from agentflow_studio.utils import write_json


@dataclass(frozen=True)
class AudioExtractionConfig:
    ffmpeg_executable: str = "ffmpeg"
    audio_dir: str = "audio"
    output_filename: str = "audio.wav"
    overwrite: bool = True
    sample_rate: int = 16000
    channels: int = 1
    codec: str = "pcm_s16le"
    execution_mode: Literal["ffmpeg", "mock"] = "ffmpeg"

    def __post_init__(self) -> None:
        if not self.ffmpeg_executable.strip():
            raise ValueError("ffmpeg_executable must not be empty")
        if self.sample_rate <= 0:
            raise ValueError("sample_rate must be greater than 0")
        if self.channels <= 0:
            raise ValueError("channels must be greater than 0")
        if not self.codec.strip():
            raise ValueError("codec must not be empty")
        if self.execution_mode not in {"ffmpeg", "mock"}:
            raise ValueError("execution_mode must be ffmpeg or mock")
        _validate_safe_relative_path(self.audio_dir, "audio_dir")
        _validate_output_filename(self.output_filename)


def build_ffmpeg_audio_extract_command(
    input_video: str | Path,
    output_audio: str | Path,
    config: AudioExtractionConfig | None = None,
) -> list[str]:
    resolved_config = config or AudioExtractionConfig()
    overwrite_flag = "-y" if resolved_config.overwrite else "-n"
    return [
        resolved_config.ffmpeg_executable,
        overwrite_flag,
        "-i",
        str(Path(input_video)),
        "-vn",
        "-acodec",
        resolved_config.codec,
        "-ar",
        str(resolved_config.sample_rate),
        "-ac",
        str(resolved_config.channels),
        str(Path(output_audio)),
    ]


def extract_audio_from_video(
    input_video: str | Path,
    output_dir: str | Path,
    config: AudioExtractionConfig | None = None,
) -> AudioArtifact:
    resolved_config = config or AudioExtractionConfig()
    source = Path(input_video)
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    audio_ref = Path(resolved_config.audio_dir) / resolved_config.output_filename
    audio_path = root / audio_ref

    if not source.is_file():
        return _write_artifact(
            root,
            AudioArtifact(
                source_video=str(source),
                audio_path=_display_ref(audio_ref),
                status="failed",
                extraction_mode=resolved_config.execution_mode,
                sample_rate=resolved_config.sample_rate,
                channels=resolved_config.channels,
                codec=resolved_config.codec,
                error=f"input_video_missing: {source}",
                metadata=_execution_metadata(executed=False),
            ),
        )

    if resolved_config.execution_mode == "mock":
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        audio_path.write_text(
            "\n".join(
                [
                    "AgentFlow Studio mock audio artifact",
                    f"source_video={source}",
                    f"sample_rate={resolved_config.sample_rate}",
                    f"channels={resolved_config.channels}",
                    f"codec={resolved_config.codec}",
                ]
            ),
            encoding="utf-8",
        )
        return _write_artifact(
            root,
            AudioArtifact(
                source_video=str(source),
                audio_path=_display_ref(audio_ref),
                status="mocked",
                extraction_mode="mock",
                sample_rate=resolved_config.sample_rate,
                channels=resolved_config.channels,
                codec=resolved_config.codec,
                metadata=_execution_metadata(executed=False, audio_path=audio_path),
            ),
        )

    audio_path.parent.mkdir(parents=True, exist_ok=True)
    command = build_ffmpeg_audio_extract_command(
        input_video=source,
        output_audio=audio_path,
        config=resolved_config,
    )
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return _write_artifact(
            root,
            _failed_artifact(
                source,
                audio_ref,
                resolved_config,
                f"ffmpeg_executable_not_found: {resolved_config.ffmpeg_executable}",
                metadata=_execution_metadata(executed=False, command=command, audio_path=audio_path),
            ),
        )
    except OSError as exc:
        return _write_artifact(
            root,
            _failed_artifact(
                source,
                audio_ref,
                resolved_config,
                f"ffmpeg_execution_failed: {exc}",
                metadata=_execution_metadata(executed=True, command=command, audio_path=audio_path, error=str(exc)),
            ),
        )

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        error = f"ffmpeg_audio_extract_failed_exit_{result.returncode}"
        if detail:
            error = f"{error}: {detail}"
        return _write_artifact(
            root,
            _failed_artifact(
                source,
                audio_ref,
                resolved_config,
                error,
                metadata=_execution_metadata(
                    executed=True,
                    command=command,
                    audio_path=audio_path,
                    returncode=result.returncode,
                    stdout=result.stdout,
                    stderr=result.stderr,
                ),
            ),
        )

    return _write_artifact(
        root,
        AudioArtifact(
            source_video=str(source),
            audio_path=_display_ref(audio_ref),
            status="succeeded",
            extraction_mode="ffmpeg",
            sample_rate=resolved_config.sample_rate,
            channels=resolved_config.channels,
            codec=resolved_config.codec,
            metadata=_execution_metadata(
                executed=True,
                command=command,
                audio_path=audio_path,
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
            ),
        ),
    )


def _failed_artifact(
    source: Path,
    audio_ref: Path,
    config: AudioExtractionConfig,
    error: str,
    metadata: dict[str, object] | None = None,
) -> AudioArtifact:
    return AudioArtifact(
        source_video=str(source),
        audio_path=_display_ref(audio_ref),
        status="failed",
        extraction_mode=config.execution_mode,
        sample_rate=config.sample_rate,
        channels=config.channels,
        codec=config.codec,
        error=error,
        metadata=metadata or _execution_metadata(executed=False),
    )


def _write_artifact(root: Path, artifact: AudioArtifact) -> AudioArtifact:
    write_json(root / AUDIO_MANIFEST, artifact.to_dict())
    return artifact


def _validate_safe_relative_path(value: str, name: str) -> None:
    path = Path(value)
    if not value.strip() or path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{name} must be a safe relative path")


def _validate_output_filename(value: str) -> None:
    path = Path(value)
    if not value.strip() or path.is_absolute() or ".." in path.parts or len(path.parts) != 1:
        raise ValueError("output_filename must be a safe filename")


def _display_ref(path: str | Path) -> str:
    return str(path).replace("\\", "/")


def _execution_metadata(
    *,
    executed: bool,
    command: list[str] | None = None,
    audio_path: Path | None = None,
    returncode: int | None = None,
    stdout: str | None = None,
    stderr: str | None = None,
    error: str | None = None,
) -> dict[str, object]:
    metadata: dict[str, object] = {
        "executed": executed,
        "ffmpeg_command": command or [],
    }
    if audio_path is not None:
        metadata["absolute_audio_path"] = str(audio_path)
    if returncode is not None:
        metadata["returncode"] = returncode
    if stdout is not None:
        metadata["stdout"] = stdout
    if stderr is not None:
        metadata["stderr"] = stderr
    if error is not None:
        metadata["error"] = error
    return metadata
