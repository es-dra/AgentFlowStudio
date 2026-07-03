from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from apps.api.runtime_models import PromptOptimizationRequest
from apps.api.runtime_prompt_memory_constants import PROMPT_MEMORY_NON_CLAIMS
from apps.api.runtime_store import RuntimeStore, safe_id


PROMPT_REVIEW_TEXT_LIMIT = 1200
PROMPT_REVIEW_SECRET_LABEL = (
    r"api[\s_.-]*key|access[\s_.-]*token|refresh[\s_.-]*token|"
    r"client[\s_.-]*secret|secret[\s_.-]*key|private[\s_.-]*key|provider[\s_.-]*key|"
    r"auth(?:orization)?|cookie|session|password|secret|signed[\s_.-]*url|token"
)
PROMPT_REVIEW_SECRET_KEY = rf"(?<![A-Za-z0-9_-])[\"']?(?:{PROMPT_REVIEW_SECRET_LABEL})[\"']?(?![A-Za-z0-9_-])"
PROMPT_REVIEW_SECRET_VALUE = r"(?:\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|[^\s,;}\])]+)"
PROMPT_REVIEW_SECRET_PAIR_REDACTIONS = (
    re.compile(rf"(?i)(?:auth(?:orization)?\s*(?:[:=]|\s)\s*)?bearer\s+{PROMPT_REVIEW_SECRET_VALUE}"),
    re.compile(rf"(?i){PROMPT_REVIEW_SECRET_KEY}\s*[:=]\s*{PROMPT_REVIEW_SECRET_VALUE}"),
    re.compile(rf"(?i){PROMPT_REVIEW_SECRET_KEY}\s+{PROMPT_REVIEW_SECRET_VALUE}"),
)
PROMPT_REVIEW_REDACTIONS = (
    re.compile(r"(?i)data:[^\s\"']+"),
    re.compile(r"(?i)https?://[^\s\"']+"),
    re.compile(r"(?i)(?:[a-z]:\\[^\s\"']+|/(?:home|users|tmp|var/lib/afs-runtime)/[^\s\"']+)"),
    re.compile(rf"(?i){PROMPT_REVIEW_SECRET_KEY}"),
    re.compile(r"(?i)(provider.?raw|raw.?response|raw.?payload|media.?bytes|image.?bytes|file.?bytes|data.?base64)"),
)


def prompt_optimization_review_summary(
    store: RuntimeStore,
    output_dir: Path,
    *,
    project_id: str,
    request: PromptOptimizationRequest,
    optimized_prompt: str,
) -> dict[str, Any]:
    sanitized = _sanitize_prompt_review_text(optimized_prompt)
    return {
        "artifact_type": "agentflow_prompt_optimization_review_summary",
        "schema_version": "0.1.0",
        "project_id": project_id,
        "node_id": request.node_id,
        "source_artifact_id": _runtime_artifact_id(store, output_dir / "creative_brief.json"),
        "source_artifact_role": "creative_brief",
        "source_artifact_ref": "creative_brief.json",
        "optimized_prompt_char_count": len(str(optimized_prompt or "")),
        "optimized_prompt_text": sanitized[:PROMPT_REVIEW_TEXT_LIMIT],
        "optimized_prompt_text_truncated": len(sanitized) > PROMPT_REVIEW_TEXT_LIMIT,
        "sanitization_policy": "redact_paths_urls_credentials_provider_responses_and_binary_payload_markers",
        "response_storage_policy": "provider_response_not_stored",
        "binary_payload_policy": "bytes_not_included",
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": PROMPT_MEMORY_NON_CLAIMS,
    }


def _sanitize_prompt_review_text(value: str) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    for pattern in PROMPT_REVIEW_SECRET_PAIR_REDACTIONS:
        text = pattern.sub("[redacted]", text)
    for pattern in PROMPT_REVIEW_REDACTIONS:
        text = pattern.sub("[redacted]", text)
    return text


def _runtime_artifact_id(store: RuntimeStore, path: Path) -> str:
    relative = Path(path).resolve().relative_to(store.root.resolve()).with_suffix("")
    return safe_id(str(relative))


__all__ = ("prompt_optimization_review_summary",)
