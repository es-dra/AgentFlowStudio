from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

from agentflow_studio.model_gateway.errors import ModelConfigError


VOLCENGINE_TOS_BEIJING_SUFFIX = "tos-cn-beijing.volces.com"
_DNS_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


@dataclass(frozen=True)
class ArtifactHostPolicy:
    exact_hosts: tuple[str, ...]
    bucket_host_suffixes: tuple[str, ...]

    @property
    def configured(self) -> bool:
        return bool(self.exact_hosts or self.bucket_host_suffixes)

    def allows(self, host: str) -> bool:
        normalized = _normalize_dns_name(host)
        if normalized is None:
            return False
        if normalized in self.exact_hosts:
            return True
        for suffix in self.bucket_host_suffixes:
            marker = f".{suffix}"
            if not normalized.endswith(marker):
                continue
            bucket_label = normalized[: -len(marker)]
            if bucket_label and "." not in bucket_label and _valid_dns_label(bucket_label):
                return True
        return False

    def as_task_contract(self) -> dict[str, list[str]]:
        return {
            "exact_hosts": list(self.exact_hosts),
            "bucket_host_suffixes": list(self.bucket_host_suffixes),
        }


def artifact_host_policy_from_service(service: Mapping[str, Any]) -> ArtifactHostPolicy:
    return artifact_host_policy(
        exact_hosts=service.get("allowed_artifact_hosts"),
        bucket_host_suffixes=service.get("allowed_artifact_host_suffixes"),
    )


def artifact_host_policy(
    *,
    exact_hosts: Any = None,
    bucket_host_suffixes: Any = None,
) -> ArtifactHostPolicy:
    return ArtifactHostPolicy(
        exact_hosts=_normalize_configured_names(exact_hosts, kind="exact host"),
        bucket_host_suffixes=_normalize_configured_names(
            bucket_host_suffixes,
            kind="bucket host suffix",
        ),
    )


def _normalize_configured_names(value: Any, *, kind: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)):
        raise ModelConfigError(f"Seedance artifact {kind} policy must be a list")
    normalized: list[str] = []
    for item in value:
        host = _normalize_dns_name(str(item))
        if host is None:
            raise ModelConfigError(f"Seedance artifact {kind} policy is invalid")
        if host not in normalized:
            normalized.append(host)
    return tuple(normalized)


def _normalize_dns_name(value: str) -> str | None:
    host = str(value or "").strip()
    if not host or host != host.lower() or host.endswith(".") or len(host) > 253:
        return None
    try:
        host.encode("ascii")
    except UnicodeEncodeError:
        return None
    labels = host.split(".")
    if len(labels) < 2 or any(not _valid_dns_label(label) for label in labels):
        return None
    return host


def _valid_dns_label(label: str) -> bool:
    return bool(_DNS_LABEL.fullmatch(label)) and not label.startswith("xn--")
