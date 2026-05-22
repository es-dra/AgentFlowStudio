from __future__ import annotations


AGENTFLOW_VALIDATION_SCHEMA_VERSION = "0.1.0"

PASSED = "passed"
WARNING = "warning"
FAILED = "failed"

AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS = (
    "D:\\",
    "C:\\",
    "data/processed/runs",
    "data/raw/",
    ".mp4",
    ".mov",
    "api_key",
    "access_token",
    "refresh_token",
    "secret_key",
    "client_secret",
    "authorization:",
    "bearer ",
    "cookie=",
    "signed_url",
)

__all__ = (
    "AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS",
    "AGENTFLOW_VALIDATION_SCHEMA_VERSION",
    "FAILED",
    "PASSED",
    "WARNING",
)
