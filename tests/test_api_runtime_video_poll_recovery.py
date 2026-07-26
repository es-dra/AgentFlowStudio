from __future__ import annotations

from agentflow_studio.model_gateway.errors import ModelGatewayError
from apps.api.runtime_store import RuntimeStore
from apps.api.runtime_video_dispatch import poll_video_generation
from apps.api.runtime_video_task_state import load_task_state, write_task_state


def test_transient_poll_error_remains_recoverable_without_terminal_failure(tmp_path) -> None:
    store = RuntimeStore(tmp_path / "runtime")
    project_id = "video-poll-recovery"
    store.ensure_project_manifest(project_id)
    output_dir = store.run_dir(project_id, "video-job-recovery")
    output_dir.mkdir(parents=True, exist_ok=True)
    write_task_state(
        output_dir,
        {
            "schema_version": "afs_video_generation_task_state.v0.1",
            "status": "submitted",
            "provider_service_id": "seedance_i2v",
            "capability": "video",
            "task": {
                "service_id": "seedance_i2v",
                "capability": "video",
                "task": {
                    "task_id": "provider-task-recovery",
                    "query_url_template": (
                        "https://relay.test/volc/v1/contents/generations/tasks/{id}"
                    ),
                },
            },
            "created_at": "2026-07-26T03:00:00Z",
            "submitted_at": "2026-07-26T03:00:00Z",
            "provider_raw_persisted": False,
        },
    )

    class TransientRegistry:
        def poll(self, *_args, **_kwargs):
            raise ModelGatewayError("temporary upstream timeout")

    result = poll_video_generation(
        store,
        project_id,
        output_dir,
        load_registry=lambda: TransientRegistry(),
    )

    assert result["status"] == "reconcile_required"
    state = load_task_state(output_dir)
    assert state["status"] == "reconcile_required"
    assert state["last_poll_error"] == {
        "category": "transient_provider_poll_error",
        "retryable": True,
    }
    assert "completed_at" not in state
