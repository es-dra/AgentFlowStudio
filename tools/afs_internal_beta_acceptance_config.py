from __future__ import annotations

from dataclasses import dataclass


GENERATED_AT = "2026-06-19T12:00:00+08:00"


@dataclass(frozen=True)
class AcceptanceConfig:
    project_id: str
    generated_at: str
    alpha_invite_code: str
    beta_invite_code: str
    alpha_email: str
    beta_email: str
    password: str = "beta-acceptance-pass-123"

    @classmethod
    def deterministic(cls) -> "AcceptanceConfig":
        return cls(
            project_id="afs-beta-accept-alpha",
            generated_at=GENERATED_AT,
            alpha_invite_code="alpha-invite",
            beta_invite_code="beta-invite",
            alpha_email="alpha.beta.acceptance@example.test",
            beta_email="beta.beta.acceptance@example.test",
        )

    @classmethod
    def deployed_http(cls, *, alpha_invite_code: str, beta_invite_code: str, run_id: str) -> "AcceptanceConfig":
        return cls(
            project_id=f"afs-beta-http-{run_id}",
            generated_at=GENERATED_AT,
            alpha_invite_code=alpha_invite_code,
            beta_invite_code=beta_invite_code,
            alpha_email=f"alpha-{run_id}@afs-acceptance.example.test",
            beta_email=f"beta-{run_id}@afs-acceptance.example.test",
        )
