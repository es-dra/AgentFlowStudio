from __future__ import annotations

import argparse
import base64
import json
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from agentflow.harness.json_io import write_json
from agentflow_studio.model_gateway.codex_image_handoff import (
    JOB_ROOT_DIR,
    REQUEST_FILENAME,
    RESULT_FILENAME,
    candidate_output_path,
    completed_result_payload,
    failed_result_payload,
)
from agentflow_studio.model_gateway.codex_runtime_env import codex_subprocess_env, prune_codex_home


class CodexImageExecutor(Protocol):
    def execute(self, request: dict[str, Any], work_dir: Path) -> Path: ...


class FakeCodexImageExecutor:
    PNG_BYTES = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
    )

    def execute(self, request: dict[str, Any], work_dir: Path) -> Path:
        candidate = work_dir / "candidate_001.png"
        candidate.write_bytes(self.PNG_BYTES)
        return candidate


class CodexExecImageExecutor:
    def __init__(self, *, cli_command: str = "codex", timeout_sec: float = 900.0) -> None:
        self.cli_command = cli_command
        self.timeout_sec = timeout_sec

    def execute(self, request: dict[str, Any], work_dir: Path) -> Path:
        work_dir = Path(work_dir).resolve()
        prompt_path = work_dir / "worker_prompt.md"
        prompt_path.write_text(_worker_prompt(request), encoding="utf-8")
        codex_env = codex_subprocess_env()
        try:
            completed = subprocess.run(
                [
                    _resolve_codex_cli_command(self.cli_command),
                    "exec",
                    "-c",
                    'approval_policy="never"',
                    "--sandbox",
                    "workspace-write",
                    "--skip-git-repo-check",
                    "--cd",
                    str(work_dir),
                    "Read worker_prompt.md in the current directory and create candidate_001.png.",
                ],
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=codex_env,
                timeout=self.timeout_sec,
                check=False,
            )
        except OSError as exc:
            raise RuntimeError("Codex image worker command is not available") from exc
        finally:
            prune_codex_home(codex_env)
        if completed.returncode != 0:
            raise RuntimeError(_safe_process_error(completed.stderr or completed.stdout))
        for candidate in (work_dir / "candidate_001.png", work_dir / "image_candidates" / "candidate_001.png"):
            if candidate.is_file():
                return candidate
        raise RuntimeError("Codex image worker did not create candidate_001.png")


@dataclass(frozen=True)
class ProcessResult:
    job_id: str
    status: str
    job_dir: Path


def process_one(root: str | Path, *, executor: CodexImageExecutor | None = None) -> ProcessResult | None:
    executor = executor or CodexExecImageExecutor()
    pending = _next_pending_job(Path(root))
    if pending is None:
        return None
    job_id = pending.name
    job_root = pending.parents[1]
    running = job_root / "running" / job_id
    running.parent.mkdir(parents=True, exist_ok=True)
    pending.rename(running)
    _append_event(job_root, job_id=job_id, status="running")
    output_dir = running.parents[2]
    try:
        request = _read_request(running)
        produced = executor.execute(request, running)
        target = candidate_output_path(output_dir)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(produced, target)
        result = completed_result_payload(job_id=job_id, output_dir=output_dir, candidate_path=target)
        write_json(running / RESULT_FILENAME, result)
        completed = job_root / "completed" / job_id
        completed.parent.mkdir(parents=True, exist_ok=True)
        running.rename(completed)
        _trim_finished_job_dir(completed)
        _append_event(job_root, job_id=job_id, status="succeeded", image_path="image_candidates/candidate_001.png")
        return ProcessResult(job_id=job_id, status="succeeded", job_dir=completed)
    except Exception as exc:  # noqa: BLE001 - worker boundary converts all failures to safe job results.
        result = failed_result_payload(job_id=job_id, reason=str(exc))
        write_json(running / RESULT_FILENAME, result)
        failed = job_root / "failed" / job_id
        failed.parent.mkdir(parents=True, exist_ok=True)
        running.rename(failed)
        _trim_finished_job_dir(failed)
        _append_event(job_root, job_id=job_id, status="failed", error_summary=result["blocks"][0]["reason"])
        return ProcessResult(job_id=job_id, status="failed", job_dir=failed)


def process_all(root: str | Path, *, executor: CodexImageExecutor | None = None, max_jobs: int | None = None) -> list[ProcessResult]:
    results: list[ProcessResult] = []
    while max_jobs is None or len(results) < max_jobs:
        result = process_one(root, executor=executor)
        if result is None:
            return results
        results.append(result)
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Process AFS Codex image handoff jobs.")
    parser.add_argument("--runtime-root", default=".", help="Runtime root or run directory to scan.")
    parser.add_argument("--executor", choices=("codex", "fake"), default="codex")
    parser.add_argument("--once", action="store_true", help="Process pending jobs once and exit.")
    parser.add_argument("--interval-sec", type=float, default=2.0)
    parser.add_argument("--max-jobs", type=int, default=None)
    args = parser.parse_args(argv)
    executor: CodexImageExecutor = FakeCodexImageExecutor() if args.executor == "fake" else CodexExecImageExecutor()
    while True:
        results = process_all(args.runtime_root, executor=executor, max_jobs=args.max_jobs)
        if args.once:
            return 0 if all(item.status == "succeeded" for item in results) else 1
        time.sleep(max(args.interval_sec, 0.2))


def _next_pending_job(root: Path) -> Path | None:
    pending_dirs: list[Path] = []
    direct = root / JOB_ROOT_DIR / "pending"
    if direct.is_dir():
        pending_dirs.append(direct)
    for path in root.rglob("pending"):
        if path.parent.name == JOB_ROOT_DIR:
            pending_dirs.append(path)
    seen: set[Path] = set()
    for pending_dir in pending_dirs:
        resolved = pending_dir.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        for job_dir in sorted(pending_dir.iterdir(), key=lambda item: item.stat().st_mtime):
            if job_dir.is_dir() and (job_dir / REQUEST_FILENAME).is_file():
                return job_dir
    return None


def _read_request(job_dir: Path) -> dict[str, Any]:
    payload = json.loads((job_dir / REQUEST_FILENAME).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise RuntimeError("request.json must be a JSON object")
    return payload


def _append_event(job_root: Path, *, job_id: str, status: str, image_path: str | None = None, error_summary: str | None = None) -> None:
    event = {
        "time": datetime.now(timezone.utc).isoformat(),
        "job_id": job_id,
        "status": status,
        "image_path": image_path,
        "error_summary": error_summary,
        "provider_raw_response_stored": False,
    }
    path = job_root / "_logs" / "events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def _trim_finished_job_dir(job_dir: Path) -> None:
    for item in Path(job_dir).iterdir():
        if item.name == RESULT_FILENAME:
            continue
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink(missing_ok=True)


def _worker_prompt(request: dict[str, Any]) -> str:
    reference_lines = "\n".join(f"- {item.get('path')}" for item in request.get("reference_images") or [])
    return (
        "You are running inside an AFS image generation job directory.\n"
        "Read request.json and create exactly one PNG image at candidate_001.png.\n"
        "Do not write provider raw responses, secrets, cookies, signed URLs, or media bytes into JSON logs.\n"
        f"Aspect ratio: {request.get('aspect_ratio')}\n"
        f"Prompt: {request.get('prompt')}\n"
        f"Reference image files:\n{reference_lines or '- none'}\n"
    )


def _resolve_codex_cli_command(cli_command: str) -> str:
    command = str(cli_command or "codex").strip() or "codex"
    path = Path(command)
    if path.anchor or "/" in command or "\\" in command:
        return command
    found = shutil.which(command)
    if found:
        return found
    local_bin_command = Path.home() / ".local" / "bin" / command
    if local_bin_command.is_file():
        return str(local_bin_command)
    return command


def _safe_process_error(value: str) -> str:
    lowered = value.lower()
    if any(term in lowered for term in ("api", "key", "secret", "token", "authorization", "cookie")):
        return "Codex image worker configuration is not ready."
    return " ".join(value.split())[:160] or "Codex image worker failed."


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = (
    "CodexExecImageExecutor",
    "FakeCodexImageExecutor",
    "ProcessResult",
    "main",
    "process_all",
    "process_one",
)
