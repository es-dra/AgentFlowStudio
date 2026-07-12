from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


GENERATION_PATH_CONTRACT_SCHEMA_VERSION = "afs_generation_path_contract.v1"
DEFAULT_VIDEO_GENERATION_PATH = "i2v_first_frame"

GenerationPathId = Literal[
    "t2v",
    "i2v_first_frame",
    "i2v_first_last",
    "reference_video",
    "director_to_keyframe",
    "director_to_video",
]
GenerationPathAdoptionState = Literal["supported", "planned", "blocked"]


@dataclass(frozen=True)
class GenerationPathContract:
    path_id: GenerationPathId
    label: str
    required_inputs: tuple[str, ...]
    optional_inputs: tuple[str, ...]
    input_media_families: tuple[str, ...]
    output_media_family: str
    provider_capability: str
    adoption_state: GenerationPathAdoptionState
    safety_preflight: tuple[str, ...]
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": GENERATION_PATH_CONTRACT_SCHEMA_VERSION,
            "path_id": self.path_id,
            "label": self.label,
            "required_inputs": list(self.required_inputs),
            "optional_inputs": list(self.optional_inputs),
            "allowed_media_families": {
                "inputs": list(self.input_media_families),
                "output": self.output_media_family,
            },
            "provider_capability": self.provider_capability,
            "adoption_state": self.adoption_state,
            "safety_preflight": {
                "checks": list(self.safety_preflight),
                "provider_calls_started": False,
                "media_bytes_required_by_preflight": False,
                "provider_raw_response_required": False,
            },
            "notes": self.notes,
        }


GENERATION_PATH_CONTRACTS: dict[str, GenerationPathContract] = {
    "t2v": GenerationPathContract(
        path_id="t2v",
        label="Text to video",
        required_inputs=("prompt_text",),
        optional_inputs=(
            "optimized_prompt",
            "duration_sec",
            "resolution",
            "aspect_ratio",
            "motion",
            "context_subgraph",
        ),
        input_media_families=("text",),
        output_media_family="video",
        provider_capability="video.t2v",
        adoption_state="planned",
        safety_preflight=(
            "prompt_text_present",
            "generation_path_adoption_state",
            "provider_submit_disabled_until_provider_vertical_exists",
        ),
        notes="Contracted for routing and preflight only; no provider submit path is implemented.",
    ),
    "i2v_first_frame": GenerationPathContract(
        path_id="i2v_first_frame",
        label="Image to video from first frame",
        required_inputs=("prompt_text", "first_frame_image_asset_id"),
        optional_inputs=(
            "optimized_prompt",
            "input_source",
            "duration_sec",
            "resolution",
            "aspect_ratio",
            "motion",
            "context_subgraph",
        ),
        input_media_families=("text", "image"),
        output_media_family="video",
        provider_capability="video.i2v.first_frame",
        adoption_state="supported",
        safety_preflight=(
            "prompt_text_present",
            "first_frame_image_asset_id_present",
            "duration_contract",
            "provider_descriptor_capability",
            "provider_gate_before_submit",
        ),
        notes="Current legacy-compatible video path.",
    ),
    "i2v_first_last": GenerationPathContract(
        path_id="i2v_first_last",
        label="Image to video from first and last frames",
        required_inputs=("prompt_text", "first_frame_image_asset_id", "last_frame_image_asset_id"),
        optional_inputs=(
            "optimized_prompt",
            "input_source",
            "duration_sec",
            "resolution",
            "aspect_ratio",
            "motion",
            "context_subgraph",
        ),
        input_media_families=("text", "image"),
        output_media_family="video",
        provider_capability="video.i2v.first_last_frame",
        adoption_state="supported",
        safety_preflight=(
            "prompt_text_present",
            "first_frame_image_asset_id_present",
            "last_frame_image_asset_id_present",
            "duration_contract",
            "provider_descriptor_capability",
            "provider_gate_before_submit",
        ),
        notes="Runtime supports the contract; provider descriptors may still reject unsupported frame modes.",
    ),
    "reference_video": GenerationPathContract(
        path_id="reference_video",
        label="Reference video to video",
        required_inputs=("prompt_text", "reference_video_artifact_id"),
        optional_inputs=(
            "optimized_prompt",
            "duration_sec",
            "resolution",
            "aspect_ratio",
            "motion",
            "context_subgraph",
        ),
        input_media_families=("text", "video"),
        output_media_family="video",
        provider_capability="video.reference_video",
        adoption_state="blocked",
        safety_preflight=(
            "prompt_text_present",
            "reference_video_artifact_id_present",
            "frontend_safe_reference_only",
            "provider_submit_disabled",
        ),
        notes="Blocked until a frontend-safe reference-video boundary and provider capability exist.",
    ),
    "director_to_keyframe": GenerationPathContract(
        path_id="director_to_keyframe",
        label="Director setup to keyframe",
        required_inputs=("prompt_text", "director_setup"),
        optional_inputs=("optimized_prompt", "context_subgraph", "aspect_ratio"),
        input_media_families=("text", "director"),
        output_media_family="image",
        provider_capability="image.keyframe.director",
        adoption_state="supported",
        safety_preflight=(
            "prompt_text_present",
            "director_setup_present",
            "image_provider_gate_before_submit",
        ),
        notes="Contract describes the existing keyframe-side director path, not the video endpoint.",
    ),
    "director_to_video": GenerationPathContract(
        path_id="director_to_video",
        label="Director setup to video",
        required_inputs=("prompt_text", "director_setup"),
        optional_inputs=(
            "optimized_prompt",
            "duration_sec",
            "resolution",
            "aspect_ratio",
            "motion",
            "context_subgraph",
        ),
        input_media_families=("text", "director"),
        output_media_family="video",
        provider_capability="video.director",
        adoption_state="planned",
        safety_preflight=(
            "prompt_text_present",
            "director_setup_present",
            "generation_path_adoption_state",
            "provider_submit_disabled_until_provider_vertical_exists",
        ),
        notes="Contracted for future director-to-video routing; no provider submit path is implemented.",
    ),
}


def generation_path_contracts() -> dict[str, dict[str, Any]]:
    return {path_id: contract.to_dict() for path_id, contract in GENERATION_PATH_CONTRACTS.items()}


def generation_path_contract(path_id: str) -> dict[str, Any]:
    return _contract(path_id).to_dict()


def video_generation_path_id(request: Any) -> GenerationPathId:
    explicit = str(getattr(request, "generation_path", "") or "").strip()
    if explicit:
        return _contract(explicit).path_id
    if str(getattr(request, "last_frame_image_asset_id", "") or "").strip():
        return "i2v_first_last"
    return DEFAULT_VIDEO_GENERATION_PATH


def video_generation_path_contract(request: Any, *, endpoint_media_family: str = "video") -> dict[str, Any]:
    path_id = video_generation_path_id(request)
    contract = _contract(path_id)
    payload = contract.to_dict()
    preflight = generation_path_preflight(request, endpoint_media_family=endpoint_media_family)
    payload["resolved_from"] = "explicit" if getattr(request, "generation_path", None) else "legacy_projection"
    payload["safety_preflight"].update(
        {
            "endpoint_media_family": endpoint_media_family,
            "provider_submit_allowed": preflight["provider_submit_allowed"],
            "preflight_blocked": preflight["preflight_blocked"],
            "blocks": preflight["blocks"],
        }
    )
    return payload


def generation_path_preflight(request: Any, *, endpoint_media_family: str = "video") -> dict[str, Any]:
    path_id = video_generation_path_id(request)
    contract = _contract(path_id)
    blocks = _input_blocks(request, contract)
    if contract.output_media_family != endpoint_media_family:
        blocks.append(
            _block(
                "generation_path_media_family_mismatch",
                "generation_path",
                path_id=contract.path_id,
                details={
                    "endpoint_media_family": endpoint_media_family,
                    "output_media_family": contract.output_media_family,
                    "provider_capability": contract.provider_capability,
                },
            )
        )
    if contract.adoption_state != "supported":
        blocks.append(
            _block(
                "generation_path_not_supported",
                "generation_path",
                path_id=contract.path_id,
                details={
                    "adoption_state": contract.adoption_state,
                    "provider_capability": contract.provider_capability,
                    "output_media_family": contract.output_media_family,
                },
            )
        )
    return {
        "schema_version": GENERATION_PATH_CONTRACT_SCHEMA_VERSION,
        "path_id": contract.path_id,
        "adoption_state": contract.adoption_state,
        "provider_capability": contract.provider_capability,
        "provider_calls_started": False,
        "provider_submit_allowed": not blocks,
        "preflight_blocked": bool(blocks),
        "blocks": blocks,
    }


def validate_generation_path_request_inputs(request: Any) -> None:
    path_id = video_generation_path_id(request)
    contract = _contract(path_id)
    missing = _missing_required_inputs(request, contract)
    if missing:
        raise ValueError(
            f"generation_path {contract.path_id} missing required input(s): {', '.join(missing)}"
        )


def generation_path_submit_error(request: Any, *, endpoint_media_family: str = "video") -> dict[str, Any] | None:
    preflight = generation_path_preflight(request, endpoint_media_family=endpoint_media_family)
    if not preflight["preflight_blocked"]:
        return None
    first = preflight["blocks"][0]
    return {
        "error": str(first.get("error") or "unsupported_generation_path"),
        "message": "Generation path is not available for provider submit.",
        "stage": "generation_path_preflight",
        "details": {
            "provider_calls_started": False,
            "generation_path": preflight["path_id"],
            "adoption_state": preflight["adoption_state"],
            "provider_capability": preflight["provider_capability"],
            "blocks": preflight["blocks"],
        },
    }


def _contract(path_id: str) -> GenerationPathContract:
    try:
        return GENERATION_PATH_CONTRACTS[path_id]
    except KeyError as exc:
        raise ValueError(f"unknown generation_path: {path_id}") from exc


def _input_blocks(request: Any, contract: GenerationPathContract) -> list[dict[str, Any]]:
    return [
        _block(
            "missing_generation_path_input",
            field,
            path_id=contract.path_id,
            details={"required_input": field, "provider_capability": contract.provider_capability},
        )
        for field in _missing_required_inputs(request, contract)
    ]


def _missing_required_inputs(request: Any, contract: GenerationPathContract) -> list[str]:
    return [field for field in contract.required_inputs if not _has_input(request, field)]


def _has_input(request: Any, field: str) -> bool:
    value = getattr(request, field, None)
    if field == "director_setup":
        return value is not None
    if isinstance(value, str):
        return bool(value.strip())
    return value is not None


def _block(error: str, field: str, *, path_id: str, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "error": error,
        "field": field,
        "stage": "generation_path_preflight",
        "provider_calls_started": False,
        "details": {
            "generation_path": path_id,
            "provider_calls_started": False,
            **details,
        },
    }


__all__ = (
    "DEFAULT_VIDEO_GENERATION_PATH",
    "GENERATION_PATH_CONTRACT_SCHEMA_VERSION",
    "GENERATION_PATH_CONTRACTS",
    "GenerationPathAdoptionState",
    "GenerationPathId",
    "generation_path_contract",
    "generation_path_contracts",
    "generation_path_preflight",
    "generation_path_submit_error",
    "validate_generation_path_request_inputs",
    "video_generation_path_contract",
    "video_generation_path_id",
)
