from __future__ import annotations

import json
import shutil
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agentflow.harness.json_io import exclusive_file_lock
from apps.api import runtime_m6_script_plan_asset_bible as m6_routes
from apps.api.runtime_m6_preview_runs import (
    MAX_TERMINAL_RUNS_PER_PROJECT,
    MAX_UNCONFIRMED_RUNS_PER_PROJECT,
    M6PreviewRunError,
    M6PreviewRunStore,
    preview_source_digest,
)
from apps.api.runtime_service import create_runtime_app
from apps.api.runtime_store import RuntimeStore
from tests.test_runtime_m6_script_plan_asset_bible import (
    IDEA_TEXT,
    SCRIPT_TEXT,
    _bind_script_revision,
)


@pytest.mark.parametrize("source_text", ["灯亮", "第一行。\n第二行？", "🌧️ 雨夜，纸船逆流。"])
def test_short_unicode_ideas_enter_durable_planning_without_schema_rejection_or_graph_mutation(
    tmp_path,
    monkeypatch,
    source_text: str,
) -> None:
    monkeypatch.setattr(m6_routes, "_server_codex_m6_enabled", lambda: False)
    runtime_root = tmp_path / "runtime"
    client = TestClient(create_runtime_app(runtime_root=runtime_root))
    binding = _bind_script_revision(client, "short-unicode", source_text)

    response = client.post(
        "/projects/short-unicode/m6/script-plan-asset-bible/preview",
        headers={"X-Client-Request-ID": f"short-{len(source_text)}"},
        json={"source_kind": "script", "source_text": source_text, **binding},
    )
    assert response.status_code == 200, response.text
    run = _wait_for_phase(
        client,
        "short-unicode",
        response.json()["run_id"],
        "failed",
    )

    assert run["phase"] == "failed"
    assert run["error"]["category"] == "planning_rejected"
    assert run["provider"] == {
        "service": "local_deterministic",
        "provider": "local_runtime",
        "model": "deterministic_contract",
    }
    assert run["dispatch_count"] == 0
    assert run["cost"]["actual_usd"] is None
    assert run["cost"]["reported_external_paid_cost_usd"] == 0
    assert not (runtime_root / "projects" / "short-unicode" / "production_graph.json").exists()
    ledger_text = (
        runtime_root
        / "projects"
        / "short-unicode"
        / "m6_preview_runs"
        / run["run_id"]
        / "run.json"
    ).read_text(encoding="utf-8")
    assert source_text not in ledger_text


def test_disconnect_recovery_reuses_one_dispatch_and_confirm_is_exactly_once(tmp_path, monkeypatch) -> None:
    original = m6_routes.build_m6_script_plan_asset_bible
    started = threading.Event()
    release = threading.Event()
    calls: list[str] = []

    def controlled_planner(project_id, body):
        calls.append(project_id)
        started.set()
        assert release.wait(timeout=5)
        return original(project_id, body)

    monkeypatch.setattr(m6_routes, "_server_codex_m6_enabled", lambda: True)
    monkeypatch.setattr(m6_routes, "_preview_planner", lambda enabled: controlled_planner)
    runtime_root = tmp_path / "runtime"
    client = TestClient(create_runtime_app(runtime_root=runtime_root))
    headers = {"X-Client-Request-ID": "disconnect-one"}
    binding = _bind_script_revision(client, "recover", IDEA_TEXT)
    payload = {"source_kind": "script", "source_text": IDEA_TEXT, **binding}

    created = client.post("/projects/recover/m6/script-plan-asset-bible/preview", headers=headers, json=payload)
    assert created.status_code == 200, created.text
    assert started.wait(timeout=2)
    run = client.get(
        "/projects/recover/m6/script-plan-asset-bible/preview-runs/by-client/disconnect-one",
    ).json()
    assert run["phase"] == "running"
    assert run["dispatch_count"] == 1
    assert run["provider"] == {"service": "server_codex", "provider": "codex_local", "model": "gpt-5.5"}
    assert not (runtime_root / "projects" / "recover" / "production_graph.json").exists()

    replay = client.post("/projects/recover/m6/script-plan-asset-bible/preview", headers=headers, json=payload)
    assert replay.status_code == 200
    assert replay.json()["run_id"] == run["run_id"]
    conflict = client.post(
        "/projects/recover/m6/script-plan-asset-bible/preview",
        headers=headers,
        json={**payload, "revision_instruction": "different source digest"},
    )
    assert conflict.status_code == 409
    assert "preview_source_digest_mismatch" in conflict.text
    assert calls == ["recover"]

    release.set()
    run = _wait_for_phase(client, "recover", run["run_id"], "succeeded")
    assert run["preview"]["candidate_digest"] == run["candidate_digest"]
    assert calls == ["recover"]
    ledger_text = (
        runtime_root
        / "projects"
        / "recover"
        / "m6_preview_runs"
        / run["run_id"]
        / "run.json"
    ).read_text(encoding="utf-8")
    assert IDEA_TEXT.strip() not in ledger_text
    assert "source_text" not in ledger_text

    confirm_body = {
        "run_id": run["run_id"],
        "candidate_digest": run["candidate_digest"],
        "expected_graph_version": 0,
    }
    first = client.post("/projects/recover/m6/script-plan-asset-bible/confirm", json=confirm_body)
    second = client.post("/projects/recover/m6/script-plan-asset-bible/confirm", json=confirm_body)
    assert first.status_code == second.status_code == 200
    assert first.json()["graph"]["version"] == second.json()["graph"]["version"] == 1
    assert first.json()["graph"]["graph_digest"] == second.json()["graph"]["graph_digest"]
    assert len(first.json()["graph"]["idempotency"]) == 1
    mismatch = client.post(
        "/projects/recover/m6/script-plan-asset-bible/confirm",
        json={**confirm_body, "candidate_digest": "f" * 64},
    )
    assert mismatch.status_code == 409


def test_concurrent_confirm_builds_and_persists_one_receipt(tmp_path) -> None:
    store = M6PreviewRunStore(RuntimeStore(tmp_path / "runtime"))
    preview = m6_routes.build_m6_script_plan_asset_bible(
        "confirm-race",
        {"source_kind": "idea", "source_text": IDEA_TEXT},
    )
    run, _ = store.create_or_load(
        "confirm-race",
        owner_id="owner",
        client_request_id="confirm-race",
        source_digest="a" * 64,
        expected_graph_version=0,
        remote_llm_enabled=False,
    )
    store.begin_dispatch("confirm-race", run["run_id"], owner_id="owner")
    run = store.succeed("confirm-race", run["run_id"], owner_id="owner", preview=preview)
    barrier = threading.Barrier(3)
    build_count = 0
    responses: list[dict] = []

    def build_response(bound_run: dict, candidate: dict) -> dict:
        nonlocal build_count
        build_count += 1
        time.sleep(0.05)
        return {
            "status": "confirmed",
            "run_id": bound_run["run_id"],
            "candidate_digest": candidate["candidate_digest"],
            "graph": {"version": 1, "graph_digest": "b" * 64},
        }

    def confirm() -> None:
        barrier.wait()
        responses.append(
            store.confirm_once(
                "confirm-race",
                run["run_id"],
                owner_id="owner",
                candidate_digest=run["candidate_digest"],
                expected_graph_version=0,
                build_response=build_response,
            )
        )

    threads = [threading.Thread(target=confirm), threading.Thread(target=confirm)]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join(timeout=2)
        assert not thread.is_alive()
    assert build_count == 1
    assert len(responses) == 2
    assert responses[0] == responses[1]


def test_failed_or_cancelled_run_never_writes_graph_or_blindly_retries(tmp_path, monkeypatch) -> None:
    calls = 0

    def failed_planner(project_id, body):
        nonlocal calls
        calls += 1
        raise TimeoutError("controlled timeout without provider output")

    monkeypatch.setattr(m6_routes, "_server_codex_m6_enabled", lambda: True)
    monkeypatch.setattr(m6_routes, "_preview_planner", lambda enabled: failed_planner)
    runtime_root = tmp_path / "runtime"
    client = TestClient(create_runtime_app(runtime_root=runtime_root))
    headers = {"X-Client-Request-ID": "failed-once"}
    binding = _bind_script_revision(client, "failed", SCRIPT_TEXT)
    payload = {"source_kind": "script", "source_text": SCRIPT_TEXT, **binding}
    created = client.post(
        "/projects/failed/m6/script-plan-asset-bible/preview",
        headers=headers,
        json=payload,
    )
    run = _wait_for_phase(client, "failed", created.json()["run_id"], "failed")
    assert run["dispatch_count"] == 1
    assert run["error"]["category"] == "timeout"
    assert "制作事实未改变" not in json.dumps(run, ensure_ascii=False) or run["phase"] == "failed"
    replay = client.post(
        "/projects/failed/m6/script-plan-asset-bible/preview",
        headers=headers,
        json=payload,
    )
    assert replay.json()["phase"] == "failed"
    assert calls == 1
    assert not (runtime_root / "projects" / "failed" / "production_graph.json").exists()
    confirm = client.post(
        "/projects/failed/m6/script-plan-asset-bible/confirm",
        json={"run_id": run["run_id"], "candidate_digest": "0" * 64, "expected_graph_version": 0},
    )
    assert confirm.status_code == 409

    store = M6PreviewRunStore(RuntimeStore(tmp_path / "cancel-runtime"))
    queued, _ = store.create_or_load(
        "cancelled",
        owner_id="owner",
        client_request_id="cancel-before-dispatch",
        source_digest="a" * 64,
        expected_graph_version=0,
        remote_llm_enabled=True,
    )
    cancelled = store.cancel("cancelled", queued["run_id"], owner_id="owner")
    assert cancelled["phase"] == "cancelled"
    assert cancelled["dispatch_count"] == 0


def test_stale_graph_and_candidate_digest_fail_closed(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    first = _start_and_wait(client, "stale", IDEA_TEXT, "stale-first")
    confirmed = client.post(
        "/projects/stale/m6/script-plan-asset-bible/confirm",
        json={
            "run_id": first["run_id"],
            "candidate_digest": first["candidate_digest"],
            "expected_graph_version": 0,
        },
    )
    assert confirmed.status_code == 200
    second = _start_and_wait(client, "stale", SCRIPT_TEXT, "stale-second")
    stale = client.post(
        "/projects/stale/m6/script-plan-asset-bible/confirm",
        json={
            "run_id": second["run_id"],
            "candidate_digest": second["candidate_digest"],
            "expected_graph_version": 0,
        },
    )
    assert stale.status_code == 409
    graph = client.get("/projects/stale/m5/sequence-workspace").json()
    assert graph["graph_version"] == 1


def test_preview_run_recovery_is_owner_and_project_scoped(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AFS_AUTH_ALLOW_OPEN_SIGNUP", "true")
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    owner = _register(client, "owner@example.com")
    other = _register(client, "other@example.com")
    owner_headers = {
        "Authorization": f"Bearer {owner['session_token']}",
        "X-Client-Request-ID": "owner-preview",
    }
    other_headers = {"Authorization": f"Bearer {other['session_token']}"}
    created_project = client.post(
        "/projects",
        headers=owner_headers,
        json={"project_id": "owned-preview", "goal": "owner scoped preview"},
    )
    assert created_project.status_code == 200
    run = _start_and_wait(
        client,
        "owned-preview",
        IDEA_TEXT,
        "owner-preview",
        headers=owner_headers,
    )

    for method, path, body in (
        ("get", f"/projects/owned-preview/m6/script-plan-asset-bible/preview-runs/{run['run_id']}", None),
        ("get", "/projects/owned-preview/m6/script-plan-asset-bible/preview-runs/by-client/owner-preview", None),
        ("post", f"/projects/owned-preview/m6/script-plan-asset-bible/preview-runs/{run['run_id']}/cancel", {}),
        (
            "post",
            "/projects/owned-preview/m6/script-plan-asset-bible/confirm",
            {"run_id": run["run_id"], "candidate_digest": run["candidate_digest"], "expected_graph_version": 0},
        ),
    ):
        response = getattr(client, method)(path, headers=other_headers, json=body) if body is not None else getattr(client, method)(path, headers=other_headers)
        assert response.status_code == 403
    owner_run = client.get(
        f"/projects/owned-preview/m6/script-plan-asset-bible/preview-runs/{run['run_id']}",
        headers=owner_headers,
    )
    assert owner_run.status_code == 200
    assert owner_run.json()["candidate_digest"] == run["candidate_digest"]


def test_terminal_and_unconfirmed_candidate_retention_are_bounded(tmp_path) -> None:
    store = M6PreviewRunStore(RuntimeStore(tmp_path / "runtime"))
    succeeded_ids: list[str] = []
    preview = m6_routes.build_m6_script_plan_asset_bible(
        "retention",
        {"source_kind": "idea", "source_text": IDEA_TEXT},
    )
    for index in range(MAX_UNCONFIRMED_RUNS_PER_PROJECT + 3):
        run, _ = store.create_or_load(
            "retention",
            owner_id="owner",
            client_request_id=f"succeeded-{index}",
            source_digest=f"{index + 100:064x}",
            expected_graph_version=0,
            remote_llm_enabled=False,
        )
        store.begin_dispatch("retention", run["run_id"], owner_id="owner")
        store.succeed("retention", run["run_id"], owner_id="owner", preview=preview)
        succeeded_ids.append(run["run_id"])
    for index in range(MAX_TERMINAL_RUNS_PER_PROJECT + 8):
        run, _ = store.create_or_load(
            "retention",
            owner_id="owner",
            client_request_id=f"terminal-{index}",
            source_digest=f"{index:064x}",
            expected_graph_version=0,
            remote_llm_enabled=False,
        )
        store.cancel("retention", run["run_id"], owner_id="owner")
    paths = list(store.runs_dir("retention").glob("*/run.json"))
    assert len(paths) <= MAX_TERMINAL_RUNS_PER_PROJECT + MAX_UNCONFIRMED_RUNS_PER_PROJECT
    assert not store.run_path("retention", succeeded_ids[0]).exists()
    assert store.tombstone_path("retention").is_file()
    tombstone_index = json.loads(store.tombstone_path("retention").read_text(encoding="utf-8"))
    assert succeeded_ids[0] in tombstone_index["runs"]
    with pytest.raises(M6PreviewRunError) as replay:
        store.create_or_load(
            "retention",
            owner_id="owner",
            client_request_id="succeeded-0",
            source_digest=f"{100:064x}",
            expected_graph_version=0,
            remote_llm_enabled=False,
        )
    assert getattr(replay.value, "code", "") == "preview_run_expired"
    with pytest.raises(M6PreviewRunError) as mismatch:
        store.create_or_load(
            "retention",
            owner_id="owner",
            client_request_id="succeeded-0",
            source_digest="f" * 64,
            expected_graph_version=0,
            remote_llm_enabled=False,
        )
    assert getattr(mismatch.value, "code", "") == "preview_source_digest_mismatch"
    for run_id in succeeded_ids[-MAX_UNCONFIRMED_RUNS_PER_PROJECT:]:
        assert store.run_path("retention", run_id).is_file()
        assert store.candidate_path("retention", run_id).is_file()


def test_prune_serializes_run_and_candidate_reads_to_expired_contract(tmp_path) -> None:
    store = M6PreviewRunStore(RuntimeStore(tmp_path / "runtime"))
    preview = m6_routes.build_m6_script_plan_asset_bible(
        "prune-race",
        {"source_kind": "idea", "source_text": IDEA_TEXT},
    )
    run, _ = store.create_or_load(
        "prune-race",
        owner_id="owner",
        client_request_id="prune-race",
        source_digest="a" * 64,
        expected_graph_version=0,
        remote_llm_enabled=False,
    )
    store.begin_dispatch("prune-race", run["run_id"], owner_id="owner")
    run = store.succeed("prune-race", run["run_id"], owner_id="owner", preview=preview)
    started = threading.Barrier(3)
    outcomes: list[str] = []

    def read_run() -> None:
        started.wait()
        try:
            store.load("prune-race", run["run_id"], owner_id="owner")
        except M6PreviewRunError as exc:
            outcomes.append(exc.code)

    def read_public_candidate() -> None:
        started.wait()
        try:
            store.public(run)
        except M6PreviewRunError as exc:
            outcomes.append(exc.code)

    with exclusive_file_lock(store.run_lock_path("prune-race", run["run_id"])):
        threads = [
            threading.Thread(target=read_run),
            threading.Thread(target=read_public_candidate),
        ]
        for thread in threads:
            thread.start()
        started.wait()
        store._record_tombstone("prune-race", run["run_id"], store._build_tombstone(run))
        shutil.rmtree(store.run_path("prune-race", run["run_id"]).parent)
    for thread in threads:
        thread.join(timeout=2)
        assert not thread.is_alive()
    assert outcomes == ["preview_run_expired", "preview_run_expired"]


def test_pruned_confirmed_run_replays_minimal_canonical_receipt(tmp_path) -> None:
    runtime_root = tmp_path / "runtime"
    client = TestClient(create_runtime_app(runtime_root=runtime_root))
    run = _start_and_wait(client, "confirmed-retention", IDEA_TEXT, "confirmed-retention")
    body = {
        "run_id": run["run_id"],
        "candidate_digest": run["candidate_digest"],
        "expected_graph_version": 0,
    }
    first = client.post(
        "/projects/confirmed-retention/m6/script-plan-asset-bible/confirm",
        json=body,
    )
    assert first.status_code == 200
    first_graph = {
        "version": first.json()["graph"]["version"],
        "graph_digest": first.json()["graph"]["graph_digest"],
    }
    store = M6PreviewRunStore(RuntimeStore(runtime_root))
    for index in range(MAX_TERMINAL_RUNS_PER_PROJECT + 2):
        terminal, _ = store.create_or_load(
            "confirmed-retention",
            owner_id="local-runtime-owner",
            client_request_id=f"confirmed-terminal-{index}",
            source_digest=f"{index + 500:064x}",
            expected_graph_version=1,
            remote_llm_enabled=False,
        )
        store.cancel("confirmed-retention", terminal["run_id"], owner_id="local-runtime-owner")
    assert not store.run_path("confirmed-retention", run["run_id"]).exists()
    replay = client.post(
        "/projects/confirmed-retention/m6/script-plan-asset-bible/confirm",
        json=body,
    )
    assert replay.status_code == 200
    assert replay.json()["status"] == "confirmed"
    assert replay.json()["graph"] == first_graph
    assert replay.json()["candidate_digest"] == run["candidate_digest"]
    projection = client.get("/projects/confirmed-retention/script-truth").json()["projection"]
    preview_replay = client.post(
        "/projects/confirmed-retention/m6/script-plan-asset-bible/preview",
        headers={"X-Client-Request-ID": "confirmed-retention"},
        json={
            "source_kind": "script",
            "source_text": IDEA_TEXT,
            "source_revision_id": projection["current_revision_id"],
            "source_revision_digest": projection["current_revision"]["source_digest"],
        },
    )
    assert preview_replay.status_code == 410
    assert "preview_run_expired" in preview_replay.text


def test_orphaned_ledger_never_blindly_redispatches_after_service_recovery(tmp_path) -> None:
    store = M6PreviewRunStore(RuntimeStore(tmp_path / "runtime"))
    queued, _ = store.create_or_load(
        "orphaned",
        owner_id="owner",
        client_request_id="queued-orphan",
        source_digest="a" * 64,
        expected_graph_version=0,
        remote_llm_enabled=True,
    )
    queued_recovery = store.recover("orphaned", queued["run_id"], owner_id="owner")
    assert queued_recovery["phase"] == "failed"
    assert queued_recovery["dispatch_count"] == 0
    assert queued_recovery["error"]["category"] == "submission_interrupted"

    running, _ = store.create_or_load(
        "orphaned",
        owner_id="owner",
        client_request_id="running-orphan",
        source_digest="b" * 64,
        expected_graph_version=0,
        remote_llm_enabled=True,
    )
    store.begin_dispatch("orphaned", running["run_id"], owner_id="owner")
    running_recovery = store.recover("orphaned", running["run_id"], owner_id="owner")
    assert running_recovery["phase"] == "failed"
    assert running_recovery["status"] == "failed_after_dispatch"
    assert running_recovery["dispatch_count"] == 1
    assert running_recovery["error"]["category"] == "dispatch_result_unrecoverable"


def test_execution_contract_is_immutable_across_gate_changes(tmp_path, monkeypatch) -> None:
    runtime_root = tmp_path / "runtime"
    store = M6PreviewRunStore(RuntimeStore(runtime_root))
    client = TestClient(create_runtime_app(runtime_root=runtime_root))
    deterministic_binding = _bind_script_revision(client, "deterministic-contract", IDEA_TEXT)
    deterministic_body = {"source_kind": "script", "source_text": IDEA_TEXT, **deterministic_binding}

    deterministic, _ = store.create_or_load(
        "deterministic-contract",
        owner_id="local-runtime-owner",
        client_request_id="deterministic-gate-flip",
        source_digest=preview_source_digest(deterministic_body),
        expected_graph_version=0,
        remote_llm_enabled=False,
    )
    monkeypatch.setattr(m6_routes, "_server_codex_m6_enabled", lambda: True)
    response = client.post(
        "/projects/deterministic-contract/m6/script-plan-asset-bible/preview",
        headers={"X-Client-Request-ID": "deterministic-gate-flip"},
        json=deterministic_body,
    )
    assert response.status_code == 200
    completed = _wait_for_phase(
        client,
        "deterministic-contract",
        deterministic["run_id"],
        "succeeded",
    )
    assert completed["provider"]["service"] == "local_deterministic"
    assert completed["dispatch_count"] == 0

    remote_binding = _bind_script_revision(client, "remote-contract", IDEA_TEXT)
    remote_body = {"source_kind": "script", "source_text": IDEA_TEXT, **remote_binding}
    remote, _ = store.create_or_load(
        "remote-contract",
        owner_id="local-runtime-owner",
        client_request_id="remote-gate-flip",
        source_digest=preview_source_digest(remote_body),
        expected_graph_version=0,
        remote_llm_enabled=True,
    )
    monkeypatch.setattr(m6_routes, "_server_codex_m6_enabled", lambda: False)
    blocked = client.post(
        "/projects/remote-contract/m6/script-plan-asset-bible/preview",
        headers={"X-Client-Request-ID": "remote-gate-flip"},
        json=remote_body,
    )
    assert blocked.status_code == 200
    assert blocked.json()["phase"] == "failed"
    assert blocked.json()["dispatch_count"] == 0
    assert blocked.json()["error"]["category"] == "text_service_failed"


def test_execution_contract_tampering_fails_before_dispatch_or_recovery(tmp_path) -> None:
    runtime_root = tmp_path / "runtime"
    client = TestClient(create_runtime_app(runtime_root=runtime_root))
    run = _start_and_wait(client, "contract-tamper", IDEA_TEXT, "contract-tamper")
    path = (
        runtime_root
        / "projects"
        / "contract-tamper"
        / "m6_preview_runs"
        / run["run_id"]
        / "run.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["provider"]["model"] = "changed-model"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    recovered = client.get(
        f"/projects/contract-tamper/m6/script-plan-asset-bible/preview-runs/{run['run_id']}",
    )
    assert recovered.status_code == 409
    assert "preview_execution_contract_mismatch" in recovered.text


def test_candidate_storage_corruption_fails_before_render_or_confirm(tmp_path) -> None:
    runtime_root = tmp_path / "runtime"
    client = TestClient(create_runtime_app(runtime_root=runtime_root))
    run = _start_and_wait(client, "corrupt", IDEA_TEXT, "corrupt-preview")
    candidate_path = (
        runtime_root
        / "projects"
        / "corrupt"
        / "m6_preview_runs"
        / run["run_id"]
        / "candidate.json"
    )
    payload = json.loads(candidate_path.read_text(encoding="utf-8"))
    payload["candidate"]["brief"]["title"] = "tampered without digest update"
    candidate_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    recovered = client.get(
        f"/projects/corrupt/m6/script-plan-asset-bible/preview-runs/{run['run_id']}",
    )
    assert recovered.status_code == 409
    assert "preview_candidate_digest_mismatch" in recovered.text
    confirmed = client.post(
        "/projects/corrupt/m6/script-plan-asset-bible/confirm",
        json={"run_id": run["run_id"], "candidate_digest": run["candidate_digest"], "expected_graph_version": 0},
    )
    assert confirmed.status_code == 409
    assert not (runtime_root / "projects" / "corrupt" / "production_graph.json").exists()


def _start_and_wait(
    client: TestClient,
    project_id: str,
    source_text: str,
    client_request_id: str,
    *,
    headers: dict[str, str] | None = None,
) -> dict:
    request_headers = {**(headers or {}), "X-Client-Request-ID": client_request_id}
    binding = _bind_script_revision(client, project_id, source_text, headers=headers)
    response = client.post(
        f"/projects/{project_id}/m6/script-plan-asset-bible/preview",
        headers=request_headers,
        json={"source_kind": "script", "source_text": source_text, **binding},
    )
    assert response.status_code == 200, response.text
    return _wait_for_phase(client, project_id, response.json()["run_id"], "succeeded", headers=request_headers)


def _wait_for_phase(
    client: TestClient,
    project_id: str,
    run_id: str,
    phase: str,
    *,
    headers: dict[str, str] | None = None,
) -> dict:
    run = {}
    for _ in range(300):
        response = client.get(
            f"/projects/{project_id}/m6/script-plan-asset-bible/preview-runs/{run_id}",
            headers=headers,
        )
        assert response.status_code == 200, response.text
        run = response.json()
        if run["phase"] == phase:
            return run
        if run["phase"] in {"succeeded", "failed", "cancelled", "confirmed"}:
            break
        time.sleep(0.01)
    raise AssertionError(run)


def _register(client: TestClient, email: str) -> dict:
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "strong-password-123",
            "display_name": email.split("@", 1)[0],
            "invite_code": "",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()
