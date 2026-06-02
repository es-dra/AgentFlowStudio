from __future__ import annotations

from pathlib import Path

from agentflow_studio.asr_sop import FasterWhisperASRProvider, MockASRProvider, OpenAICompatibleASRProvider
from agentflow_studio.audio_sop import (
    AUDIO_MANIFEST,
    BOUNDARY_SIGNAL_MANIFEST,
    AudioArtifact,
    AudioBoundarySignalConfig,
    AudioExtractionConfig,
    analyze_audio_boundary_signals,
    extract_audio_from_video,
)
from agentflow_studio.schemas import Transcript
from agentflow_studio.utils import write_json
from agentflow_studio.workflow_engine.context import WorkflowContext
from agentflow_studio.workflow_engine.definitions import WorkflowStepDefinition
from agentflow_studio.workflow_engine.node_artifacts import (
    require_input as _require_input,
    require_output as _require_output,
)


def load_video_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    video_ref = _require_input(step, "video")
    video_path = Path(str(context.resolve_input(str(video_ref))))
    if not video_path.is_file():
        raise ValueError(f"video_path does not exist: {video_path}")
    context.state["video_path"] = video_path
    context.state["source_video"] = str(video_path)
    return []


def extract_audio_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    video_path = _state_video_path(context)
    mode = str(_optional_resolved_input(step, context, "audio_extraction_mode") or "ffmpeg")
    config = AudioExtractionConfig(execution_mode=_audio_extraction_mode(mode))
    artifact = extract_audio_from_video(video_path, context.output_dir, config=config)

    context.state["audio_artifact"] = artifact
    context.artifacts["audio_manifest"] = _output_ref(step, "audio_manifest", AUDIO_MANIFEST)
    context.artifacts["audio"] = artifact.audio_path
    if artifact.status == "failed":
        raise ValueError(artifact.error or "audio_extraction_failed")
    return [context.artifacts["audio_manifest"], artifact.audio_path]


def analyze_audio_boundary_signals_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    audio_path = Path(str(_required_artifact_or_input(step, context, "audio")))
    manifest_ref = _output_ref(step, "boundary_signal_manifest", BOUNDARY_SIGNAL_MANIFEST)
    config = AudioBoundarySignalConfig(
        window_sec=_float_parameter_or_default(step, context, "boundary_window_sec", 0.5),
        low_energy_ratio=_float_parameter_or_default(step, context, "boundary_low_energy_ratio", 0.18),
        peak_energy_ratio=_float_parameter_or_default(step, context, "boundary_peak_energy_ratio", 0.75),
    )
    manifest = analyze_audio_boundary_signals(audio_path, context.output_dir, config=config)
    if manifest_ref != BOUNDARY_SIGNAL_MANIFEST:
        write_json(context.output_path(manifest_ref), manifest)
    context.state["boundary_signal_manifest"] = manifest
    context.artifacts["boundary_signal_manifest"] = manifest_ref
    return [manifest_ref]


def transcribe_audio_mock_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    fixture_ref = _require_input(step, "asr_fixture")
    fixture_path = Path(str(context.resolve_input(str(fixture_ref))))
    audio_artifact = _state_audio_artifact(context)
    language = _optional_resolved_input(step, context, "language")
    transcript = MockASRProvider(fixture_path=fixture_path).transcribe(
        audio_artifact,
        language=str(language) if language is not None else None,
    )
    context.state["transcript"] = transcript
    return []


def transcribe_audio_openai_compatible_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    audio_artifact = _state_audio_artifact(context)
    base_url = str(_required_resolved_input(step, context, "base_url"))
    model = str(_required_resolved_input(step, context, "model"))
    api_key = _optional_parameter_input(step, context, "api_key")
    api_key_env = _optional_parameter_input(step, context, "api_key_env")
    timeout_sec = _optional_parameter_input(step, context, "timeout_sec")
    language = _optional_parameter_input(step, context, "language")

    provider = OpenAICompatibleASRProvider(
        base_url=base_url,
        model=model,
        api_key=str(api_key) if api_key is not None else None,
        api_key_env=str(api_key_env) if api_key_env is not None else None,
        timeout_sec=float(timeout_sec) if timeout_sec is not None else 60.0,
    )
    transcript = provider.transcribe(
        audio_artifact,
        language=str(language) if language is not None else None,
    )
    context.state["transcript"] = transcript
    return []


def transcribe_audio_faster_whisper_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    audio_artifact = _state_audio_artifact(context)
    model = _optional_parameter_input(step, context, "model")
    device = _optional_parameter_input(step, context, "device")
    compute_type = _optional_parameter_input(step, context, "compute_type")
    download_root = _optional_parameter_input(step, context, "download_root")
    beam_size = _optional_parameter_input(step, context, "beam_size")
    vad_filter = _optional_parameter_input(step, context, "vad_filter")
    language = _optional_parameter_input(step, context, "language")

    provider = FasterWhisperASRProvider(
        model=str(model) if model is not None else "tiny",
        device=str(device) if device is not None else "cpu",
        compute_type=str(compute_type) if compute_type is not None else "int8",
        download_root=str(download_root) if download_root is not None else None,
        beam_size=int(beam_size) if beam_size is not None else 1,
        vad_filter=_bool_input(vad_filter) if vad_filter is not None else False,
    )
    transcript = provider.transcribe(
        audio_artifact,
        language=str(language) if language is not None else None,
    )
    context.state["transcript"] = transcript
    return []


def write_transcript_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    transcript = _state_transcript(context)
    output_ref = _require_output(step, "transcript")
    write_json(context.output_path(output_ref), transcript)
    context.artifacts["transcript"] = output_ref
    return [output_ref]


def _output_ref(step: WorkflowStepDefinition, name: str, default: str) -> str:
    return step.outputs.get(name, default)


def _optional_resolved_input(
    step: WorkflowStepDefinition,
    context: WorkflowContext,
    name: str,
) -> object | None:
    if name not in step.inputs:
        return None
    value = step.inputs[name]
    if value == name and name not in context.inputs and name not in context.state and name not in context.artifacts:
        return None
    if isinstance(value, str) and value not in context.inputs and value not in context.state and value not in context.artifacts:
        return value
    return context.resolve_input(str(value))


def _required_resolved_input(
    step: WorkflowStepDefinition,
    context: WorkflowContext,
    name: str,
) -> object:
    value = _optional_resolved_input(step, context, name)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError(f"Step {step.id} missing required input: {name}")
    return value


def _required_artifact_or_input(
    step: WorkflowStepDefinition,
    context: WorkflowContext,
    name: str,
) -> object:
    value = _required_resolved_input(step, context, name)
    if isinstance(value, str) and value in context.artifacts:
        return context.resolve_input(value)
    return value


def _optional_parameter_input(
    step: WorkflowStepDefinition,
    context: WorkflowContext,
    name: str,
) -> object | None:
    if name not in step.inputs:
        return None
    value = step.inputs[name]
    if isinstance(value, str) and value not in context.inputs and value not in context.state and value not in context.artifacts:
        return None
    return context.resolve_input(str(value))


def _optional_float_parameter(
    step: WorkflowStepDefinition,
    context: WorkflowContext,
    name: str,
) -> float | None:
    value = _optional_parameter_input(step, context, name)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number") from exc


def _float_parameter_or_default(
    step: WorkflowStepDefinition,
    context: WorkflowContext,
    name: str,
    default: float,
) -> float:
    value = _optional_float_parameter(step, context, name)
    return default if value is None else value


def _state_video_path(context: WorkflowContext) -> Path:
    value = context.state.get("video_path")
    if isinstance(value, Path):
        return value
    raise ValueError("video_path must be loaded before extract_audio")


def _state_audio_artifact(context: WorkflowContext) -> AudioArtifact:
    value = context.state.get("audio_artifact")
    if isinstance(value, AudioArtifact):
        return value
    raise ValueError("audio_artifact must be generated before transcription")


def _state_transcript(context: WorkflowContext) -> Transcript:
    value = context.state.get("transcript")
    if isinstance(value, Transcript):
        return value
    raise ValueError("transcript must be generated before write_transcript")


def _audio_extraction_mode(value: str) -> str:
    text = value.strip().lower()
    if text not in {"ffmpeg", "mock"}:
        raise ValueError("audio_extraction_mode must be ffmpeg or mock")
    return text


def _bool_input(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}
