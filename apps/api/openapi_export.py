from __future__ import annotations

import json
from pathlib import Path

from apps.api.runtime_service import DEFAULT_RUNTIME_ROOT, create_runtime_app


def export_openapi_schema(output_path: Path, runtime_root: Path = DEFAULT_RUNTIME_ROOT) -> Path:
    app = create_runtime_app(runtime_root=runtime_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(app.openapi(), ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    return output_path


__all__ = ("export_openapi_schema",)
