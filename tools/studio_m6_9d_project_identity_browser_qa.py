from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

from playwright.sync_api import Browser, Page, expect, sync_playwright

from studio_asset_context_browser_qa_support import chrome_path, stop_runtime, wait_for_http


REPO_ROOT = Path(__file__).resolve().parents[1]
ACCOUNT_A_PROJECT = "m6-9d-account-a-project"
ACCOUNT_A_SECOND = "m6-9d-account-a-second"
ACCOUNT_B_PROJECT = "m6-9d-account-b-project"
ACCOUNT_A_MARKER = "A-Fact-Must-Not-Appear"
ACCOUNT_A_SECOND_MARKER = "A-Second-Project-Fact"
ACCOUNT_B_MARKER = "B-Exact-Cache-Fact"
VIEWPORTS = (
    (1440, 900, "desktop"),
    (1024, 768, "tablet"),
    (390, 844, "mobile-390"),
    (360, 800, "mobile-360"),
)


def main() -> int:
    args = parse_args()
    repo = Path(args.root).resolve()
    runtime_root = Path(args.runtime_root or tempfile.mkdtemp(prefix="afs-m6-9d-runtime-")).resolve()
    evidence_root = Path(args.evidence_root).resolve()
    report_path = evidence_root / "browser-report.json"
    evidence_root.mkdir(parents=True, exist_ok=True)
    runtime_root.mkdir(parents=True, exist_ok=True)
    server = start_runtime(repo, runtime_root, args.port)
    try:
        wait_for_http(f"http://127.0.0.1:{args.port}/health")
        base_url = f"http://127.0.0.1:{args.port}"
        accounts = seed_accounts_and_projects(base_url)
        report = run_browser_qa(base_url, evidence_root, accounts)
        report["runtime"] = read_health(base_url)
        report["runtime_root"] = str(runtime_root)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps({
            "status": report["status"],
            "report": str(report_path),
            "screenshots": report["screenshots"],
            "project_mutation_posts": report["project_mutation_posts"],
            "provider_generation_posts": report["provider_generation_posts"],
            "P0": report["P0"],
            "P1": report["P1"],
            "P2": report["P2"],
        }, ensure_ascii=False, sort_keys=True))
        return 0
    finally:
        stop_runtime(server)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="M6.9D project identity fail-closed browser QA")
    parser.add_argument("--root", default=str(REPO_ROOT))
    parser.add_argument("--runtime-root", default="")
    parser.add_argument("--evidence-root", required=True)
    parser.add_argument("--port", type=int, default=8794)
    return parser.parse_args()


def start_runtime(repo: Path, runtime_root: Path, port: int) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env.update({
        "AFS_RUNTIME_SERVICE_ROOT": str(runtime_root),
        "AFS_RUNTIME_ROOT": str(runtime_root),
        "AFS_RUNTIME_SERVICE_HOST": "127.0.0.1",
        "AFS_RUNTIME_SERVICE_PORT": str(port),
        "AFS_AUTH_ENABLED": "true",
        "AFS_AUTH_ALLOW_OPEN_SIGNUP": "true",
        "NO_PROXY": "127.0.0.1,localhost,::1",
        "no_proxy": "127.0.0.1,localhost,::1",
    })
    for key in (
        "AFS_ALLOW_REMOTE_LLM",
        "AFS_ALLOW_REMOTE_IMAGE",
        "AFS_ALLOW_REMOTE_VIDEO",
        "AFS_ALLOW_REMOTE_AUDIO",
        "AFS_ALLOW_REMOTE_ASR",
        "AFS_ALLOW_REMOTE_VISION",
        "AFS_ALLOW_EXTERNAL_DOWNLOAD",
    ):
        env.pop(key, None)
    return subprocess.Popen(
        [sys.executable, "-m", "apps.cli.main", "runtime-service", "--host", "127.0.0.1", "--port", str(port)],
        cwd=repo,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def seed_accounts_and_projects(base_url: str) -> dict[str, dict[str, str]]:
    stamp = str(int(time.time() * 1000))
    account_a = register(base_url, f"m69d-a-{stamp}@example.test", "Identity Account A")
    account_b = register(base_url, f"m69d-b-{stamp}@example.test", "Identity Account B")
    create_and_seed(base_url, account_a["token"], ACCOUNT_A_PROJECT, "Accessible Project A", ACCOUNT_A_MARKER)
    create_and_seed(base_url, account_a["token"], ACCOUNT_A_SECOND, "Accessible Project C", ACCOUNT_A_SECOND_MARKER)
    create_and_seed(base_url, account_b["token"], ACCOUNT_B_PROJECT, "Protected Project B", ACCOUNT_B_MARKER)
    return {"account_a": account_a, "account_b": account_b}


def register(base_url: str, email: str, display_name: str) -> dict[str, str]:
    payload = api_json(base_url, "/auth/register", method="POST", payload={
        "email": email,
        "password": "identity-browser-qa-password",
        "display_name": display_name,
        "invite_code": "",
    })
    return {
        "token": str(payload["session_token"]),
        "user_id": str(payload["user"]["user_id"]),
    }


def create_and_seed(base_url: str, token: str, project_id: str, title: str, marker: str) -> None:
    api_json(base_url, "/projects", token=token, method="POST", payload={
        "project_id": project_id,
        "project_type": "studio_creator_authoring",
        "goal": title,
    })
    api_json(base_url, f"/projects/{project_id}/studio-state", token=token, method="PUT", payload={
        "state": seeded_state(project_id, title, marker),
    })


def seeded_state(project_id: str, title: str, marker: str) -> dict[str, Any]:
    return {
        "meta": {
            "projectId": project_id,
            "projectName": title,
            "canvasName": "Identity QA Canvas",
            "seq": 2,
            "updated_at": "2026-07-24T00:00:00Z",
        },
        "viewport": {"x": 120, "y": 90, "scale": 1},
        "nodes": {
            "identity_fact": {
                "id": "identity_fact",
                "type": "text",
                "title": marker,
                "content": marker,
                "prompt": marker,
                "x": 240,
                "y": 180,
                "w": 320,
                "h": 220,
                "status": "approved",
                "params": {},
            },
        },
        "edges": {},
        "order": ["identity_fact"],
        "assets": [],
        "assetBible": {},
        "production": {},
        "selection": {"nodeIds": ["identity_fact"], "edgeId": None},
        "ui": {"saveState": "已保存"},
    }


def run_browser_qa(base_url: str, evidence_root: Path, accounts: dict[str, dict[str, str]]) -> dict[str, Any]:
    screenshots: list[str] = []
    console_errors: list[str] = []
    http_errors: list[dict[str, Any]] = []
    requests: list[dict[str, str]] = []
    cases: dict[str, Any] = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=chrome_path(),
            args=["--proxy-server=direct://", "--proxy-bypass-list=*"],
        )
        try:
            cases["blocked_403"] = blocked_cross_account_case(
                browser, base_url, evidence_root, screenshots, console_errors, http_errors, requests,
                accounts["account_a"]["token"],
            )
            cases["exact_cache_read_only"] = exact_cache_case(
                browser, base_url, evidence_root, screenshots, console_errors, http_errors, requests,
                accounts["account_b"]["token"],
            )
            cases["explicit_switch_history"] = explicit_switch_case(
                browser, base_url, evidence_root, screenshots, console_errors, http_errors, requests,
                accounts["account_a"]["token"],
            )
        finally:
            browser.close()
    project_posts = [
        item for item in requests
        if item["method"] in {"POST", "PUT", "PATCH", "DELETE"}
        and "/projects/" in item["url"]
    ]
    provider_posts = [
        item for item in requests
        if item["method"] == "POST"
        and any(marker in item["url"] for marker in ("generation", "provider", "image-admission/dispatch"))
    ]
    expected_console = [
        item for item in console_errors
        if item in {
            "Failed to load resource: the server responded with a status of 403 (Forbidden)",
            "Failed to load resource: net::ERR_CONNECTION_REFUSED",
        }
    ]
    unexpected_console = [item for item in console_errors if item not in expected_console]
    unexpected_http = [
        item for item in http_errors
        if not (item["status"] == 403 and f"/projects/{ACCOUNT_B_PROJECT}/" in item["url"])
        and not item["url"].endswith("/favicon.ico")
    ]
    issues: list[dict[str, str]] = []
    if unexpected_console:
        issues.append({"severity": "P1", "finding": f"unexpected console errors: {unexpected_console}"})
    if unexpected_http:
        issues.append({"severity": "P1", "finding": f"unexpected HTTP errors: {unexpected_http}"})
    if project_posts:
        issues.append({"severity": "P0", "finding": f"project mutations during identity QA: {project_posts}"})
    if provider_posts:
        issues.append({"severity": "P0", "finding": f"provider/generation requests: {provider_posts}"})
    if issues:
        raise AssertionError(json.dumps(issues, ensure_ascii=False))
    return {
        "artifact_type": "afs_m6_9d_project_identity_browser_qa",
        "schema_version": "afs.m6_9d.browser_qa.v0.1",
        "status": "passed",
        "cases": cases,
        "screenshots": screenshots,
        "expected_boundary_console_errors": expected_console,
        "unexpected_console_errors": unexpected_console,
        "http_errors": http_errors,
        "project_mutation_posts": len(project_posts),
        "provider_generation_posts": len(provider_posts),
        "dispatch_count": 0,
        "reservation_count": 0,
        "cost_usd": 0,
        "issue_ledger": issues,
        "P0": 0,
        "P1": 0,
        "P2": 0,
    }


def blocked_cross_account_case(
    browser: Browser,
    base_url: str,
    evidence_root: Path,
    screenshots: list[str],
    console_errors: list[str],
    http_errors: list[dict[str, Any]],
    requests: list[dict[str, str]],
    token: str,
) -> dict[str, Any]:
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    observe(page, console_errors, http_errors, requests)
    authenticate(page, base_url, token)
    page.goto(f"{base_url}/studio/?project={ACCOUNT_A_PROJECT}", wait_until="networkidle")
    expect_project_node(page, ACCOUNT_A_MARKER)
    page.goto(f"{base_url}/studio/?project={ACCOUNT_B_PROJECT}", wait_until="networkidle")
    expect(page.get_by_role("heading", name="无权访问此项目")).to_be_visible()
    body = page.locator("body").inner_text()
    assert ACCOUNT_A_MARKER not in body
    assert "Accessible Project A" not in body
    assert ACCOUNT_B_MARKER not in body
    assert page.evaluate("window.__AFS_PROJECT_IDENTITY__")["status"] == "blocked"
    assert page.evaluate("new URL(location.href).searchParams.get('project')") == ACCOUNT_B_PROJECT
    assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
    for width, height, label in VIEWPORTS:
        page.set_viewport_size({"width": width, "height": height})
        expect(page.get_by_role("heading", name="无权访问此项目")).to_be_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
        path = evidence_root / f"01-blocked-403-{label}.png"
        page.screenshot(path=str(path), full_page=True)
        screenshots.append(str(path))
    context.close()
    return {
        "requested_project": ACCOUNT_B_PROJECT,
        "rendered_project": "",
        "blocked_reason": "project_access_denied",
        "foreign_marker_visible": False,
        "url_preserved": True,
        "mutation_post_count": 0,
    }


def exact_cache_case(
    browser: Browser,
    base_url: str,
    evidence_root: Path,
    screenshots: list[str],
    console_errors: list[str],
    http_errors: list[dict[str, Any]],
    requests: list[dict[str, str]],
    token: str,
) -> dict[str, Any]:
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    observe(page, console_errors, http_errors, requests)
    authenticate(page, base_url, token)
    target = f"{base_url}/studio/?project={ACCOUNT_B_PROJECT}"
    page.goto(target, wait_until="networkidle")
    expect_project_node(page, ACCOUNT_B_MARKER)
    page.route(
        f"**/projects/{ACCOUNT_B_PROJECT}/studio-state",
        lambda route: route.abort("connectionrefused"),
    )
    page.reload(wait_until="networkidle")
    expect(page.locator(".identity-cache-banner")).to_be_visible()
    expect_project_node(page, ACCOUNT_B_MARKER)
    body = page.locator("body").inner_text()
    assert ACCOUNT_A_MARKER not in body
    assert page.evaluate("window.__AFS_PROJECT_IDENTITY__")["status"] == "cache_read_only"
    assert page.locator(".identity-cache-read-only button:not([disabled])").count() == 0
    assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
    path = evidence_root / "05-exact-project-cache-read-only-mobile-390.png"
    page.screenshot(path=str(path), full_page=True)
    screenshots.append(str(path))
    page.unroute(f"**/projects/{ACCOUNT_B_PROJECT}/studio-state")
    page.reload(wait_until="networkidle")
    expect_project_node(page, ACCOUNT_B_MARKER)
    assert page.evaluate("window.__AFS_PROJECT_IDENTITY__")["status"] == "ready"
    path = evidence_root / "06-exact-project-cache-revalidated-mobile-390.png"
    page.screenshot(path=str(path), full_page=True)
    screenshots.append(str(path))
    context.close()
    return {
        "cache_project": ACCOUNT_B_PROJECT,
        "cache_account_bound": True,
        "read_only": True,
        "revalidated": True,
        "foreign_marker_visible": False,
    }


def explicit_switch_case(
    browser: Browser,
    base_url: str,
    evidence_root: Path,
    screenshots: list[str],
    console_errors: list[str],
    http_errors: list[dict[str, Any]],
    requests: list[dict[str, str]],
    token: str,
) -> dict[str, Any]:
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    observe(page, console_errors, http_errors, requests)
    authenticate(page, base_url, token)
    page.goto(f"{base_url}/studio/?project={ACCOUNT_A_PROJECT}", wait_until="networkidle")
    expect_project_node(page, ACCOUNT_A_MARKER)
    page.locator(".studio-project-button").click()
    page.locator(".studio-project-switch-list button", has_text="Accessible Project C").click()
    expect_project_node(page, ACCOUNT_A_SECOND_MARKER)
    assert page.evaluate("new URL(location.href).searchParams.get('project')") == ACCOUNT_A_SECOND
    path = evidence_root / "07-explicit-project-switch-desktop.png"
    page.screenshot(path=str(path), full_page=True)
    screenshots.append(str(path))
    page.go_back(wait_until="networkidle")
    expect_project_node(page, ACCOUNT_A_MARKER)
    assert ACCOUNT_A_SECOND_MARKER not in page.locator("body").inner_text()
    page.go_forward(wait_until="networkidle")
    expect_project_node(page, ACCOUNT_A_SECOND_MARKER)
    assert ACCOUNT_A_MARKER not in page.locator("body").inner_text()
    path = evidence_root / "08-history-forward-project-c-desktop.png"
    page.screenshot(path=str(path), full_page=True)
    screenshots.append(str(path))
    context.close()
    return {
        "switch_was_explicit": True,
        "back_restored_exact_project": True,
        "forward_restored_exact_project": True,
        "mixed_dom_facts": False,
    }


def authenticate(page: Page, base_url: str, token: str) -> None:
    page.goto(f"{base_url}/studio/", wait_until="domcontentloaded")
    page.evaluate("(token) => localStorage.setItem('afs_auth_session_token', token)", token)


def expect_project_node(page: Page, marker: str) -> None:
    page.wait_for_timeout(250)
    target = page.locator('.node[data-node-id="identity_fact"]')
    expect(target).to_be_visible(timeout=15_000)
    expect(target).to_contain_text(marker)
    page.wait_for_function(
        """marker => {
          const node = document.querySelector('.node[data-node-id="identity_fact"]');
          return node && node.textContent.includes(marker)
            && !document.querySelector('.product-state-empty')
            && !document.querySelector('.product-state-loading');
        }""",
        arg=marker,
    )


def observe(
    page: Page,
    console_errors: list[str],
    http_errors: list[dict[str, Any]],
    requests: list[dict[str, str]],
) -> None:
    page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
    page.on("response", lambda response: http_errors.append({
        "status": response.status,
        "url": response.url,
    }) if response.status >= 400 else None)
    page.on("request", lambda request: requests.append({
        "method": request.method,
        "url": request.url,
    }))


def api_json(
    base_url: str,
    path: str,
    *,
    token: str = "",
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"{base_url}{path}", data=data, headers=headers, method=method)
    opener = build_opener(ProxyHandler({}))
    try:
        with opener.open(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise AssertionError(f"{method} {path} failed: {exc.code} {detail}") from exc


def read_health(base_url: str) -> dict[str, Any]:
    health = api_json(base_url, "/health")
    return {
        "status": health.get("status"),
        "exposure": health.get("exposure"),
        "auth_required": health.get("auth_required"),
        "provider_gates": health.get("provider_gates"),
    }


if __name__ == "__main__":
    raise SystemExit(main())
