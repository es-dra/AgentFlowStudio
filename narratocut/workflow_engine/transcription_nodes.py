from __future__ import annotations

from pathlib import Path

from narratocut.asr_sop import MockASRProvider, OpenAICompatibleASRProvider
from narratocut.audio_sop import AUDIO_MANIFEST, AudioArtifact, AudioExtractionConfig, extract_audio_from_video
from narratocut.schemas import Transcript
from narratocut.utils import write_json
from narratocut.workflow_engine.context import WorkflowContext
from narratocut.workflow_engine.definitions import WorkflowStepDefinition


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


def write_transcript_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    transcript = _state_transcript(context)
    output_ref = _require_output(step, "transcript")
    write_json(context.output_path(output_ref), transcript)
    context.artifacts["transcript"] = output_ref
    return [output_ref]


def _require_input(step: WorkflowStepDefinition, name: str) -> object:
    if name not in step.inputs:
        raise ValueError(f"Step {step.id} missing required input: {name}")
    return step.inputs[name]


def _require_output(step: WorkflowStepDefinition, name: str) -> str:
    if name not in step.outputs:
        raise ValueError(f"Step {step.id} missing required output: {name}")
    return step.outputs[name]


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
    if value == name and name not in context.inputs and name not in context.state:
        return None
    if isinstance(value, str) and value not in context.inputs and value not in context.state:
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
