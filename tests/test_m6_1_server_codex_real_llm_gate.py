from __future__ import annotations

from tools import m6_1_server_codex_real_llm_gate as gate


def test_real_llm_gate_uses_durable_preview_and_confirm_contract(monkeypatch) -> None:
    posts: list[tuple[str, dict, dict]] = []
    polls = iter([
        {
            "run_id": "m6-preview-test",
            "phase": "running",
            "expected_graph_version": 3,
        },
        {
            "run_id": "m6-preview-test",
            "phase": "succeeded",
            "expected_graph_version": 3,
            "preview": {
                "candidate_digest": "a" * 64,
                "candidate": {"brief": {"title": "测试制作方案"}},
                "provider_dispatch_count": 1,
            },
        },
    ])

    def post(base_url, path, payload, *, headers=None):
        posts.append((path, payload, dict(headers or {})))
        if path.endswith("/preview"):
            return {
                "run_id": "m6-preview-test",
                "phase": "queued",
                "expected_graph_version": 3,
            }
        return {"status": "confirmed", "graph": {"version": 4}}

    monkeypatch.setattr(gate, "_post_json", post)
    monkeypatch.setattr(gate, "_get_json", lambda base_url, path: next(polls))
    monkeypatch.setattr(gate.time, "sleep", lambda seconds: None)

    preview = gate._preview(
        "http://127.0.0.1:8790/",
        "test-project",
        "idea",
        "一个可验证的制作方案输入。",
        "",
        "",
        invocation_id="invocation-a",
    )
    confirmed = gate._confirm("http://127.0.0.1:8790/", "test-project", preview)

    assert posts[0][0].endswith("/preview")
    assert posts[0][2]["X-Client-Request-ID"].startswith("m6-real-")
    assert preview["run_id"] == "m6-preview-test"
    assert preview["candidate_digest"] == "a" * 64
    assert posts[1][0].endswith("/confirm")
    assert posts[1][1] == {
        "run_id": "m6-preview-test",
        "candidate_digest": "a" * 64,
        "expected_graph_version": 3,
    }
    assert confirmed["graph"]["version"] == 4


def test_real_llm_gate_recovers_preview_by_client_without_second_post(monkeypatch) -> None:
    posts: list[tuple[str, dict]] = []
    gets: list[str] = []

    def post(base_url, path, payload, *, headers=None):
        posts.append((path, dict(headers or {})))
        raise gate.TransportInterrupted("controlled response loss")

    def get(base_url, path):
        gets.append(path)
        return {
            "run_id": "m6-preview-recovered",
            "phase": "succeeded",
            "expected_graph_version": 0,
            "preview": {
                "candidate_digest": "b" * 64,
                "candidate": {"brief": {"title": "恢复的制作方案"}},
            },
        }

    monkeypatch.setattr(gate, "_post_json", post)
    monkeypatch.setattr(gate, "_get_json", get)

    preview = gate._preview(
        "http://127.0.0.1:8790/",
        "test-project",
        "idea",
        "一个可恢复的制作方案输入。",
        "",
        "",
        invocation_id="invocation-recovery",
    )

    assert len(posts) == 1
    assert len(gets) == 1
    assert "/preview-runs/by-client/" in gets[0]
    assert gets[0].endswith(posts[0][1]["X-Client-Request-ID"])
    assert preview["run_id"] == "m6-preview-recovered"


def test_real_llm_gate_replays_same_confirm_after_transport_loss(monkeypatch) -> None:
    posts: list[dict] = []

    def post(base_url, path, payload, *, headers=None):
        posts.append(dict(payload))
        if len(posts) == 1:
            raise gate.TransportInterrupted("controlled confirm response loss")
        return {"status": "confirmed", "graph": {"version": 1, "graph_digest": "c" * 64}}

    monkeypatch.setattr(gate, "_post_json", post)
    result = gate._confirm(
        "http://127.0.0.1:8790/",
        "test-project",
        {
            "run_id": "m6-preview-confirm",
            "candidate_digest": "d" * 64,
            "expected_graph_version": 0,
        },
    )

    assert len(posts) == 2
    assert posts[0] == posts[1]
    assert result["graph"]["version"] == 1


def test_real_llm_gate_request_id_is_unique_per_invocation(monkeypatch) -> None:
    request_ids: list[str] = []

    def post(base_url, path, payload, *, headers=None):
        request_ids.append(headers["X-Client-Request-ID"])
        return {
            "run_id": f"run-{len(request_ids)}",
            "phase": "succeeded",
            "expected_graph_version": 0,
            "preview": {
                "candidate_digest": f"{len(request_ids):064x}",
                "candidate": {"brief": {"title": "隔离执行"}},
            },
        }

    monkeypatch.setattr(gate, "_post_json", post)
    for invocation_id in ("invocation-one", "invocation-two"):
        gate._preview(
            "http://127.0.0.1:8790/",
            "test-project",
            "idea",
            "同一个输入在不同 gate 执行中不能复用旧 run。",
            "",
            "",
            invocation_id=invocation_id,
        )

    assert len(set(request_ids)) == 2
