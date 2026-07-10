from __future__ import annotations

import re

SCHEMA_VERSION = "0.1.0"
ARTIFACT_TYPE = "agentflow_maintenance_audit_report"

DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "data/models",
    "data/processed",
    "data/raw",
    "data/reports",
    "node_modules",
}

LEGACY_FROZEN_PREFIXES = (
    "agentflow/memory/",
    "agentflow_studio/asr_sop/",
    "agentflow_studio/audio_sop/",
    "agentflow_studio/candidate_sop/",
    "agentflow_studio/highlight_sop/",
    "agentflow_studio/ocr_sop/",
    "agentflow_studio/production/",
    "agentflow_studio/slicing_sop/",
    "agentflow_studio/workflow_engine/",
    "apps/cli/production_memory_",
)

TEXT_SUFFIXES = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".jsonl",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}

LEGACY_COMPANY_PATTERNS = (
    "D:\\Learning materials\\Learning_notes" + "\\Company",
    "Company " + "source knowledge base",
)

HIGH_CONFIDENCE_SECRET_PATTERNS = (
    re.compile(r"(?<![A-Za-z0-9_])sk-[A-Za-z0-9_\-]{12,}"),
    re.compile(r"(?<![A-Za-z0-9_])AKIA[0-9A-Z]{12,}"),
    re.compile(r"BEGIN [A-Z ]*PRIVATE KEY"),
)

SAFE_HIGH_CONFIDENCE_SECRET_FIXTURE_PATTERNS = (
    re.compile(r"sk-(?:test|fixture)-[A-Za-z0-9_\-]{4,}"),
)

SECRET_FIELD_PATTERNS = (
    re.compile(r"api[_-]?key\s*(?::|=(?!=))", re.IGNORECASE),
    re.compile(r"token\s*(?::|=(?!=))", re.IGNORECASE),
    re.compile(r"cookie\s*(?::|=(?!=))", re.IGNORECASE),
    re.compile(r"signed_url\s*(?::|=(?!=))", re.IGNORECASE),
)

KNOWN_SAFE_SECRET_FIXTURES = {
    "<local-provider-key>",
    "<your-local-key>",
    "?token=secret",
    "abc123",
    "fake",
    "fake-key",
    "fake-secret-key",
    "fake-token",
    "fk-mm-key",
    "provider-secret-url",
    "signed_url=abc",
    "secret-key",
    "sk-test-secret-value",
    "token=abc",
}
