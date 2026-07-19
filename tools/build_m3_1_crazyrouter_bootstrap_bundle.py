from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from textwrap import dedent
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DEFAULT_CANDIDATE = Path("/home/afs-ops/.codex/worktrees/afs-m3-0-zero-cost-knowledge-context-audit-20260718")
PROVIDER_CONFIG = Path("/etc/afs/providers.local.json")
M3_1_PROVIDER_CONFIG_TARGET = Path("/etc/afs/m3-1-crazyrouter.providers.json")
ENV_FILE = Path("/etc/afs/afs-runtime.env")
PYTHON = Path("/opt/afs/AgentFlowStudio/.venv/bin/python")
HARNESS_REL = Path("tools/m3_1_crazyrouter_provider_harness.py")
PROVIDER_MANIFEST_REL = Path("configs/m3_1_crazyrouter_provider.manifest.json")
RUNNER_TARGET = Path("/usr/local/sbin/afs-m3-1-crazyrouter-runner")
UNIT_TARGET = Path("/etc/systemd/system/afs-m3-1-crazyrouter.service")
SUDOERS_TARGET = Path("/etc/sudoers.d/afs-m3-1-crazyrouter")
STATE_DIR = "afs-m3-1-crazyrouter"
SERVICE_NAME = "afs-m3-1-crazyrouter.service"
EXPECTED_HOST = "api.crazyrouter.com"
EXPECTED_SERVICE_ID = "creative_script_planner"
EXPECTED_MODEL = "qwen-plus"


def main() -> int:
    args = parse_args()
    bundle = build_bundle(candidate=Path(args.candidate), output_root=Path(args.output_root))
    print(json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the non-secret M3.1 CrazyRouter admin bootstrap bundle.")
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--output-root", type=Path, default=Path("/tmp"))
    return parser.parse_args()


def build_bundle(*, candidate: Path, output_root: Path) -> dict[str, Any]:
    candidate = candidate.resolve()
    head = _git(candidate, "rev-parse", "HEAD")
    short = head[:12]
    status = _git(candidate, "status", "--porcelain")
    if status:
        raise RuntimeError("candidate worktree must be clean before bundle generation")
    harness_path = candidate / HARNESS_REL
    harness_hash = _sha256_file(harness_path)
    provider_manifest_path = candidate / PROVIDER_MANIFEST_REL
    provider_manifest_hash = _sha256_file(provider_manifest_path)
    bundle_dir = output_root.resolve() / f"afs-m3-1-crazyrouter-bootstrap-{short}"
    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    bundle_dir.mkdir(parents=True, mode=0o755)
    files = {
        "afs-m3-1-crazyrouter-runner": _runner_script(candidate, head, harness_hash),
        "afs-m3-1-crazyrouter.service": _unit_file(candidate),
        "afs-m3-1-crazyrouter.sudoers": _sudoers(),
        PROVIDER_MANIFEST_REL.name: provider_manifest_path.read_text(encoding="utf-8"),
        "install.sh": _install_script(candidate, head, harness_hash, provider_manifest_hash),
        "uninstall.sh": _uninstall_script(),
        "README.md": _readme(candidate, head, harness_hash, provider_manifest_hash),
        "manifest.json": json.dumps(_manifest(candidate, head, harness_hash, provider_manifest_hash), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    }
    for name, content in files.items():
        path = bundle_dir / name
        path.write_text(content, encoding="utf-8")
        if name.endswith(".sh") or name == "afs-m3-1-crazyrouter-runner":
            path.chmod(0o755)
        else:
            path.chmod(0o644)
    _write_sha256s(bundle_dir)
    return {
        "bundle_dir": str(bundle_dir),
        "candidate": str(candidate),
        "head": head,
        "harness_sha256": harness_hash,
        "provider_manifest_sha256": provider_manifest_hash,
        "install_command": f"sudo {bundle_dir / 'install.sh'}",
        "start_command_after_install": f"sudo -n /usr/bin/systemctl start {SERVICE_NAME}",
        "rollback_command": f"sudo {bundle_dir / 'uninstall.sh'}",
        "contains_secret": False,
    }


def _runner_script(candidate: Path, head: str, harness_hash: str) -> str:
    return dedent(
        f"""\
        #!/usr/bin/env bash
        set -euo pipefail

        CANDIDATE_DIR="{candidate}"
        EXPECTED_HEAD="{head}"
        HARNESS_PATH="$CANDIDATE_DIR/{HARNESS_REL.as_posix()}"
        EXPECTED_HARNESS_SHA256="{harness_hash}"
        PYTHON="{PYTHON}"
        PROVIDER_CONFIG="{M3_1_PROVIDER_CONFIG_TARGET}"
        EXPECTED_PROVIDER_CONFIG_SHA256="__PROVIDER_CONFIG_SHA256__"
        STATE_ROOT="${{STATE_DIRECTORY:-/var/lib/{STATE_DIR}}}"
        ARTIFACT_ROOT="$STATE_ROOT/artifacts"

        current_head="$(git -C "$CANDIDATE_DIR" rev-parse HEAD)"
        if [ "$current_head" != "$EXPECTED_HEAD" ]; then
          echo '{{"status":"blocked","reason":"candidate_head_mismatch"}}'
          exit 2
        fi
        if [ -n "$(git -C "$CANDIDATE_DIR" status --porcelain)" ]; then
          echo '{{"status":"blocked","reason":"candidate_dirty"}}'
          exit 2
        fi
        actual_hash="$(sha256sum "$HARNESS_PATH" | awk '{{print $1}}')"
        if [ "$actual_hash" != "$EXPECTED_HARNESS_SHA256" ]; then
          echo '{{"status":"blocked","reason":"harness_hash_mismatch"}}'
          exit 2
        fi
        actual_provider_hash="$(sha256sum "$PROVIDER_CONFIG" | awk '{{print $1}}')"
        if [ "$actual_provider_hash" != "$EXPECTED_PROVIDER_CONFIG_SHA256" ]; then
          echo '{{"status":"blocked","reason":"provider_manifest_hash_mismatch"}}'
          exit 2
        fi
        mkdir -p "$ARTIFACT_ROOT"
        chmod 0700 "$STATE_ROOT" "$ARTIFACT_ROOT"
        exec "$PYTHON" "$HARNESS_PATH" \\
          --provider-config "$PROVIDER_CONFIG" \\
          --artifact-root "$ARTIFACT_ROOT" \\
          --service-id "{EXPECTED_SERVICE_ID}" \\
          --expected-host "{EXPECTED_HOST}" \\
          --expected-model "{EXPECTED_MODEL}" \\
          --max-requests 8 \\
          --max-total-cost-usd 20 \\
          --max-output-tokens 6000 \\
          --max-repair-requests 2
        """
    ).replace("__PROVIDER_CONFIG_SHA256__", _sha256_file(candidate / PROVIDER_MANIFEST_REL))


def _unit_file(candidate: Path) -> str:
    return dedent(
        f"""\
        [Unit]
        Description=AFS M3.1 bounded CrazyRouter text provider harness
        Documentation=file://{candidate}/tools/m3_1_crazyrouter_provider_harness.py
        After=network-online.target
        Wants=network-online.target

        [Service]
        Type=oneshot
        User=afs-ops
        Group=afs-ops
        WorkingDirectory={candidate}
        EnvironmentFile={ENV_FILE}
        Environment=AFS_PROVIDER_CONFIG={M3_1_PROVIDER_CONFIG_TARGET}
        Environment=AFS_ALLOW_REMOTE_LLM=true
        Environment=AFS_ALLOW_REMOTE_IMAGE=false
        Environment=AFS_ALLOW_REMOTE_VIDEO=false
        Environment=AFS_ALLOW_REMOTE_AUDIO=false
        Environment=AFS_ALLOW_REMOTE_ASR=false
        Environment=AFS_ALLOW_REMOTE_VISION=false
        Environment=AFS_ALLOW_EXTERNAL_DOWNLOAD=false
        StateDirectory={STATE_DIR}
        UMask=0077
        ExecStart={RUNNER_TARGET}
        NoNewPrivileges=true
        ProtectSystem=strict
        ProtectHome=read-only
        PrivateTmp=true
        CapabilityBoundingSet=
        RestrictSUIDSGID=true
        LockPersonality=true
        RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
        TimeoutStartSec=1800

        [Install]
        WantedBy=multi-user.target
        """
    )


def _sudoers() -> str:
    return dedent(
        f"""\
        afs-ops ALL=(root) NOPASSWD: /usr/bin/systemctl start {SERVICE_NAME}, /usr/bin/systemctl stop {SERVICE_NAME}, /usr/bin/systemctl reset-failed {SERVICE_NAME}
        """
    )


def _install_script(candidate: Path, head: str, harness_hash: str, provider_manifest_hash: str) -> str:
    return dedent(
        f"""\
        #!/usr/bin/env bash
        set -euo pipefail
        if [ "$(id -u)" -ne 0 ]; then
          echo "install.sh must run as root"
          exit 2
        fi
        BUNDLE_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
        CANDIDATE_DIR="{candidate}"
        EXPECTED_HEAD="{head}"
        HARNESS_PATH="$CANDIDATE_DIR/{HARNESS_REL.as_posix()}"
        EXPECTED_HARNESS_SHA256="{harness_hash}"
        PROVIDER_MANIFEST="$CANDIDATE_DIR/{PROVIDER_MANIFEST_REL.as_posix()}"
        EXPECTED_PROVIDER_MANIFEST_SHA256="{provider_manifest_hash}"

        test -d "$CANDIDATE_DIR"
        test "$(git -C "$CANDIDATE_DIR" rev-parse HEAD)" = "$EXPECTED_HEAD"
        test -z "$(git -C "$CANDIDATE_DIR" status --porcelain)"
        test "$(sha256sum "$HARNESS_PATH" | awk '{{print $1}}')" = "$EXPECTED_HARNESS_SHA256"
        test "$(sha256sum "$PROVIDER_MANIFEST" | awk '{{print $1}}')" = "$EXPECTED_PROVIDER_MANIFEST_SHA256"
        test -f "{ENV_FILE}"
        env_mode="$(stat -c '%a %U:%G' "{ENV_FILE}")"
        test "$env_mode" = "600 root:root"
        BUNDLE_PROVIDER_MANIFEST="$BUNDLE_DIR/{PROVIDER_MANIFEST_REL.name}"
        export BUNDLE_PROVIDER_MANIFEST
        "{PYTHON}" - <<'PY'
        import json
        import os
        from pathlib import Path
        data = json.loads(Path(os.environ["BUNDLE_PROVIDER_MANIFEST"]).read_text(encoding="utf-8-sig"))
        service = data.get("services", {{}}).get("{EXPECTED_SERVICE_ID}", {{}})
        contract = service.get("m3_1_contract", {{}})
        account = data.get("accounts", {{}}).get("crazyrouter_m3_1", {{}})
        pool = data.get("account_pools", {{}}).get("creative_script_planner_pool", {{}})
        assert service.get("provider") == "openai_compatible"
        assert service.get("capability") == "llm"
        assert service.get("model") == "{EXPECTED_MODEL}"
        assert service.get("required_gate") == "AFS_ALLOW_REMOTE_LLM"
        assert service.get("max_completion_tokens") == 6000
        assert contract.get("purpose") == "bounded_creative_script_planning_text_gate"
        assert contract.get("structured_output_json") is True
        assert int(contract.get("input_token_budget") or 0) >= 7000
        assert contract.get("hard_gates", {{}}).get("llm") is True
        assert all(contract.get("hard_gates", {{}}).get(key) is False for key in ("image", "video", "audio", "asr", "vision", "external_download"))
        assert service.get("descriptor", {{}}).get("prompt_char_limit", 0) >= 12000
        assert str(account.get("base_url", "")).split("://")[-1].split("/")[0] == "{EXPECTED_HOST}"
        assert bool(account.get("api_key_env"))
        assert any(item.get("account_id") == "crazyrouter_m3_1" for item in pool.get("accounts", []))
        PY
        if command -v visudo >/dev/null 2>&1; then
          visudo -cf "$BUNDLE_DIR/afs-m3-1-crazyrouter.sudoers"
        fi
        install -o root -g root -m 0750 "$BUNDLE_DIR/afs-m3-1-crazyrouter-runner" "{RUNNER_TARGET}"
        install -o root -g root -m 0644 "$BUNDLE_DIR/afs-m3-1-crazyrouter.service" "{UNIT_TARGET}"
        install -o root -g root -m 0644 "$BUNDLE_DIR/{PROVIDER_MANIFEST_REL.name}" "{M3_1_PROVIDER_CONFIG_TARGET}"
        install -o root -g root -m 0440 "$BUNDLE_DIR/afs-m3-1-crazyrouter.sudoers" "{SUDOERS_TARGET}"
        systemctl daemon-reload
        echo "installed; not started"
        """
    )


def _uninstall_script() -> str:
    return dedent(
        f"""\
        #!/usr/bin/env bash
        set -euo pipefail
        if [ "$(id -u)" -ne 0 ]; then
          echo "uninstall.sh must run as root"
          exit 2
        fi
        systemctl stop {SERVICE_NAME} 2>/dev/null || true
        rm -f "{UNIT_TARGET}" "{RUNNER_TARGET}" "{SUDOERS_TARGET}" "{M3_1_PROVIDER_CONFIG_TARGET}"
        systemctl daemon-reload
        systemctl reset-failed {SERVICE_NAME} 2>/dev/null || true
        echo "uninstalled; evidence under /var/lib/{STATE_DIR} was preserved"
        """
    )


def _readme(candidate: Path, head: str, harness_hash: str, provider_manifest_hash: str) -> str:
    return dedent(
        f"""\
        # AFS M3.1 CrazyRouter Admin Bootstrap Bundle

        Purpose: install a bounded, auditable oneshot path for the M3.1 text-only CrazyRouter provider gate.

        Candidate:
        - path: `{candidate}`
        - exact HEAD: `{head}`
        - harness SHA256: `{harness_hash}`
        - provider manifest SHA256: `{provider_manifest_hash}`
        - provider service: `{EXPECTED_SERVICE_ID}` only; `prompt_optimizer` is intentionally rejected for this gate.

        This bundle contains no API key, token, password, provider raw output, or environment value.

        Admin install:

        ```bash
        sudo {candidate.parent.parent.parent if False else '<bundle-dir>'}/install.sh
        ```

        After install, Stage may run exactly:

        ```bash
        sudo -n /usr/bin/systemctl start {SERVICE_NAME}
        ```

        Evidence path:

        ```text
        /var/lib/{STATE_DIR}/artifacts
        ```

        Rollback:

        ```bash
        sudo <bundle-dir>/uninstall.sh
        ```

        Threat model:
        - The root-owned wrapper checks exact Git HEAD, clean worktree, and harness file hash before execution.
        - The systemd unit runs as `afs-ops`, not root.
        - `/etc/afs/afs-runtime.env` is consumed by systemd and never printed by the scripts.
        - The bundle installs a root-owned non-secret M3.1 provider manifest to `{M3_1_PROVIDER_CONFIG_TARGET}`; it does not modify `{PROVIDER_CONFIG}`.
        - Only `AFS_ALLOW_REMOTE_LLM=true` is process-local; image/video/audio/asr/vision/external download gates are forced false.
        - The harness enforces max 8 requests and USD 20 estimated budget before each call.
        - Artifacts are written under StateDirectory with UMask 0077 and reject credential-like strings.
        - The sudoers snippet allows only start/stop/reset-failed for this exact unit.
        - This does not modify or restart `afs-runtime.service`.
        """
    )


def _manifest(candidate: Path, head: str, harness_hash: str, provider_manifest_hash: str) -> dict[str, Any]:
    return {
        "artifact_type": "afs_m3_1_crazyrouter_admin_bootstrap_bundle",
        "schema_version": "afs.m3_1.bootstrap_bundle.v0.1",
        "candidate": str(candidate),
        "head": head,
        "harness_sha256": harness_hash,
        "provider_config": str(M3_1_PROVIDER_CONFIG_TARGET),
        "provider_manifest_source": PROVIDER_MANIFEST_REL.as_posix(),
        "provider_manifest_sha256": provider_manifest_hash,
        "provider_service_id": EXPECTED_SERVICE_ID,
        "env_file": str(ENV_FILE),
        "service": SERVICE_NAME,
        "runner_target": str(RUNNER_TARGET),
        "unit_target": str(UNIT_TARGET),
        "sudoers_target": str(SUDOERS_TARGET),
        "state_directory": f"/var/lib/{STATE_DIR}",
        "contains_secret": False,
        "provider_calls_started_by_bundle_generation": False,
    }


def _write_sha256s(bundle_dir: Path) -> None:
    rows = []
    for path in sorted(bundle_dir.iterdir()):
        if path.name == "SHA256SUMS":
            continue
        rows.append(f"{_sha256_file(path)}  {path.name}\n")
    sums = bundle_dir / "SHA256SUMS"
    sums.write_text("".join(rows), encoding="utf-8")
    sums.chmod(0o644)


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(cwd), *args], check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.stdout.strip()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
