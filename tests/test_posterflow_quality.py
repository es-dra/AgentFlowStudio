from __future__ import annotations

import base64
import json
from pathlib import Path

from apps.cli.workflow_commands import run_workflow_from_cli
from narratocut.harness.inspection import inspect_run
from narratocut.harness.reviewer import review_run
from narratostudio.posterflow import provider as poster_provider


PNG_B64 = base64.b64encode(
    base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
    )
).decode("ascii")


class FakeResponse:
    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        return False

    def read(self) -> bytes:
        return json.dumps({"data": [{"b64_json": PNG_B64}, {"b64_json": PNG_B64}, {"b64_json": PNG_B64}]}).encode(
            "utf-8"
        )


def test_posterflow_review_fails_when_candidate_image_is_missing(monkeypatch, tmp_path) -> None:
    output_dir = _run_posterflow_workflow(monkeypatch, tmp_path)
    (output_dir / "image_candidates" / "candidate_001.png").unlink()

    inspection = inspect_run(output_dir)
    review = review_run(output_dir)

    assert inspection["status"] == "fail"
    assert review["status"] == "failed"
    assert "posterflow_candidate_images_exist" in _failed_ids(review)


def test_posterflow_review_fails_when_feedback_references_unknown_candidate(monkeypatch, tmp_path) -> None:
    output_dir = _run_posterflow_workflow(monkeypatch, tmp_path)
    feedback = _json(output_dir / "poster_feedback_signal_log.json")
    feedback["signals"][0]["candidate_id"] = "missing_candidate"
    (output_dir / "poster_feedback_signal_log.json").write_text(
        json.dumps(feedback, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    inspect_run(output_dir)
    review = review_run(output_dir)

    assert review["status"] == "failed"
    assert "posterflow_feedback_candidate_refs_known" in _failed_ids(review)


def test_posterflow_review_fails_when_profile_uses_unapproved_memory(monkeypatch, tmp_path) -> None:
    output_dir = _run_posterflow_workflow(monkeypatch, tmp_path)
    profile = _json(output_dir / "poster_preference_profile.json")
    profile["source_memory_candidates"].append("missing_memory_candidate")
    (output_dir / "poster_preference_profile.json").write_text(
        json.dumps(profile, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    inspect_run(output_dir)
    review = review_run(output_dir)

    assert review["status"] == "failed"
    assert "posterflow_profile_uses_accepted_memory" in _failed_ids(review)


def test_posterflow_review_fails_when_feedback_signal_replaces_raw_feedback(monkeypatch, tmp_path) -> None:
    output_dir = _run_posterflow_workflow(monkeypatch, tmp_path)
    (output_dir / "poster_feedback.jsonl").unlink()

    inspect_run(output_dir)
    review = review_run(output_dir)

    assert review["status"] == "failed"
    assert "posterflow_poster_feedback_exists" in _failed_ids(review)
    assert "posterflow_feedback_source_of_truth_is_raw_jsonl" in _failed_ids(review)


def test_posterflow_review_fails_when_memory_review_claims_durable_write(monkeypatch, tmp_path) -> None:
    output_dir = _run_posterflow_workflow(monkeypatch, tmp_path)
    review_events = _jsonl(output_dir / "poster_memory_review.jsonl")
    review_events[0]["writes_long_term_memory"] = True
    (output_dir / "poster_memory_review.jsonl").write_text(
        "\n".join(json.dumps(event, ensure_ascii=False) for event in review_events) + "\n",
        encoding="utf-8",
    )

    inspect_run(output_dir)
    review = review_run(output_dir)

    assert review["status"] == "failed"
    assert "posterflow_memory_review_no_long_term_write" in _failed_ids(review)


def test_posterflow_review_fails_when_context_trace_points_to_wrong_bundle(monkeypatch, tmp_path) -> None:
    output_dir = _run_posterflow_workflow(monkeypatch, tmp_path)
    trace = _json(output_dir / "context_assembly_trace.json")
    trace["bundle_id"] = "wrong_bundle"
    (output_dir / "context_assembly_trace.json").write_text(
        json.dumps(trace, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    inspect_run(output_dir)
    review = review_run(output_dir)

    assert review["status"] == "failed"
    assert "posterflow_context_trace_refs_bundle" in _failed_ids(review)


def _run_posterflow_workflow(monkeypatch, tmp_path) -> Path:
    def fake_urlopen(request, timeout):
        return FakeResponse()

    monkeypatch.setattr(poster_provider.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("NARRATOCUT_ALLOW_REMOTE_IMAGE", "true")
    monkeypatch.setenv("NARRATOCUT_IMAGE_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("NARRATOCUT_IMAGE_API_KEY", "secret-key")
    monkeypatch.setenv("NARRATOCUT_IMAGE_MODEL", "fake-image-model")

    output_dir = tmp_path / "poster_run"
    status, _manifest_path = run_workflow_from_cli(
        Path("workflows/posterflow_memory_demo.yaml"),
        Path("examples/posterflow/poster_brief.example.json"),
        output_dir,
    )
    assert status == "success"
    return output_dir


def _failed_ids(review: dict) -> set[str]:
    return {
        check["id"]
        for section in review["sections"]
        for check in section["checks"]
        if check["status"] == "failed"
    }


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
