from __future__ import annotations

import os
from pathlib import Path

from apps.api.runtime_service import DEFAULT_RUNTIME_ROOT, create_runtime_app


runtime_root = Path(os.environ.get("AFS_RUNTIME_SERVICE_ROOT", str(DEFAULT_RUNTIME_ROOT)))
app = create_runtime_app(runtime_root=runtime_root)


def main() -> None:
    import uvicorn

    host = os.environ.get("AFS_RUNTIME_SERVICE_HOST", "127.0.0.1")
    port = int(os.environ.get("AFS_RUNTIME_SERVICE_PORT", "8790"))
    uvicorn.run("apps.api.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
