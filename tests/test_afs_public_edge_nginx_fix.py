from __future__ import annotations

from pathlib import Path

from tools.afs_public_edge_nginx_fix import build_nginx_basic_auth_fix_report


NGINX_WITH_EDGE_BASIC_AUTH = """
server {
    server_name afstudio.art www.afstudio.art;

    location /ai-native-os/ {
        auth_basic off;
        alias /var/www/afstudio-art/ai-native-os/;
    }

    location / {
        auth_basic "AFS Studio Internal Test";
        auth_basic_user_file /etc/nginx/.htpasswd_afs;
        proxy_pass http://127.0.0.1:8790;
    }
}
""".lstrip()


def test_nginx_basic_auth_fix_dry_run_does_not_modify_config(tmp_path: Path) -> None:
    config_path = tmp_path / "afs-runtime"
    config_path.write_text(NGINX_WITH_EDGE_BASIC_AUTH, encoding="utf-8")

    report = build_nginx_basic_auth_fix_report(config_path=config_path)

    assert report["status"] == "ready_to_apply"
    assert report["provider_calls_started"] is False
    assert report["writes_company_kb"] is False
    assert report["writes_long_term_memory"] is False
    assert report["summary"]["target_line_count"] == 2
    assert report["summary"]["changed"] is False
    assert config_path.read_text(encoding="utf-8") == NGINX_WITH_EDGE_BASIC_AUTH


def test_nginx_basic_auth_fix_applies_backup_and_preserves_other_auth(tmp_path: Path) -> None:
    config_path = tmp_path / "afs-runtime"
    backup_path = tmp_path / "afs-runtime.bak-test"
    config_path.write_text(NGINX_WITH_EDGE_BASIC_AUTH, encoding="utf-8")

    report = build_nginx_basic_auth_fix_report(config_path=config_path, apply=True, backup_path=backup_path)

    updated = config_path.read_text(encoding="utf-8")
    assert report["status"] == "applied"
    assert backup_path.read_text(encoding="utf-8") == NGINX_WITH_EDGE_BASIC_AUTH
    assert 'auth_basic "AFS Studio Internal Test";' not in updated
    assert "auth_basic_user_file /etc/nginx/.htpasswd_afs;" not in updated
    assert "auth_basic off;" in updated
    assert "proxy_pass http://127.0.0.1:8790;" in updated


def test_nginx_basic_auth_fix_reports_already_ready_without_backup(tmp_path: Path) -> None:
    config_path = tmp_path / "afs-runtime"
    backup_path = tmp_path / "unused.bak"
    config_path.write_text(NGINX_WITH_EDGE_BASIC_AUTH.replace('auth_basic "AFS Studio Internal Test";\n        auth_basic_user_file /etc/nginx/.htpasswd_afs;\n', ""), encoding="utf-8")

    report = build_nginx_basic_auth_fix_report(config_path=config_path, apply=True, backup_path=backup_path)

    assert report["status"] == "already_ready"
    assert report["summary"]["target_line_count"] == 0
    assert not backup_path.exists()


def test_nginx_basic_auth_fix_reports_missing_config(tmp_path: Path) -> None:
    report = build_nginx_basic_auth_fix_report(config_path=tmp_path / "missing")

    assert report["status"] == "config_missing"
    assert report["summary"]["target_line_count"] == 0
