from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

try:
    from tools.maintenance_audit_policy import (
        HIGH_CONFIDENCE_SECRET_PATTERNS,
        KNOWN_SAFE_SECRET_FIXTURES,
        SECRET_FIELD_PATTERNS,
    )
except ModuleNotFoundError:
    from maintenance_audit_policy import (  # type: ignore[no-redef]
        HIGH_CONFIDENCE_SECRET_PATTERNS,
        KNOWN_SAFE_SECRET_FIXTURES,
        SECRET_FIELD_PATTERNS,
    )


def check_secret_like_fragments(root: Path, files: list[Path]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    high_confidence = 0
    for path in files:
        if path.as_posix().endswith("tests/provider_smoke_helpers.py"):
            continue
        for line_no, line in _read_lines(path):
            if any(pattern.search(line) for pattern in HIGH_CONFIDENCE_SECRET_PATTERNS):
                if _is_known_safe_high_confidence_fixture(line):
                    continue
                high_confidence += 1
                findings.append(_finding(root, path, "high-confidence secret-like fragment", line_no))
            elif (
                any(pattern.search(line) for pattern in SECRET_FIELD_PATTERNS)
                and not _is_known_safe_secret_fixture(line)
                and not _is_safe_secret_field_reference(line)
            ):
                findings.append(_finding(root, path, "secret-like or signed-url-like fragment", line_no))
    return {
        "check_id": "secret_like_fragments",
        "status": "warning" if findings else "passed",
        "count": len(findings),
        "findings": findings[:80],
        "high_confidence_count": high_confidence,
    }


def _is_known_safe_secret_fixture(line: str) -> bool:
    return any(value in line for value in KNOWN_SAFE_SECRET_FIXTURES)


def _is_known_safe_high_confidence_fixture(line: str) -> bool:
    return "sk-test-secret-value" in line


def _is_safe_secret_field_reference(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if _is_type_annotation_or_signature(stripped):
        return True
    if _is_safe_env_reference(stripped):
        return True

    match = re.search(r"(?:api[_-]?key|token|cookie|signed_url)\s*(?::|=(?!=))\s*(?P<value>.*)$", stripped, re.IGNORECASE)
    if not match:
        return False
    raw_value = match.group("value").strip()
    if _is_safe_environment_lookup(raw_value):
        return True
    if _is_safe_parameter_lookup(raw_value):
        return True

    value = _normalize_secret_field_value(raw_value)
    if not value:
        return True
    if value.lower() in {"true", "false", "null", "none", "unset"}:
        return True
    if value.startswith("<") and value.endswith(">"):
        return True
    if value.startswith(("AFS_", "OPENAI_", "KLING_", "MINIMAX_")):
        return True
    if _is_symbolic_secret_reference(value):
        return True
    return any(fixture in value for fixture in KNOWN_SAFE_SECRET_FIXTURES)


def _normalize_secret_field_value(value: str) -> str:
    normalized = value.strip().rstrip(",;")
    if "#" in normalized:
        normalized = normalized.split("#", 1)[0].strip()
    while normalized and normalized[-1] in ")]}":
        normalized = normalized[:-1].strip()
    if (normalized.startswith('"') and normalized.endswith('"')) or (
        normalized.startswith("'") and normalized.endswith("'")
    ):
        normalized = normalized[1:-1]
    return normalized.strip()


def _is_type_annotation_or_signature(line: str) -> bool:
    if "def " in line or "class " in line:
        return True
    return bool(re.search(r"(?:api[_-]?key|token|cookie|signed_url)\s*:\s*[A-Za-z_][A-Za-z0-9_ .|\[\]]+", line))


def _is_symbolic_secret_reference(value: str) -> bool:
    if '"' in value or "'" in value or "http" in value.lower():
        return False
    if re.search(r"(?<![A-Za-z0-9_])sk-", value):
        return False
    return bool(
        re.fullmatch(r"[A-Za-z_][A-Za-z0-9_(). |]*", value)
        and (
            any(token in value.lower() for token in ("api_key", "token", "cookie", "signed_url", "key_env"))
            or "(" in value
            or "." in value
        )
    )


def _is_safe_env_reference(line: str) -> bool:
    return bool(
        re.search(
            r"(?:AFS|OPENAI|KLING|MINIMAX)_[A-Z0-9_]*(?:API[_-]?KEY|TOKEN|COOKIE|SIGNED_URL)[A-Z0-9_]*\s*=\s*(?:unset|\"?<[^>]+>\"?)",
            line,
            re.IGNORECASE,
        )
    )


def _is_safe_environment_lookup(value: str) -> bool:
    return bool(
        re.search(
            r"os\.environ\.get\([\"'](?:AFS|OPENAI|KLING|MINIMAX)_[A-Z0-9_]*(?:API[_-]?KEY|TOKEN|COOKIE|SIGNED_URL)[A-Z0-9_]*[\"']\)",
            value,
            re.IGNORECASE,
        )
    )


def _is_safe_parameter_lookup(value: str) -> bool:
    return bool(re.search(r"_optional_parameter_input\([^)]*[\"'](?:api[_-]?key|token|cookie|signed_url)[\"']", value))


def _read_lines(path: Path) -> Iterable[tuple[int, str]]:
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return []
    return enumerate(lines, start=1)


def _finding(root: Path, path: Path, detail: str, line: int) -> dict[str, Any]:
    return {
        "path": path.resolve().relative_to(root).as_posix(),
        "detail": detail,
        "line": line,
    }
