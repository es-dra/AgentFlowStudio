from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from agentflow.harness.json_io import write_json
from agentflow_studio.model_gateway.errors import ModelProviderError
from agentflow_studio.model_gateway.kling_video_runtime import (
    download_with_transport,
    poll_video_task,
    request_json_with_transport,
    task_video_url,
    video_extension,
)
from agentflow_studio.model_gateway.kling_video_task_state import (
    build_success_manifest,
    manifest_name_for_api_family,
    updated_task_state,
    write_task_state,
)


def complete_video_task_with_transport_fallback(
    output_root: Path,
    *,
    state: dict[str, Any],
    query_url_template: str,
    authorization: str,
    transport: str,
    poll_interval_sec: float,
    max_polls: int,
    timeout_sec: float,
    started: float,
    resumed_from_task_state: bool,
) -> dict[str, Any]:
    try:
        return complete_video_task(
            output_root,
            state=state,
            query_url_template=query_url_template,
            authorization=authorization,
            request_json=request_json_with_transport(transport),
            download=download_with_transport(transport),
            poll_interval_sec=poll_interval_sec,
            max_polls=max_polls,
            timeout_sec=timeout_sec,
            started=started,
            resumed_from_task_state=resumed_from_task_state,
        )
    except ModelProviderError:
        if transport != "httpx":
            raise
        return complete_video_task(
            output_root,
            state=state,
            query_url_template=query_url_template,
            authorization=authorization,
            request_json=request_json_with_transport("curl"),
            download=download_with_transport("curl"),
            poll_interval_sec=poll_interval_sec,
            max_polls=max_polls,
            timeout_sec=timeout_sec,
            started=started,
            resumed_from_task_state=resumed_from_task_state,
        )


def complete_video_task(
    output_root: Path,
    *,
    state: dict[str, Any],
    query_url_template: str,
    authorization: str,
    request_json,
    download,
    poll_interval_sec: float,
    max_polls: int,
    timeout_sec: float,
    started: float,
    resumed_from_task_state: bool,
) -> dict[str, Any]:
    task_id = str((state.get("task") or {}).get("task_id") or "")
    try:
        task_data = poll_video_task(
            query_url_template,
            task_id=task_id,
            authorization=authorization,
            request_json=request_json,
            poll_interval_sec=poll_interval_sec,
            max_polls=max_polls,
            timeout_sec=timeout_sec,
        )
    except ModelProviderError as exc:
        write_task_state(output_root, updated_task_state(state, status="poll_failed", error_message=str(exc)))
        raise

    try:
        video_url = task_video_url(task_data)
        video_bytes, content_type = download(video_url, timeout_sec=timeout_sec)
    except ModelProviderError as exc:
        write_task_state(
            output_root,
            updated_task_state(state, status="download_failed", task_data=task_data, error_message=str(exc)),
        )
        raise

    video_ref = f"video_candidates/candidate_001{video_extension(content_type)}"
    video_path = output_root / video_ref
    video_path.parent.mkdir(parents=True, exist_ok=True)
    video_path.write_bytes(video_bytes)
    success_state = updated_task_state(state, status="succeeded", task_data=task_data)
    write_task_state(output_root, success_state)
    manifest = build_success_manifest(
        state=success_state,
        task_data=task_data,
        video_ref=video_ref,
        video_bytes=video_bytes,
        content_type=content_type,
        latency_ms=int((time.perf_counter() - started) * 1000),
        resumed_from_task_state=resumed_from_task_state,
    )
    write_json(output_root / manifest_name_for_api_family(str(success_state.get("api_family") or "")), manifest)
    return manifest
