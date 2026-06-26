from __future__ import annotations

from pathlib import Path


def test_runtime_auth_keeps_security_helpers_split_from_routes_and_store() -> None:
    api_root = Path("apps/api")
    auth_source = (api_root / "runtime_auth.py").read_text(encoding="utf-8")
    security_source_path = api_root / "runtime_auth_security.py"
    invites_source_path = api_root / "runtime_auth_invites.py"
    routes_source_path = api_root / "runtime_auth_routes.py"

    assert security_source_path.is_file()
    assert invites_source_path.is_file()
    assert routes_source_path.is_file()
    assert "from apps.api.runtime_auth_security import" in auth_source
    assert "from apps.api.runtime_auth_invites import" in auth_source
    for helper_name in (
        "register_runtime_auth_routes",
        "configure_runtime_auth_middleware",
        "_password_hash",
        "_verify_password",
        "_hash_text",
        "_bearer_token",
        "_session_expired",
        "_parse_datetime",
        "_now",
    ):
        assert f"def {helper_name}" not in auth_source
    security_source = security_source_path.read_text(encoding="utf-8")
    for helper_name in (
        "password_hash",
        "verify_password",
        "hash_text",
        "bearer_token",
        "session_expired",
        "now",
    ):
        assert f"def {helper_name}" in security_source
    routes_source = routes_source_path.read_text(encoding="utf-8")
    for helper_name in ("register_runtime_auth_routes", "configure_runtime_auth_middleware"):
        assert f"def {helper_name}" in routes_source
    assert "from apps.api.runtime_auth_routes import" in (api_root / "runtime_service.py").read_text(encoding="utf-8")
    invites_source = invites_source_path.read_text(encoding="utf-8")
    assert len(auth_source.splitlines()) <= 300
    assert len(invites_source.splitlines()) <= 300
    assert len(security_source.splitlines()) <= 300
    assert len(routes_source.splitlines()) <= 300
