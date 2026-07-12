from __future__ import annotations

import json
from pathlib import Path

from apps.api.openapi_export import export_openapi_schema


REPO_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = REPO_ROOT / "docs" / "openapi" / "afs-runtime-service.openapi.json"


def test_committed_runtime_openapi_snapshot_matches_default_exporter(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ENABLE_LEGACY_RUNTIME_V02", raising=False)

    exported_path = export_openapi_schema(
        tmp_path / "afs-runtime-service.openapi.json",
        runtime_root=tmp_path / "runtime",
    )

    committed_schema = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    exported_schema = json.loads(exported_path.read_text(encoding="utf-8"))

    assert committed_schema == exported_schema
