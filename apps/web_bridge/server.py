from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from apps.web_bridge.bridge import (
    bridge_health,
    create_workflow_plan,
    list_workflows,
    refresh_run_review,
    run_status,
    start_workflow_run,
)


class BridgeRequestHandler(BaseHTTPRequestHandler):
    server_version = "NarratoCutWebBridge/0.1"

    def do_OPTIONS(self) -> None:  # noqa: N802 - stdlib handler API
        self._send_json({"status": "ok"})

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        path = urlparse(self.path).path
        if path == "/health":
            self._send_json(bridge_health())
            return
        if path == "/workflows":
            self._send_json({"workflows": list_workflows()})
            return
        if path.startswith("/runs/"):
            run_id = unquote(path.removeprefix("/runs/")).strip("/")
            self._send_json(run_status(_run_dir(run_id)))
            return
        self._send_json({"error": "not_found", "path": path}, status=404)

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        path = urlparse(self.path).path
        try:
            payload = self._read_json()
            if path == "/plans":
                self._send_json(
                    create_workflow_plan(
                        workflow_path=Path(str(payload["workflow_path"])),
                        input_path=Path(str(payload["input_path"])),
                        output_dir=_optional_path(payload.get("output_dir")),
                    )
                )
                return
            if path == "/runs":
                self._send_json(
                    start_workflow_run(
                        workflow_path=Path(str(payload["workflow_path"])),
                        input_path=Path(str(payload["input_path"])),
                        output_dir=_optional_path(payload.get("output_dir")),
                    )
                )
                return
            if path.startswith("/runs/") and path.endswith("/review"):
                run_id = unquote(path.removeprefix("/runs/").removesuffix("/review")).strip("/")
                self._send_json(refresh_run_review(_run_dir(run_id)))
                return
        except KeyError as exc:
            self._send_json({"error": "missing_field", "field": str(exc)}, status=400)
            return
        except Exception as exc:  # noqa: BLE001 - local bridge returns structured UI errors.
            self._send_json({"error": "bridge_error", "message": str(exc)}, status=500)
            return
        self._send_json({"error": "not_found", "path": path}, status=404)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - stdlib signature
        return

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        payload = json.loads(raw)
        return payload if isinstance(payload, dict) else {}

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        try:
            self.wfile.write(encoded)
        except (BrokenPipeError, ConnectionAbortedError):
            return


def serve(host: str = "127.0.0.1", port: int = 8787) -> None:
    server = ThreadingHTTPServer((host, port), BridgeRequestHandler)
    print(f"NarratoCut web bridge listening on http://{host}:{port}")
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local NarratoCut Web UI bridge.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8787, type=int)
    args = parser.parse_args()
    serve(host=args.host, port=args.port)


def _optional_path(value: object) -> Path | None:
    if value is None:
        return None
    text = str(value).strip()
    return Path(text) if text else None


def _run_dir(run_id: str) -> Path:
    path = Path(run_id)
    if path.is_absolute() or path.exists():
        return path
    return Path("data/processed/runs/web_bridge") / run_id


if __name__ == "__main__":
    main()
