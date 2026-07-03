from __future__ import annotations


ALGORITHM_ID = "afs.control_event_register.v0.1"
INPUT_CONTRACT = "repo-local append-only JSONL control events for active and pending-control lanes"
OUTPUT_CONTRACT = "deterministic active/pending control register reconstructed from first-class events"
EVIDENCE_BOUNDARY = (
    "control-plane adapter evidence only; does not archive threads, replay full history, "
    "call providers, mutate Runtime Service, or promote Company OS rules"
)

CONTROL_EVENT_SCHEMA_VERSION = "0.1.0"
CONTROL_EVENT_ARTIFACT_TYPE = "agentflow_control_event"
CONTROL_REGISTER_ARTIFACT_TYPE = "agentflow_control_register"

ACTIVE_PENDING_STATES = frozenset({"active", "pending_control"})
ACK_STATES = frozenset({"no_ack", "ack_delivery_confirmed", "ack_delivery_failed"})
ARCHIVE_POLICIES = frozenset({"agent_created_archive_when_useless"})
ARCHIVE_EVALUATION_STATES = frozenset({"not_allowed", "allowed", "blocked_pending_ack"})
CLAIM_STATES = frozenset({"not_claimed", "claimed", "verified", "rejected"})
EVIDENCE_SOURCE_CLASSES = frozenset(
    {
        "dispatcher_instruction",
        "phase0_spec_artifact",
        "repo_fixture",
        "local_artifact",
        "runtime_verification",
        "human_review",
    }
)
EVENT_TYPES = frozenset(
    {
        "lane_registered",
        "role_surface_registered",
        "artifact_attached",
        "claim_state_changed",
        "non_claim_recorded",
        "archive_policy_evaluated",
        "archive_executed",
        "ack_state_changed",
    }
)
FIXED_ROLE_SURFACE_ROLES = frozenset({"dispatcher", "cto_disposition", "implementation_worker", "evaluator"})
IMPLEMENTATION_LANE_KINDS = frozenset({"implementation", "fixback"})


__all__ = (
    "ACK_STATES",
    "ACTIVE_PENDING_STATES",
    "ALGORITHM_ID",
    "ARCHIVE_EVALUATION_STATES",
    "ARCHIVE_POLICIES",
    "CLAIM_STATES",
    "CONTROL_EVENT_ARTIFACT_TYPE",
    "CONTROL_EVENT_SCHEMA_VERSION",
    "CONTROL_REGISTER_ARTIFACT_TYPE",
    "EVENT_TYPES",
    "EVIDENCE_BOUNDARY",
    "EVIDENCE_SOURCE_CLASSES",
    "FIXED_ROLE_SURFACE_ROLES",
    "IMPLEMENTATION_LANE_KINDS",
    "INPUT_CONTRACT",
    "OUTPUT_CONTRACT",
)
