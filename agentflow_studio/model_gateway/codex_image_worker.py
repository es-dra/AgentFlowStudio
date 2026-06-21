from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import subprocess
import time
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
from agentflow_studio.model_gateway.codex_image_worker_io import append_worker_event, trim_finished_job_dir
from agentflow_studio.model_gateway.codex_image_worker_recovery import recover_stale_running_jobs
from agentflow_studio.model_gateway.codex_image_worker_result import ProcessResult


class CodexImageExecutor(Protocol):
    def execute(self, request: dict[str, Any], work_dir: Path) -> Path: ...


CLAIM_FILENAME = "claim.json"


class FakeCodexImageExecutor:
    PNG_BYTES = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
    )

    def execute(self, request: dict[str, Any], work_dir: Path) -> Path:
        candidate = work_dir / "candidate_001.png"
        candidate.write_bytes(self.PNG_BYTES)
        return candidate


class CodexExecImageExecutor:
    def __init__(
        self,
        *,
        cli_command: str = "codex",
        timeout_sec: float = 900.0,
        poll_interval_sec: float = 2.0,
        candidate_settled_sec: float = 5.0,
    ) -> None:
        self.cli_command = cli_command
        self.timeout_sec = timeout_sec
        self.poll_interval_sec = poll_interval_sec
        self.candidate_settled_sec = candidate_settled_sec

    def execute(self, request: dict[str, Any], work_dir: Path) -> Path:
        work_dir = Path(work_dir).resolve()
        prompt_path = work_dir / "worker_prompt.md"
        prompt_path.write_text(_worker_prompt(request), encoding="utf-8")
        codex_env_source = dict(os.environ)
        codex_env_source["AFS_CODEX_HOME"] = str(work_dir / ".codex-home")
        codex_env = codex_subprocess_env(codex_env_source)
        process: subprocess.Popen[str] | None = None
        try:
            process = subprocess.Popen(
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
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=codex_env,
            )
            completed = _wait_for_codex_image_process(
                process,
                work_dir,
                timeout_sec=self.timeout_sec,
                poll_interval_sec=self.poll_interval_sec,
                candidate_settled_sec=self.candidate_settled_sec,
            )
        except OSError as exc:
            raise RuntimeError("Codex image worker command is not available") from exc
        finally:
            prune_codex_home(codex_env)
        if isinstance(completed, Path):
            return completed
        returncode, stdout, stderr = completed
        if returncode != 0:
            raise RuntimeError(_safe_process_error(stderr or stdout))
        candidate = _existing_candidate(work_dir, settled_sec=0)
        if candidate is not None:
            return candidate
        raise RuntimeError("Codex image worker did not create candidate_001.png")


def process_one(
    root: str | Path,
    *,
    executor: CodexImageExecutor | None = None,
    stale_running_sec: float = 3600.0,
    worker_id: str | None = None,
) -> ProcessResult | None:
    executor = executor or CodexExecImageExecutor()
    resolved_worker_id = worker_id or _worker_id()
    recover_stale_running_jobs(root, stale_running_sec=stale_running_sec)
    running = _claim_next_pending_job(Path(root), worker_id=resolved_worker_id)
    if running is None:
        return None
    return _process_running(running, executor, worker_id=resolved_worker_id)


def _process_running(running: Path, executor: CodexImageExecutor, *, worker_id: str) -> ProcessResult:
    job_id = running.name
    job_root = running.parents[1]
    append_worker_event(job_root, job_id=job_id, status="running", worker_id=worker_id)
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
        trim_finished_job_dir(completed)
        append_worker_event(
            job_root,
            job_id=job_id,
            status="succeeded",
            image_path="image_candidates/candidate_001.png",
            worker_id=worker_id,
        )
        return ProcessResult(job_id=job_id, status="succeeded", job_dir=completed)
    except Exception as exc:  # noqa: BLE001 - worker boundary converts all failures to safe job results.
        result = failed_result_payload(job_id=job_id, reason=str(exc))
        write_json(running / RESULT_FILENAME, result)
        failed = job_root / "failed" / job_id
        failed.parent.mkdir(parents=True, exist_ok=True)
        running.rename(failed)
        trim_finished_job_dir(failed)
        append_worker_event(
            job_root,
            job_id=job_id,
            status="failed",
            error_summary=result["blocks"][0]["reason"],
            worker_id=worker_id,
        )
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


def _claim_next_pending_job(root: Path, *, worker_id: str) -> Path | None:
    for pending in _pending_jobs(root):
        running = _try_claim_pending_job(pending, worker_id=worker_id)
        if running is not None:
            return running
    return None


def _pending_jobs(root: Path) -> list[Path]:
    pending_dirs: list[Path] = []
    jobs: list[Path] = []
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
        try:
            candidates = sorted(pending_dir.iterdir(), key=lambda item: item.stat().st_mtime)
        except FileNotFoundError:
            continue
        for job_dir in candidates:
            if job_dir.is_dir() and (job_dir / REQUEST_FILENAME).is_file():
                jobs.append(job_dir)
    return jobs


def _try_claim_pending_job(pending: Path, *, worker_id: str) -> Path | None:
    job_id = pending.name
    job_root = pending.parents[1]
    running = job_root / "running" / job_id
    running.parent.mkdir(parents=True, exist_ok=True)
    try:
        pending.rename(running)
    except (FileNotFoundError, FileExistsError):
        return None
    claim = {
        "schema_version": "afs_codex_image_claim.v0.1",
        "job_id": job_id,
        "worker_id": worker_id,
        "claimed_at": time.time(),
        "provider_raw_response_stored": False,
    }
    write_json(running / CLAIM_FILENAME, claim)
    return running


def _next_pending_job(root: Path) -> Path | None:
    jobs = _pending_jobs(root)
    return jobs[0] if jobs else None


def _read_request(job_dir: Path) -> dict[str, Any]:
    payload = json.loads((job_dir / REQUEST_FILENAME).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise RuntimeError("request.json must be a JSON object")
    return payload


def _worker_prompt(request: dict[str, Any]) -> str:
    reference_lines = "\n".join(f"- {item.get('path')}" for item in request.get("reference_images") or [])
    return (
        "You are running inside an AFS image generation job directory.\n"
        "Read request.json and create exactly one PNG image at candidate_001.png.\n"
        "Do not write provider raw responses, secrets, cookies, signed URLs, or media bytes into JSON logs.\n"
        "Follow the prompt literally. For simple subject prompts, create a clear natural depiction of the requested subject.\n"
        "If the prompt does not explicitly ask for illustration, cartoon, anime, icon, logo, mascot, or diagram style, default to a realistic photographic image with plausible texture and anatomy.\n"
        "Do not turn the subject into an icon, logo, mascot, diagram, UI element, abstract symbol, or unrelated scene unless the prompt explicitly asks for that style.\n"
        "If the prompt asks for a style, keep the subject identity, anatomy, material, and key visual traits readable.\n"
        "Create a fresh image for this specific job. Do not reuse a previous job output.\n"
        f"Non-visual job nonce, do not draw or write this text: {request.get('job_id') or 'unknown_job'}\n"
        f"Aspect ratio: {request.get('aspect_ratio')}\n"
        f"Prompt: {request.get('prompt')}\n"
        f"Reference image files:\n{reference_lines or '- none'}\n"
    )


def _wait_for_codex_image_process(
    process: subprocess.Popen[str],
    work_dir: Path,
    *,
    timeout_sec: float,
    poll_interval_sec: float,
    candidate_settled_sec: float,
) -> Path | tuple[int, str, str]:
    deadline = time.monotonic() + max(timeout_sec, 0.1)
    while True:
        candidate = _existing_candidate(work_dir, settled_sec=candidate_settled_sec)
        if candidate is not None:
            _stop_process(process)
            return candidate
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            return process.returncode or 0, stdout or "", stderr or ""
        if time.monotonic() >= deadline:
            _stop_process(process)
            candidate = _existing_candidate(work_dir, settled_sec=0)
            if candidate is not None:
                return candidate
            raise RuntimeError("Codex image worker timed out before creating a usable image")
        time.sleep(max(poll_interval_sec, 0.1))


def _stop_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
    except OSError:
        return


def _existing_candidate(work_dir: Path, *, settled_sec: float = 0) -> Path | None:
    now = time.time()
    for candidate in (work_dir / "candidate_001.png", work_dir / "image_candidates" / "candidate_001.png"):
        if not candidate.is_file():
            continue
        stat = candidate.stat()
        if stat.st_size > 0 and (settled_sec <= 0 or stat.st_mtime <= now - settled_sec):
            return candidate
    return None


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


def _worker_id() -> str:
    return f"worker-{os.getpid()}"


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = (
    "CodexExecImageExecutor",
    "FakeCodexImageExecutor",
    "ProcessResult",
    "main",
    "process_all",
    "process_one",
    "recover_stale_running_jobs",
)
