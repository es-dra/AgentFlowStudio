from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping

from agentflow_studio.domain_crew_execution import DomainCrewExecution, ExecutionDriftError


@dataclass(frozen=True)
class _Response:
    status_code: int
    payload: Any

    @property
    def text(self) -> str:
        return ""

    def json(self) -> Any:
        return self.payload


class RuntimeTransport:
    def __init__(self, base_url: str, token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._token = token

    def request(self, method: str, path: str, *, json: Mapping[str, Any] | None = None) -> _Response:
        body = None if json is None else _canonical_bytes(json)
        request = urllib.request.Request(
            self.base_url + path,
            data=body,
            method=method,
            headers={"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return _Response(response.status, _decode(response.read()))
        except urllib.error.HTTPError as exc:
            exc.read()
            return _Response(exc.code, {})


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    if _contains_token_argument(raw):
        print("Bearer tokens are accepted only through AFS_RUNTIME_BEARER_TOKEN.", file=sys.stderr)
        return 2
    parser = argparse.ArgumentParser(description="Run the provider-free authenticated domain-crew adapter.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8790")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--crew-id", required=True)
    parser.add_argument("--execution-id", required=True)
    parser.add_argument("--source-idea", required=True)
    parser.add_argument("--phase", choices=("a", "b"), required=True)
    parser.add_argument("--approved-version-id")
    args = parser.parse_args(raw)
    token = os.environ.get("AFS_RUNTIME_BEARER_TOKEN", "")
    if not token:
        print("AFS_RUNTIME_BEARER_TOKEN is required.", file=sys.stderr)
        return 2
    if args.phase == "b" and not args.approved_version_id:
        print("--approved-version-id is required for phase b.", file=sys.stderr)
        return 2
    execution = DomainCrewExecution(RuntimeTransport(args.base_url, token), project_id=args.project_id,
        crew_id=args.crew_id, execution_id=args.execution_id, source_idea=args.source_idea)
    try:
        evidence = execution.run_phase_a() if args.phase == "a" else execution.run_phase_b(
            approved_version_id=args.approved_version_id)
    except (ExecutionDriftError, ValueError):
        print("Domain-crew execution failed closed; inspect authenticated Runtime state.", file=sys.stderr)
        return 1
    print(json.dumps(evidence, sort_keys=True, separators=(",", ":")))
    return 0


def _contains_token_argument(argv: list[str]) -> bool:
    lowered = [item.lower() for item in argv]
    return any(item in {"--token", "--bearer-token", "--authorization"}
               or item.startswith(("--token=", "--bearer-token=", "--authorization="))
               or item.startswith("bearer ") for item in lowered)


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _decode(value: bytes) -> Any:
    try:
        return json.loads(value.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}


if __name__ == "__main__":
    raise SystemExit(main())
