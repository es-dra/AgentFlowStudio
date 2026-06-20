from __future__ import annotations

import argparse


def parse_acceptance_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a safe deterministic AFS internal beta acceptance contract.")
    parser.add_argument("--runtime-root", default="", help="Optional local runtime root for deterministic in-process mode.")
    parser.add_argument("--base-url", default="", help="Optional deployed Runtime base URL for HTTP acceptance mode.")
    parser.add_argument("--invite-code", default="", help="Disposable alpha invite code for HTTP mode. Prefer the env form.")
    parser.add_argument("--invite-code-env", default="AFS_INTERNAL_BETA_ACCEPTANCE_INVITE_CODE", help="Environment variable holding the alpha invite code.")
    parser.add_argument("--beta-invite-code", default="", help="Disposable beta invite code for HTTP mode.")
    parser.add_argument("--beta-invite-code-env", default="AFS_INTERNAL_BETA_ACCEPTANCE_INVITE_CODE_BETA", help="Environment variable holding the beta invite code.")
    parser.add_argument("--preflight-only", action="store_true", help="Only inspect deployed Runtime readiness; no invite codes or provider calls.")
    parser.add_argument("--three-end-status", action="store_true", help="Run or include safe local/GitHub/server drift status.")
    parser.add_argument("--three-end-repo-root", default=".", help="Local repository root for optional three-end preflight status.")
    parser.add_argument("--three-end-server", default="", help="Optional SSH alias for server-side three-end status.")
    parser.add_argument("--public-edge-status", action="store_true", help="Include public Studio edge-auth status.")
    parser.add_argument("--public-edge-url", default="", help="Optional public Studio URL for edge-auth preflight.")
    parser.add_argument("--public-edge-server", default="", help="Optional SSH alias for Runtime health inside public-edge preflight.")
    parser.add_argument("--public-edge-check-runtime-health", action="store_true", help="Check Runtime health directly from this machine for public-edge preflight.")
    parser.add_argument("--report", default="", help="Optional JSON report output path.")
    parser.add_argument("--human-review-md", default="", help="Optional safe Markdown checklist for the human beta reviewer.")
    return parser.parse_args()
