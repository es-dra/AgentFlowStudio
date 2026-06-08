from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from agentflow_studio.model_gateway.company_secrets import CompanyProviderSecrets, resolve_ref
from agentflow_studio.model_gateway.errors import ModelConfigError, ModelProviderError
from agentflow_studio.model_gateway.kling_plan import build_kling_request_plan
from agentflow_studio.model_gateway.kling_video_task_state import (
    I2V_MANIFEST_NAME,
    build_success_manifest,
    build_task_state,
    load_task_state,
    manifest_name_for_api_family,
    safe_input_image_state,
    updated_task_state,
    write_task_state,
)
from agentflow_studio.model_gateway.kling_video_runtime import (
    build_runtime_payload,
    build_runtime_token,
    download_with_transport,
    poll_video_task,
    request_json_with_transport,
    response_data,
    task_video_url,
    video_extension,
)
from agentflow_studio.utils import write_json


MANIFEST_NAME = I2V_MANIFEST_NAME


def run_kling_i2v_smoke(
    store: CompanyProviderSecrets,
    *,
    service_id: str,
    prompt: str,
    image_path: str | Path,
    output_dir: str | Path,
    duration: str = "5",
    mode: str = "pro",
    poll_interval_sec: float = 5.0,
    max_polls: int = 120,
    timeout_sec: float = 120.0,
    transport: str = "httpx",
) -> dict[str, Any]:
    source_image = Path(image_path)
    if not source_image.is_file():
        raise ModelProviderError(f"Kling I2V source image not found: {source_image}")
    plan = build_kling_request_plan(
        store,
        service_id=service_id,
        prompt=prompt,
        image_ref=source_image.name,
        duration=duration,
        mode=mode,
        require_live_gate=True,
    )
    if plan.get("api_family") != "i2v":
        raise ModelConfigError(f"Kling I2V smoke requires i2v api_family: {service_id}")
    account = store.account(str(store.service(service_id).get("account_ref") or ""))
    authorization = f"Bearer {build_runtime_token(account)}"
    started = time.perf_counter()
    payload = build_runtime_payload(plan["create_request"]["json"], source_image)
    request_json = request_json_with_transport(transport)
    create_response = request_json(
        str(plan["create_request"]["url"]),
        method="POST",
        authorization=authorization,
        payload=payload,
        timeout_sec=timeout_sec,
    )
    task_id = _task_id(create_response)
    output_root = Path(output_dir)
    state = build_task_state(
        plan=plan,
        task_id=task_id,
        task_data=response_data(create_response),
        input_image=safe_input_image_state(source_image),
        status="submitted",
    )
    write_task_state(output_root, state)
    return _complete_video_task_with_transport_fallback(
        output_root,
        state=state,
        query_url_template=str(plan["query_request"]["url_template"]),
        authorization=authorization,
        transport=transport,
        poll_interval_sec=poll_interval_sec,
        max_polls=max_polls,
        timeout_sec=timeout_sec,
        started=started,
        resumed_from_task_state=False,
    )


def run_kling_t2v_smoke(
    store: CompanyProviderSecrets,
    *,
    service_id: str,
    prompt: str,
    output_dir: str | Path,
    duration: str = "5",
    mode: str = "pro",
    aspect_ratio: str = "9:16",
    poll_interval_sec: float = 5.0,
    max_polls: int = 120,
    timeout_sec: float = 120.0,
    transport: str = "httpx",
) -> dict[str, Any]:
    if store.service(service_id).get("api_family") != "t2v":
        raise ModelConfigError(f"Kling T2V smoke requires t2v api_family: {service_id}")
    plan = build_kling_request_plan(
        store,
        service_id=service_id,
        prompt=prompt,
        duration=duration,
        mode=mode,
        aspect_ratio=aspect_ratio,
        require_live_gate=True,
    )
    account = store.account(str(store.service(service_id).get("account_ref") or ""))
    authorization = f"Bearer {build_runtime_token(account)}"
    started = time.perf_counter()
    payload = dict(plan["create_request"]["json"])
    request_json = request_json_with_transport(transport)
    create_response = request_json(
        str(plan["create_request"]["url"]),
        method="POST",
        authorization=authorization,
        payload=payload,
        timeout_sec=timeout_sec,
    )
    task_id = _task_id(create_response)
    output_root = Path(output_dir)
    state = build_task_state(
        plan=plan,
        task_id=task_id,
        task_data=response_data(create_response),
        status="submitted",
    )
    write_task_state(output_root, state)
    return _complete_video_task_with_transport_fallback(
        output_root,
        state=state,
        query_url_template=str(plan["query_request"]["url_template"]),
        authorization=authorization,
        transport=transport,
        poll_interval_sec=poll_interval_sec,
        max_polls=max_polls,
        timeout_sec=timeout_sec,
        started=started,
        resumed_from_task_state=False,
    )


def resume_kling_video_task(
    store: CompanyProviderSecrets,
    *,
    task_state_path: str | Path,
    poll_interval_sec: float = 5.0,
    max_polls: int = 120,
    timeout_sec: float = 120.0,
    transport: str = "httpx",
) -> dict[str, Any]:
    state_path = Path(task_state_path)
    state = load_task_state(state_path)
    service = store.service(str(state["service_id"]))
    if service.get("provider") != "kling":
        raise ModelConfigError(f"Provider service is not a Kling service: {state['service_id']}")
    if service.get("api_family") != state.get("api_family"):
        raise ModelConfigError("Kling task state api_family does not match provider service")
    _require_live_gate(str(service.get("required_gate") or ""))
    account = store.account(str(service.get("account_ref") or ""))
    authorization = f"Bearer {build_runtime_token(account)}"
    query_url_template = _resume_query_url_template(store, service, account)
    started = time.perf_counter()
    return _complete_video_task_with_transport_fallback(
        state_path.parent,
        state=state,
        query_url_template=query_url_template,
        authorization=authorization,
        transport=transport,
        poll_interval_sec=poll_interval_sec,
        max_polls=max_polls,
        timeout_sec=timeout_sec,
        started=started,
        resumed_from_task_state=True,
    )


def _complete_video_task_with_transport_fallback(
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
        return _complete_video_task(
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
        return _complete_video_task(
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


def _complete_video_task(
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


def _resume_query_url_template(
    store: CompanyProviderSecrets,
    service: dict[str, Any],
    account: dict[str, Any],
) -> str:
    ref = service.get("query_endpoint_ref")
    if not isinstance(ref, str):
        raise ModelConfigError("Kling service missing query_endpoint_ref")
    endpoint = resolve_ref(store.model_dump(mode="python"), ref)
    base_url = str(account.get("base_url") or "")
    if not base_url:
        raise ModelConfigError("Kling base_url is required")
    endpoint_text = str(endpoint or "")
    if not endpoint_text.startswith("/"):
        raise ModelConfigError(f"Kling endpoint must start with '/': {endpoint_text}")
    return f"{base_url.rstrip('/')}{endpoint_text}"


def _require_live_gate(name: str) -> None:
    if os.environ.get(name, "").strip().lower() not in {"1", "true", "yes", "on"}:
        raise ModelProviderError(f"Remote video calls are disabled; set {name}=true to enable them")


def _task_id(response: dict[str, Any]) -> str:
    data = response_data(response)
    task_id = data.get("task_id") or response.get("task_id")
    if not isinstance(task_id, str) or not task_id.strip():
        raise ModelProviderError("Kling video response missing task_id")
    return task_id.strip()
