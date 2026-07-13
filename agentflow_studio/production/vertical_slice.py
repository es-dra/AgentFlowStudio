from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


SCHEMA_VERSION = "0.1.0"
CHECKPOINT_MODEL_VERSION = "1.0.0"
STAGES = ("initialized", "script_assets", "storyboard", "candidates", "creator_review", "quality_gate", "exported")
PROTECTED_NON_CLAIMS = {
    "provider_smoke": False,
    "generated_media_quality": False,
    "human_acceptance": False,
    "business_validation": False,
    "public_release": False,
    "cos_active_rule_promotion": False,
}


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CharacterSeed(ContractModel):
    character_id: str
    name: str
    role: str
    visual_anchor: str


class ProjectIP(ContractModel):
    schema_version: Literal["0.1.0"] = SCHEMA_VERSION
    project_id: str
    title: str
    premise: str
    audience: str
    format: str
    tone: str
    characters: list[CharacterSeed] = Field(min_length=1)


class CreatorDecision(ContractModel):
    schema_version: Literal["0.1.0"] = SCHEMA_VERSION
    decision_id: str
    creator_id: str
    selected_candidate_ids: list[str] = Field(min_length=1)
    revision_notes: dict[str, str] = Field(default_factory=dict)


class QualityChecklist(ContractModel):
    story_intent_preserved: bool
    character_continuity_checked: bool
    shot_coverage_checked: bool
    revision_addressed: bool


class QualityReview(ContractModel):
    schema_version: Literal["0.1.0"] = SCHEMA_VERSION
    review_id: str
    reviewer_id: str
    review_mode: Literal["fixture", "human"]
    project_fingerprint: str
    reviewed_subject_digest: str
    decision: Literal["approve", "reject"]
    checklist: QualityChecklist
    notes: str

    @model_validator(mode="after")
    def approved_review_requires_complete_checklist(self) -> "QualityReview":
        if self.decision == "approve" and not all(self.checklist.model_dump().values()):
            raise ValueError("approved quality review requires every checklist item")
        return self


class DeterministicProductionSlice:
    """Recoverable local production slice with explicit creator and quality gates."""

    state_name = "production_state.json"

    def __init__(self, project: ProjectIP, output_dir: str | Path) -> None:
        self.project = project
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.output_dir / self.state_name
        self.state = self._load_or_initialize()

    @classmethod
    def from_files(
        cls,
        project_path: str | Path,
        creator_decision_path: str | Path,
        quality_review_path: str | Path,
        output_dir: str | Path,
    ) -> dict[str, Path]:
        project = ProjectIP.model_validate(_read_json(Path(project_path)))
        decision = CreatorDecision.model_validate(_read_json(Path(creator_decision_path)))
        review = QualityReview.model_validate(_read_json(Path(quality_review_path)))
        run = cls(project, output_dir)
        run.advance_to_candidates()
        run.record_creator_decision(decision)
        run.record_quality_review(review)
        return run.export()

    def advance_to_candidates(self, *, fail_after_stage: str | None = None) -> None:
        for stage, builder in (
            ("script_assets", self._build_script_assets),
            ("storyboard", self._build_storyboard),
            ("candidates", self._build_candidates),
        ):
            if self._stage_index() < STAGES.index(stage):
                builder()
                self.state["stage"] = stage
                self._write_state()
            if fail_after_stage == stage:
                raise RuntimeError(f"injected deterministic failure after {stage}")

    def record_creator_decision(self, decision: CreatorDecision) -> None:
        if self._stage_index() < STAGES.index("candidates"):
            raise ValueError("candidate generation must complete before creator selection")
        existing = self.state["artifacts"].get("creator_decision")
        if existing:
            if existing != decision.model_dump(mode="json"):
                raise ValueError("checkpoint already contains a different creator decision")
            return
        candidates = {item["candidate_id"]: item for item in self.state["artifacts"]["candidates"]}
        selected = []
        for candidate_id in decision.selected_candidate_ids:
            if candidate_id not in candidates:
                raise ValueError(f"unknown candidate: {candidate_id}")
            candidate = candidates[candidate_id]
            revision_note = decision.revision_notes.get(candidate_id, "")
            selected.append(
                {
                    **candidate,
                    "revision_id": _stable_id("revision", candidate_id, revision_note or "no_change"),
                    "revision_note": revision_note,
                    "creator_decision_id": decision.decision_id,
                }
            )
        shot_ids = {item["shot_id"] for item in self.state["artifacts"]["shots"]}
        selected_shot_ids = {item["shot_id"] for item in selected}
        if selected_shot_ids != shot_ids or len(selected) != len(shot_ids):
            raise ValueError("creator must select exactly one candidate for every shot")
        self.state["artifacts"]["creator_decision"] = decision.model_dump(mode="json")
        self.state["artifacts"]["selected_revisions"] = selected
        self.state["lineage"].extend(
            {
                "source_ref": item["candidate_id"],
                "target_ref": item["revision_id"],
                "relation": "creator_selected_and_revised",
            }
            for item in selected
        )
        self.state["stage"] = "creator_review"
        self._write_state()

    def record_quality_review(self, review: QualityReview) -> None:
        if self._stage_index() < STAGES.index("creator_review"):
            raise ValueError("creator selection must complete before quality review")
        existing = self.state["artifacts"].get("quality_review")
        if existing:
            if existing != review.model_dump(mode="json"):
                raise ValueError("checkpoint already contains a different quality review")
            return
        if review.project_fingerprint != self.state["project_fingerprint"]:
            raise ValueError("quality review project fingerprint does not match this run")
        expected_subject_digest = self._review_subject_digest()
        if review.reviewed_subject_digest != expected_subject_digest:
            raise ValueError("quality review subject digest does not match creator decision and revisions")
        self.state["artifacts"]["quality_review"] = review.model_dump(mode="json")
        self.state["lineage"].append(
            {
                "source_ref": self.state["artifacts"]["creator_decision"]["decision_id"],
                "target_ref": review.review_id,
                "relation": "creator_decision_reviewed",
            }
        )
        self.state["stage"] = "quality_gate"
        self._write_state()

    def export(self) -> dict[str, Path]:
        if self._stage_index() < STAGES.index("quality_gate"):
            raise ValueError("quality review is required before export")
        review = QualityReview.model_validate(self.state["artifacts"]["quality_review"])
        if review.decision != "approve":
            raise ValueError("quality review rejected export")

        source_state_integrity = self.state["checkpoint_integrity"]["chain_digest"]
        delivery_id = _stable_id("delivery", self.project.project_id, review.review_id)
        export_lineage = list(self.state["lineage"])
        delivery_edges = [
            *(
                {
                    "source_ref": revision["revision_id"],
                    "target_ref": delivery_id,
                    "relation": "revision_included_in_delivery",
                }
                for revision in self.state["artifacts"]["selected_revisions"]
            ),
            {
                "source_ref": review.review_id,
                "target_ref": delivery_id,
                "relation": "quality_review_approved_delivery",
            },
        ]
        for edge in delivery_edges:
            if edge not in export_lineage:
                export_lineage.append(edge)
        delivery = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "deterministic_storyboard_delivery",
            "delivery_id": delivery_id,
            "project": self.project.model_dump(mode="json"),
            "script": self.state["artifacts"]["script"],
            "character_assets": self.state["artifacts"]["character_assets"],
            "storyboard": self.state["artifacts"]["storyboard"],
            "shots": self.state["artifacts"]["shots"],
            "selected_revisions": self.state["artifacts"]["selected_revisions"],
            "creator_decision_ref": self.state["artifacts"]["creator_decision"]["decision_id"],
            "quality_review_ref": review.review_id,
            "reviewed_subject_digest": review.reviewed_subject_digest,
            "source_state_chain_digest": source_state_integrity,
            "lineage": export_lineage,
            "export_scope": "script_character_storyboard_candidate_package",
        }
        delivery_path = self.output_dir / "production_delivery.json"
        _write_json(delivery_path, delivery)
        delivery_sha256 = hashlib.sha256(delivery_path.read_bytes()).hexdigest()

        evidence = {
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "deterministic_vertical_slice_evidence",
            "run_id": self.state["run_id"],
            "claim_level": "deterministic_local_structure_and_flow",
            "stage": "exported",
            "state_ref": self.state_name,
            "delivery_ref": delivery_path.name,
            "delivery_sha256": delivery_sha256,
            "source_state_chain_digest": source_state_integrity,
            "reviewed_subject_digest": review.reviewed_subject_digest,
            "creator_in_loop": {
                "decision_ref": self.state["artifacts"]["creator_decision"]["decision_id"],
                "selected_count": len(self.state["artifacts"]["selected_revisions"]),
                "revision_count": sum(
                    bool(item["revision_note"]) for item in self.state["artifacts"]["selected_revisions"]
                ),
            },
            "quality_gate": {
                **review.model_dump(mode="json"),
                "human_acceptance_claimed": False,
                "verified_acceptance_artifact": None,
            },
            "recovery": {
                "checkpointed": True,
                "recovery_count": self.state["recovery_count"],
                "last_checkpoint": self.state["stage"],
            },
            "lineage": export_lineage,
            "non_claims": {
                **PROTECTED_NON_CLAIMS,
                "human_acceptance": False,
            },
        }
        evidence_path = self.output_dir / "evidence.json"
        _write_json(evidence_path, evidence)
        evidence_sha256 = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
        self.state["artifacts"]["export"] = {
            "delivery_ref": delivery_path.name,
            "delivery_sha256": delivery_sha256,
            "evidence_ref": evidence_path.name,
            "evidence_sha256": evidence_sha256,
            "source_state_chain_digest": source_state_integrity,
        }
        self.state["lineage"] = export_lineage
        self.state["stage"] = "exported"
        self._write_state()
        return {"delivery": delivery_path, "evidence": evidence_path, "state": self.state_path}

    def _load_or_initialize(self) -> dict[str, Any]:
        fingerprint = _digest(self.project.model_dump(mode="json"))
        if self.state_path.exists():
            state = _read_json(self.state_path)
            self._validate_checkpoint(state)
            if state.get("project_fingerprint") != fingerprint:
                raise ValueError("existing checkpoint belongs to a different project input")
            state["recovery_count"] += 1
            _write_json(self.state_path, state)
            return state
        state = {
            "schema_version": SCHEMA_VERSION,
            "checkpoint_model_version": CHECKPOINT_MODEL_VERSION,
            "run_id": _stable_id("run", self.project.project_id, fingerprint),
            "project_fingerprint": fingerprint,
            "stage": "initialized",
            "recovery_count": 0,
            "artifacts": {},
            "lineage": [],
        }
        _write_json(self.state_path, state)
        return state

    def _build_script_assets(self) -> None:
        beats = [
            {"beat_id": "beat_001", "purpose": "hook", "text": self.project.premise},
            {
                "beat_id": "beat_002",
                "purpose": "choice",
                "text": f"The lead makes a visible choice that tests the {self.project.tone} premise.",
            },
            {
                "beat_id": "beat_003",
                "purpose": "payoff",
                "text": "The consequence lands in a final image that can be evaluated shot by shot.",
            },
        ]
        script_id = _stable_id("script", self.project.project_id, self.project.premise)
        self.state["artifacts"]["script"] = {"script_id": script_id, "beats": beats}
        self.state["artifacts"]["character_assets"] = [
            {
                **character.model_dump(mode="json"),
                "asset_id": _stable_id("character_asset", self.project.project_id, character.character_id),
                "asset_kind": "deterministic_character_definition",
            }
            for character in self.project.characters
        ]
        self.state["lineage"].append(
            {"source_ref": self.project.project_id, "target_ref": script_id, "relation": "project_to_script"}
        )
        self.state["lineage"].extend(
            {
                "source_ref": self.project.project_id,
                "target_ref": asset["asset_id"],
                "relation": "project_to_character_asset",
            }
            for asset in self.state["artifacts"]["character_assets"]
        )

    def _build_storyboard(self) -> None:
        script = self.state["artifacts"]["script"]
        storyboard_id = _stable_id("storyboard", script["script_id"])
        shots = []
        for index, beat in enumerate(script["beats"], start=1):
            shot_id = f"shot_{index:03d}"
            shots.append(
                {
                    "shot_id": shot_id,
                    "beat_id": beat["beat_id"],
                    "framing": ("wide", "medium", "close")[index - 1],
                    "action": beat["text"],
                    "character_asset_refs": [item["asset_id"] for item in self.state["artifacts"]["character_assets"]],
                }
            )
            self.state["lineage"].append(
                {"source_ref": beat["beat_id"], "target_ref": shot_id, "relation": "beat_to_shot"}
            )
        self.state["artifacts"]["storyboard"] = {
            "storyboard_id": storyboard_id,
            "source_script_id": script["script_id"],
            "shot_refs": [item["shot_id"] for item in shots],
        }
        self.state["lineage"].append(
            {
                "source_ref": script["script_id"],
                "target_ref": storyboard_id,
                "relation": "script_to_storyboard",
            }
        )
        self.state["lineage"].extend(
            {
                "source_ref": asset_ref,
                "target_ref": shot["shot_id"],
                "relation": "character_asset_to_shot",
            }
            for shot in shots
            for asset_ref in shot["character_asset_refs"]
        )
        self.state["artifacts"]["shots"] = shots

    def _build_candidates(self) -> None:
        candidates = []
        for shot in self.state["artifacts"]["shots"]:
            for variant, direction in (("a", "clarity_first"), ("b", "tension_first")):
                candidate_id = _stable_id("candidate", shot["shot_id"], variant, shot["action"])
                candidates.append(
                    {
                        "candidate_id": candidate_id,
                        "shot_id": shot["shot_id"],
                        "generation_mode": "local_deterministic_text_treatment",
                        "direction": direction,
                        "treatment": f"{shot['framing']} frame; {shot['action']} Direction: {direction}.",
                        "is_generated_media": False,
                    }
                )
                self.state["lineage"].append(
                    {"source_ref": shot["shot_id"], "target_ref": candidate_id, "relation": "shot_to_candidate"}
                )
        self.state["artifacts"]["candidates"] = candidates

    def _stage_index(self) -> int:
        return STAGES.index(self.state["stage"])

    def _write_state(self) -> None:
        previous = self.state.get("checkpoint_integrity", {})
        unsigned_state = {key: value for key, value in self.state.items() if key != "checkpoint_integrity"}
        state_digest = _digest(unsigned_state)
        previous_chain_digest = previous.get("chain_digest")
        self.state["checkpoint_integrity"] = {
            "algorithm": "sha256",
            "sequence": int(previous.get("sequence", -1)) + 1,
            "previous_chain_digest": previous_chain_digest,
            "state_digest": state_digest,
            "chain_digest": _digest(
                {"previous_chain_digest": previous_chain_digest, "state_digest": state_digest}
            ),
        }
        _write_json(self.state_path, self.state)

    def _validate_checkpoint(self, state: dict[str, Any]) -> None:
        if state.get("checkpoint_model_version") != CHECKPOINT_MODEL_VERSION:
            raise ValueError("unsupported checkpoint model version")
        integrity = state.get("checkpoint_integrity")
        if not isinstance(integrity, dict) or integrity.get("algorithm") != "sha256":
            raise ValueError("checkpoint integrity metadata is missing or unsupported")
        unsigned_state = {key: value for key, value in state.items() if key != "checkpoint_integrity"}
        actual_state_digest = _digest(unsigned_state)
        if integrity.get("state_digest") != actual_state_digest:
            raise ValueError("checkpoint state integrity validation failed")
        actual_chain_digest = _digest(
            {
                "previous_chain_digest": integrity.get("previous_chain_digest"),
                "state_digest": actual_state_digest,
            }
        )
        if integrity.get("chain_digest") != actual_chain_digest:
            raise ValueError("checkpoint chain integrity validation failed")

    def _review_subject_digest(self) -> str:
        return _digest(
            {
                "project_fingerprint": self.state["project_fingerprint"],
                "creator_decision": self.state["artifacts"]["creator_decision"],
                "selected_revisions": self.state["artifacts"]["selected_revisions"],
            }
        )


def _stable_id(prefix: str, *parts: str) -> str:
    token = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{token}"


def _digest(payload: Any) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)
