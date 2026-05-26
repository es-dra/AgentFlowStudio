from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from narratocut.model_gateway.errors import ModelProviderError


ALLOW_REMOTE_IMAGE_ENV = "NARRATOCUT_ALLOW_REMOTE_IMAGE"
REMOTE_TRUE_VALUES = {"1", "true", "yes", "on"}


def ensure_remote_image_calls_allowed() -> None:
    value = os.environ.get(ALLOW_REMOTE_IMAGE_ENV, "").strip().lower()
    if value in REMOTE_TRUE_VALUES:
        return
    raise ModelProviderError(
        f"Remote image calls are disabled; set {ALLOW_REMOTE_IMAGE_ENV}=true to enable them"
    )


def input_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"
