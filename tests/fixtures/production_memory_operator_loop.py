from __future__ import annotations

from pathlib import Path

from agentflow.memory.production_next_pass_result import NEXT_PASS_RESULT_KIND


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def next_pass_result_for(packet: dict) -> dict:
    used_refs = [ref["ref_id"] for ref in packet["allowed_context_refs"][:2]]
    return {
        "kind": NEXT_PASS_RESULT_KIND,
        "artifact_type": NEXT_PASS_RESULT_KIND,
        "schema_version": packet["schema_version"],
        "task_packet_id": packet["task_packet_id"],
        "provider_mode": "no-provider",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "output_artifacts": [
            {
                "ref_id": "next-pass:artifact:draft-001",
                "title": "Second pass draft",
                "status": "draft",
                "used_context_refs": used_refs,
            }
        ],
        "feedback_events": [
            {
                "feedback_id": "feedback:next-pass-001",
                "target_ref": "next-pass:artifact:draft-001",
                "decision": "needs_revision",
                "summary": "Second pass needs operator review before memory promotion.",
            }
        ],
    }
