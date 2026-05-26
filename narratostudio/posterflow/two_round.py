from __future__ import annotations

from typing import Any

from narratostudio.posterflow.schemas import (
    ContextBundle,
    NextRoundPrompt,
    PosterCandidatesManifest,
    PosterMemoryCandidates,
    PosterModelInvocations,
    PosterPreferenceProfile,
    PosterPromptPack,
)


def build_round_2_prompt_pack(
    previous_prompt: PosterPromptPack,
    next_prompt: NextRoundPrompt,
) -> PosterPromptPack:
    memory_refs = list(next_prompt.memory_context.get("memory_refs", []))
    return PosterPromptPack(
        project_id=next_prompt.project_id,
        run_id=next_prompt.new_run_id,
        prompt_id=f"{next_prompt.new_run_id}_poster_prompt_001",
        target_model_family=previous_prompt.target_model_family,
        prompt_language=previous_prompt.prompt_language,
        positive_prompt=next_prompt.composed_positive_prompt,
        negative_prompt=next_prompt.composed_negative_prompt,
        prompt_sections={
            **previous_prompt.prompt_sections,
            "memory_context": ", ".join(memory_refs),
            "task_delta": str(next_prompt.task_delta),
        },
        model_params=dict(previous_prompt.model_params),
        context_usage={
            "project_prefix_used": True,
            "preference_profile_used": True,
            "context_bundle_used": bool(next_prompt.memory_context.get("context_bundle_path")),
            "memory_refs": memory_refs,
            "context_bundle_path": next_prompt.memory_context.get("context_bundle_path"),
            "cache_key": next_prompt.memory_context.get("cache_key"),
        },
        source_refs={
            "previous_prompt_pack": "poster_prompt_pack.json",
            "next_round_prompt": "next_round_prompt.json",
            "preference_profile": "poster_preference_profile.json",
            "context_bundle": str(next_prompt.memory_context.get("context_bundle_path") or ""),
        },
    )


def prefix_candidate_paths(
    manifest: PosterCandidatesManifest,
    invocations: PosterModelInvocations,
    *,
    path_prefix: str,
) -> tuple[PosterCandidatesManifest, PosterModelInvocations]:
    prefix = path_prefix.strip("/\\")
    candidates = [
        candidate.model_copy(update={"image_path": f"{prefix}/{candidate.image_path}"})
        for candidate in manifest.candidates
    ]
    prefixed_invocations = [
        invocation.model_copy(
            update={"output_files": [f"{prefix}/{path}" for path in invocation.output_files]}
        )
        for invocation in invocations.invocations
    ]
    return (
        manifest.model_copy(
            update={
                "candidates": candidates,
                "source_refs": {
                    **manifest.source_refs,
                    "poster_prompt_pack": f"{prefix}/poster_prompt_pack.json",
                    "round_dir": prefix,
                    "next_round_prompt": "next_round_prompt.json",
                },
            }
        ),
        invocations.model_copy(update={"invocations": prefixed_invocations}),
    )


def build_round_comparison(
    *,
    round_1_manifest: PosterCandidatesManifest,
    round_2_manifest: PosterCandidatesManifest,
    memory: PosterMemoryCandidates,
    profile: PosterPreferenceProfile,
    next_prompt: NextRoundPrompt,
    context_bundle: ContextBundle | None,
) -> dict[str, Any]:
    return {
        "schema_version": "0.1.0",
        "artifact_type": "poster_round_comparison",
        "project_id": profile.project_id,
        "round_1": _round_summary(round_1_manifest),
        "round_2": _round_summary(round_2_manifest),
        "memory_reuse": {
            "preference_profile_path": next_prompt.memory_context.get("preference_profile_path"),
            "context_bundle_path": next_prompt.memory_context.get("context_bundle_path"),
            "cache_key": next_prompt.memory_context.get("cache_key"),
            "memory_refs": list(profile.source_memory_candidates),
            "memory_candidate_count": len(memory.candidates),
            "writes_long_term_memory": False,
        },
        "prompt_diff": dict(next_prompt.diff_from_previous_prompt),
        "acceptance_evidence": [
            "round_2 prompt pack uses next_round_prompt composed prompt",
            "round_2 candidates were generated from the memory-aware prompt pack",
            "comparison records reused memory refs without durable long-term writes",
        ],
        "validation_boundary": (
            "demo evidence only; passing artifacts prove workflow structure and memory reuse, "
            "not human acceptance or business validation"
        ),
        "context_bundle_id": context_bundle.bundle_id if context_bundle else None,
    }


def render_two_round_report(comparison: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# PosterFlow Two-Round Memory Demo",
            "",
            "## Round 1",
            f"- Run ID: {comparison['round_1']['run_id']}",
            f"- Candidates: {comparison['round_1']['candidate_count']}",
            "",
            "## Round 2",
            f"- Run ID: {comparison['round_2']['run_id']}",
            f"- Candidates: {comparison['round_2']['candidate_count']}",
            "",
            "## Memory Reuse",
            *[f"- {item}" for item in comparison["memory_reuse"]["memory_refs"]],
            "",
            "## Boundary",
            comparison["validation_boundary"],
            "",
        ]
    )


def _round_summary(manifest: PosterCandidatesManifest) -> dict[str, Any]:
    return {
        "run_id": manifest.run_id,
        "prompt_id": manifest.prompt_id,
        "candidate_count": len(manifest.candidates),
        "candidate_images": [candidate.image_path for candidate in manifest.candidates],
        "provider_mode": manifest.provider_mode,
    }
