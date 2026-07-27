from __future__ import annotations

import base64
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import Page, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
VIDEO_BYTES = base64.b64decode(
    "GkXfo59ChoEBQveBAULygQRC84EIQoKEd2VibUKHgQJChYECGFOAZwEAAAAAAAJ2"
    "EU2bdLpNu4tTq4QVSalmU6yBoU27i1OrhBZUrmtTrIHYTbuMU6uEElTDZ1OsggEe"
    "TbuMU6uEHFO7a1OsggJg7AEAAAAAAABZAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAVSalmsirXsYMPQkBNgI1MYXZmNjAuMTYuMTAwV0GNTGF2ZjYwLjE2LjEw"
    "MESJiEBpAAAAAAAAFlSua8GuAQAAAAAAADjXgQFzxYi/M570D1wDI5yBACK1nIN1"
    "bmSIgQCGhVZfVlA5g4EBI+ODhAJiWgDgibCBoLqBWpqBAhJUw2dAgHNzoGPAgGf"
    "ImkWjh0VOQ09ERVJEh41MYXZmNjAuMTYuMTAwc3PaY8CLY8WIvzOe9A9cAyNnyK"
    "VFo4dFTkNPREVSRIeYTGF2YzYwLjMxLjEwMiBsaWJ2cHgtdnA5Z8ihRaOIRFVS"
    "QVRJT05Eh5MwMDowMDowMC4yMDAwMDAwMDAAH0O2dUC254EAo9WBAACAgkmDQgAJ"
    "8AWWCjgkHBhyAADQR9j9Ygzb6cw2Dr2gAGslMWDMNQ/sM6Elcq6VDPKPDufmuVw"
    "5+LCOWEZtEOxtKusYz72cgDb8ccOpfZ1FyJVwo5WBACgAhgBAkpw8TkAAA3AAAFn"
    "5huCjlYEAUACGAECSnKxXQAADcAAAWfmG4KOVgQB4AIYAQJKceFSgAANwAABZ+Y"
    "bgo5WBAKAAhgBAkpxUUaAAA3AAAFn5huAcU7trkbuPs4EAt4r3gQHxggGk8IED"
)


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return

    def do_GET(self) -> None:
        if self.path == "/__creator_video_entry.html":
            body = _contract_html().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == (
            "/projects/browser-video-entry/approved-video-assets/"
            "video-media-approved/preview"
        ):
            body = VIDEO_BYTES
            self.send_response(200)
            self.send_header("Content-Type", "video/webm")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path in {
            "/favicon.ico",
            "/favicon.svg",
            "/projects/browser-video-entry/image-assets/keyframe-approved/preview",
        }:
            body = base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
            )
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()


def _server():
    handler = partial(QuietHandler, directory=str(ROOT))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)

    class Context:
        def __enter__(self) -> str:
            thread.start()
            return f"http://127.0.0.1:{server.server_address[1]}"

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    return Context()


def test_desktop_storyboard_and_agent_use_the_same_zero_provider_video_entry() -> None:
    with _server() as base_url:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=["--proxy-server=direct://", "--proxy-bypass-list=*"],
            )
            try:
                page = browser.new_page(viewport={"width": 1440, "height": 900})
                console_errors: list[str] = []
                page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
                page.goto(f"{base_url}/__creator_video_entry.html", wait_until="domcontentloaded")
                page.wait_for_function("window.__videoEntryReady === true")

                _assert_storyboard_entry(page)
                _assert_two_step_confirmation(page)
                assert page.evaluate("window.__calls") == {
                    "compilePreview": 1,
                    "compileConfirm": 1,
                    "reservePreview": 1,
                    "agentConversation": 0,
                    "videoDispatch": 0,
                }
                assert not console_errors

                page.reload(wait_until="domcontentloaded")
                page.wait_for_function("window.__videoEntryReady === true")
                composer = page.get_by_label("向 AI 创作搭档发送消息或命令")
                composer.fill(
                    "请为当前镜头准备生成视频：仅使用已批准关键帧和同项目参考图；"
                    "必须是 doubao-seedance-2-0 非 fast、720p、6 秒。先展示确认卡，不要自动发送。"
                )
                page.get_by_label("发送到 AI 创作搭档").click()
                page.get_by_text("当前镜头已有已批准关键帧和 3 张参考图", exact=False).wait_for()
                assert page.evaluate("window.__calls.agentConversation") == 1
                page.locator(".agent-primary-action").get_by_text("准备镜头视频").click()
                page.locator(".video-generation-setup").get_by_role(
                    "button",
                    name="预览视频准备",
                    exact=True,
                ).click()
                page.get_by_text("确认视频准备", exact=True).wait_for()
                assert page.evaluate("window.__calls.videoDispatch") == 0
                assert not console_errors
            finally:
                browser.close()


def test_approved_video_is_playable_and_consistent_across_refresh_and_views() -> None:
    with _server() as base_url:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=["--proxy-server=direct://", "--proxy-bypass-list=*"],
            )
            try:
                page = browser.new_page(viewport={"width": 1440, "height": 900})
                console_errors: list[str] = []
                page.on(
                    "console",
                    lambda message: console_errors.append(message.text)
                    if message.type in {"error", "warning"}
                    else None,
                )
                page.goto(
                    f"{base_url}/__creator_video_entry.html#approved",
                    wait_until="domcontentloaded",
                )
                page.wait_for_function("window.__videoEntryReady === true")

                approved = page.locator(".approved-shot-video").first
                assert page.locator(".studio-storyboard .approved-shot-video").count() == 1
                assert page.locator(".studio-storyboard video").count() == 1
                assert page.locator(".studio-storyboard .video-admission-panel").count() == 0
                assert approved.get_by_text("视频已保存到项目", exact=True).is_visible()
                assert approved.get_by_text("doubao-seedance-2-0", exact=True).is_visible()
                assert approved.get_by_text("首帧图生视频", exact=True).is_visible()
                assert approved.get_by_text("720p · 6.04 秒", exact=True).is_visible()
                video = approved.locator("video")
                page.wait_for_function(
                    """() => {
                      const video = document.querySelector(".approved-shot-video video");
                      return video && video.readyState >= 2 && !video.error;
                    }"""
                )
                assert video.evaluate("(element) => element.src.startsWith('blob:')")
                assert video.evaluate(
                    "(element) => element.dataset.afsMediaResolved"
                ).endswith(
                    "/projects/browser-video-entry/approved-video-assets/"
                    "video-media-approved/preview"
                )
                assert "browser-contract-token" not in page.locator("body").inner_text()
                assert not page.evaluate(
                    """() => [...document.querySelectorAll("*")].some(
                      (element) => [...element.attributes].some(
                        (attribute) => attribute.value.includes("browser-contract-token")
                      )
                    )"""
                )
                assert page.get_by_text("制作图已更新", exact=True).count() == 0
                assert page.locator(".agent-primary-action").get_by_text(
                    "播放已批准视频",
                    exact=True,
                ).is_visible()
                assert page.get_by_text(
                    "已生成媒体 1 / 3 · 已批准视频 1",
                    exact=True,
                ).is_visible()

                page.evaluate("window.__setVideoSection('asset_bible')")
                assert page.get_by_text("1 条已确认", exact=True).is_visible()
                assert page.locator(".studio-asset-bible video").count() == 0
                assert page.locator(".studio-asset-bible .video-admission-panel").count() == 0
                assert page.get_by_role(
                    "button",
                    name="在故事板播放",
                    exact=True,
                ).is_visible()
                assert page.locator(".agent-primary-action").get_by_text(
                    "播放已批准视频",
                    exact=True,
                ).is_visible()

                page.evaluate("window.__setVideoSection('canvas')")
                assert page.get_by_text("1 条视频已批准", exact=False).is_visible()
                assert page.locator(".graph-canvas-status").get_by_role(
                    "button",
                    name="播放已批准视频",
                    exact=True,
                ).is_visible()
                assert page.evaluate(
                    """() => Object.values(window.__videoStudioState.nodes).some(
                      (node) => node.type === "video"
                        && node.status === "complete"
                        && node.params?.approvedMedia?.generation_mode === "first_frame"
                        && node.previewUrl.startsWith("/projects/browser-video-entry/")
                    )"""
                )

                page.evaluate("window.__refreshVideoEntry()")
                page.wait_for_function(
                    """() => {
                      const video = document.querySelector(".approved-shot-video video");
                      return video && video.readyState >= 2 && !video.error;
                    }"""
                )
                assert page.get_by_text("视频已保存到项目", exact=True).first.is_visible()
                page.evaluate("window.__setVideoSection('storyboard')")
                page.locator(".storyboard-heading-actions").get_by_role(
                    "button",
                    name="准备叙事镜头对照",
                    exact=True,
                ).click()
                comparison_setup = page.locator(".video-generation-setup")
                assert comparison_setup.is_visible()
                assert comparison_setup.get_by_label(
                    "视频生成方式"
                ).input_value() == "reference_conditioned"
                assert comparison_setup.get_by_text(
                    "使用批准资产约束身份与连续性，不锁定首帧。",
                    exact=True,
                ).is_visible()
                comparison_setup.get_by_role(
                    "button",
                    name="准备叙事镜头对照",
                    exact=True,
                ).click()
                comparison_review = page.locator(".image-admission-review")
                comparison_review.get_by_text(
                    "确认建立叙事镜头对照",
                    exact=True,
                ).wait_for()
                assert comparison_review.get_by_text(
                    "旧批准视频保持不变",
                    exact=False,
                ).is_visible()
                assert comparison_review.get_by_text(
                    "首帧：不发送",
                    exact=False,
                ).is_visible()
                assert comparison_review.get_by_text(
                    "实际发送参考图：3 张",
                    exact=False,
                ).is_visible()
                comparison_review.get_by_role(
                    "button",
                    name="确认",
                    exact=True,
                ).click()
                reserve = page.get_by_role(
                    "button",
                    name="预览并确认生成",
                    exact=True,
                )
                reserve.wait_for()
                reserve.click()
                final_review = page.locator(".image-admission-review")
                final_review.get_by_text(
                    "确认发送镜头 01 视频",
                    exact=True,
                ).wait_for()
                assert final_review.get_by_text(
                    "doubao-seedance-2-0（非 fast）",
                    exact=False,
                ).is_visible()
                assert final_review.get_by_text(
                    "720p · 6 秒 · 参考图约束视频",
                    exact=False,
                ).is_visible()
                assert final_review.get_by_text(
                    "1 次发送 · 自动重试 0 · $2.00 项目停止线",
                    exact=False,
                ).is_visible()
                assert final_review.get_by_text(
                    "首帧：不发送",
                    exact=False,
                ).is_visible()
                assert final_review.get_by_text(
                    "实际发送参考图：3 张",
                    exact=False,
                ).is_visible()
                assert final_review.get_by_role(
                    "button",
                    name="确认并发送",
                    exact=True,
                ).is_visible()
                assert page.evaluate("window.__calls.videoDispatch") == 0
                assert page.evaluate("window.__sideEffects.generateVideo") == 0
                assert not console_errors
            finally:
                browser.close()


def test_resize_observer_notification_is_not_reported_as_an_afs_error() -> None:
    with _server() as base_url:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=["--proxy-server=direct://", "--proxy-bypass-list=*"],
            )
            try:
                page = browser.new_page(viewport={"width": 1440, "height": 900})
                console_errors: list[str] = []
                page.on(
                    "console",
                    lambda message: console_errors.append(message.text)
                    if message.type == "error"
                    else None,
                )
                page.goto(
                    f"{base_url}/__creator_video_entry.html",
                    wait_until="domcontentloaded",
                )
                page.wait_for_function("window.__videoEntryReady === true")
                result = page.evaluate(
                    """async () => {
                      const module = await import(
                        "/apps/studio/src/client-error-reporter.js"
                      );
                      const events = [];
                      module.installClientErrorReporter({
                        getRuntime: () => ({
                          projectId: "browser-video-entry",
                          recordClientEvent: async (event) => events.push(event),
                        }),
                        getProjectId: () => "browser-video-entry",
                      });
                      const notification = new ErrorEvent("error", {
                        message: "ResizeObserver loop completed with undelivered notifications.",
                        cancelable: true,
                      });
                      const notificationAccepted = window.dispatchEvent(notification);
                      await new Promise((resolve) => setTimeout(resolve, 0));
                      const notificationEventCount = events.length;
                      window.dispatchEvent(new ErrorEvent("error", {
                        message: "TypeError: actual product failure",
                        cancelable: true,
                      }));
                      await new Promise((resolve) => setTimeout(resolve, 0));
                      const sameMessageError = new Error(
                        "ResizeObserver loop completed with undelivered notifications."
                      );
                      window.dispatchEvent(new ErrorEvent("error", {
                        message: sameMessageError.message,
                        error: sameMessageError,
                        filename: "/apps/studio/src/product-shell.js",
                        lineno: 42,
                        colno: 7,
                        cancelable: true,
                      }));
                      await new Promise((resolve) => setTimeout(resolve, 0));
                      return {
                        notificationAccepted,
                        defaultPrevented: notification.defaultPrevented,
                        notificationEventCount,
                        finalEventCount: events.length,
                        finalEventMessage: events[0]?.message || "",
                        sameMessageEvent: events[1]?.message || "",
                        exactClassifier: module.isNonActionableBrowserNotification(
                          "ResizeObserver loop limit exceeded"
                        ),
                        sameMessageErrorClassifier:
                          module.isNonActionableBrowserNotification({
                            message: sameMessageError.message,
                            error: sameMessageError,
                            lineno: 42,
                            colno: 7,
                          }),
                        realErrorClassifier: module.isNonActionableBrowserNotification(
                          "TypeError: actual product failure"
                        ),
                      };
                    }"""
                )
                assert result == {
                    "notificationAccepted": False,
                    "defaultPrevented": True,
                    "notificationEventCount": 0,
                    "finalEventCount": 2,
                    "finalEventMessage": "TypeError: actual product failure",
                    "sameMessageEvent": (
                        "ResizeObserver loop completed with undelivered notifications."
                    ),
                    "exactClassifier": True,
                    "sameMessageErrorClassifier": False,
                    "realErrorClassifier": False,
                }
                assert len(console_errors) == 2
                assert all(item.startswith("studio_client_error ") for item in console_errors)
                assert "actual product failure" in console_errors[0]
                assert "ResizeObserver loop completed" in console_errors[1]
            finally:
                browser.close()


def test_approved_ledger_without_graph_media_does_not_become_a_second_ui_truth() -> None:
    with _server() as base_url:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=["--proxy-server=direct://", "--proxy-bypass-list=*"],
            )
            try:
                page = browser.new_page(viewport={"width": 1440, "height": 900})
                console_errors: list[str] = []
                page.on(
                    "console",
                    lambda message: console_errors.append(message.text)
                    if message.type in {"error", "warning"}
                    else None,
                )
                page.goto(
                    f"{base_url}/__creator_video_entry.html#approved-mismatch",
                    wait_until="domcontentloaded",
                )
                page.wait_for_function("window.__videoEntryReady === true")

                assert page.locator(".approved-shot-video").count() == 0
                assert page.get_by_text("批准记录需要核对", exact=True).is_visible()
                assert page.get_by_text(
                    "当前制作图没有可验证的对应视频结果",
                    exact=False,
                ).is_visible()
                assert page.locator(".agent-primary-action").get_by_text(
                    "播放已批准视频",
                    exact=True,
                ).count() == 0
                assert not page.evaluate(
                    """() => Object.values(window.__videoStudioState.nodes).some(
                      (node) => node.type === "video"
                        && node.params?.productionGraphProjection
                    )"""
                )
                assert page.evaluate("window.__calls.videoDispatch") == 0
                assert page.evaluate("window.__sideEffects.generateVideo") == 0
                assert not console_errors
            finally:
                browser.close()


def test_rejected_round_builds_a_new_reference_manifest_without_dispatch() -> None:
    with _server() as base_url:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=["--proxy-server=direct://", "--proxy-bypass-list=*"],
            )
            try:
                page = browser.new_page(viewport={"width": 1440, "height": 900})
                console_errors: list[str] = []
                page.on(
                    "console",
                    lambda message: console_errors.append(message.text)
                    if message.type == "error"
                    else None,
                )
                page.goto(
                    f"{base_url}/__creator_video_entry.html#rejected",
                    wait_until="domcontentloaded",
                )
                page.wait_for_function("window.__videoEntryReady === true")
                panel = page.locator(".video-admission-panel")
                assert panel.get_by_text("上一次发送被上游拒绝", exact=True).is_visible()
                page.get_by_role(
                    "button",
                    name="建立新的单次视频清单",
                    exact=True,
                ).click()
                page.get_by_text("确认建立新的单次视频清单", exact=True).wait_for()
                review = page.locator(".image-admission-review")
                assert review.get_by_text("旧失败清单和唯一一次发送记录保持不变", exact=False).is_visible()
                assert review.get_by_text("实际发送参考图：3 张", exact=False).is_visible()
                assert review.get_by_text("参考图约束视频", exact=False).is_visible()
                page.get_by_role("button", name="确认", exact=True).click()
                page.get_by_role("button", name="预览并确认生成", exact=True).wait_for()
                assert panel.get_by_text("实际发送参考图").is_visible()
                assert page.evaluate("window.__calls.videoDispatch") == 0
                assert page.evaluate("window.__sideEffects.generateVideo") == 0
                assert not console_errors
            finally:
                browser.close()


def test_refreshed_planned_manifest_reopens_final_confirmation_without_reserving() -> None:
    with _server() as base_url:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=["--proxy-server=direct://", "--proxy-bypass-list=*"],
            )
            try:
                page = browser.new_page(viewport={"width": 1440, "height": 900})
                console_errors: list[str] = []
                page.on(
                    "console",
                    lambda message: console_errors.append(message.text)
                    if message.type == "error"
                    else None,
                )
                page.goto(
                    f"{base_url}/__creator_video_entry.html#planned",
                    wait_until="domcontentloaded",
                )
                page.wait_for_function("window.__videoEntryReady === true")

                page.evaluate("window.__refreshVideoEntry()")
                assert page.locator("#product-main").get_by_role(
                    "button",
                    name="确认镜头视频",
                    exact=True,
                ).is_visible()
                assert page.locator(".agent-primary-action").get_by_text(
                    "确认镜头视频",
                    exact=True,
                ).is_visible()
                page.evaluate(
                    """() => {
                      const button = [...document.querySelectorAll("button")]
                        .find((item) => item.textContent.trim() === "预览并确认生成");
                      button.replaceWith(button.cloneNode(true));
                    }"""
                )
                page.evaluate("window.__deferReservePreview = true")
                page.get_by_role(
                    "button",
                    name="预览并确认生成",
                    exact=True,
                ).click()
                assert page.get_by_role(
                    "button",
                    name="正在准备最终确认…",
                    exact=True,
                ).is_disabled()
                assert page.evaluate("window.__calls") == {
                    "compilePreview": 0,
                    "compileConfirm": 0,
                    "reservePreview": 1,
                    "agentConversation": 0,
                    "videoDispatch": 0,
                }
                assert page.evaluate("window.__sideEffects") == {
                    "reserveConfirm": 0,
                    "persistedWrites": 0,
                    "preflightVideo": 0,
                    "generateVideo": 0,
                }
                assert page.evaluate("window.__persistedVideoState()") == {
                    "status": "locked",
                    "itemState": "planned",
                    "reserved": 0,
                    "remaining": 1,
                    "dispatches": 0,
                }
                page.evaluate("window.__releaseReservePreview()")
                page.get_by_text("确认发送镜头 01 视频", exact=True).wait_for()
                assert page.get_by_role(
                    "button",
                    name="确认并发送",
                    exact=True,
                ).is_visible()
                assert page.evaluate("window.__sideEffects") == {
                    "reserveConfirm": 0,
                    "persistedWrites": 0,
                    "preflightVideo": 0,
                    "generateVideo": 0,
                }
                assert page.evaluate("window.__persistedVideoState()") == {
                    "status": "locked",
                    "itemState": "planned",
                    "reserved": 0,
                    "remaining": 1,
                    "dispatches": 0,
                }
                assert page.evaluate("window.__calls.videoDispatch") == 0
                assert not console_errors
            finally:
                browser.close()


def test_stale_video_manifest_rebuilds_current_version_before_final_confirmation() -> None:
    with _server() as base_url:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=["--proxy-server=direct://", "--proxy-bypass-list=*"],
            )
            try:
                page = browser.new_page(viewport={"width": 1440, "height": 900})
                console_errors: list[str] = []
                page.on(
                    "console",
                    lambda message: console_errors.append(message.text)
                    if message.type == "error"
                    else None,
                )
                page.goto(
                    f"{base_url}/__creator_video_entry.html#stale",
                    wait_until="domcontentloaded",
                )
                page.wait_for_function("window.__videoEntryReady === true")

                main_action = page.locator(".storyboard-heading-actions").get_by_role(
                    "button",
                    name="按当前版本重新准备",
                    exact=True,
                )
                assert main_action.is_visible()
                assert page.locator(".agent-primary-action").get_by_text(
                    "按当前版本重新准备",
                    exact=True,
                ).is_visible()
                panel = page.locator(".video-admission-panel")
                assert panel.get_by_text("制作图已更新", exact=True).is_visible()
                assert panel.get_by_text(
                    "旧视频准备基于 v14；当前制作图为 v15",
                    exact=False,
                ).is_visible()
                assert panel.get_by_text(
                    "镜头 01 的画面语义未变化",
                    exact=False,
                ).is_visible()
                page.evaluate("window.__deferRecompilePreview = true")
                main_action.click()
                setup = page.locator(".video-generation-setup")
                assert setup.get_by_label(
                    "视频生成方式"
                ).input_value() == "reference_conditioned"
                setup.get_by_role(
                    "button",
                    name="按当前版本重新准备",
                    exact=True,
                ).click()
                assert panel.get_by_role(
                    "button",
                    name="正在准备…",
                    exact=True,
                ).is_disabled()
                assert page.evaluate("window.__rebuildEffects") == {
                    "recompilePreview": 1,
                    "recompileConfirm": 0,
                    "oldManifestArchived": 0,
                }
                page.evaluate("window.__releaseRecompilePreview()")
                page.get_by_text("确认按当前版本重新准备", exact=True).wait_for()
                assert page.get_by_text(
                    "旧视频准备将保留在历史记录；新清单基于 v15",
                    exact=False,
                ).is_visible()
                assert page.get_by_text("角色甲、月台甲、怀表甲").is_visible()
                page.get_by_role("button", name="确认", exact=True).click()

                page.get_by_role(
                    "button",
                    name="预览并确认生成",
                    exact=True,
                ).wait_for()
                assert page.evaluate("window.__rebuildEffects") == {
                    "recompilePreview": 1,
                    "recompileConfirm": 1,
                    "oldManifestArchived": 1,
                }
                page.get_by_role(
                    "button",
                    name="预览并确认生成",
                    exact=True,
                ).click()
                page.get_by_text("确认发送镜头 01 视频", exact=True).wait_for()
                final_card = page.locator(".image-admission-review")
                for text in (
                    "doubao-seedance-2-0（非 fast）",
                    "720p",
                    "6 秒",
                    "1 次发送",
                    "自动重试 0",
                    "$2.00 项目停止线",
                    "角色甲、月台甲、怀表甲",
                ):
                    assert final_card.get_by_text(text, exact=False).is_visible()
                assert page.get_by_role(
                    "button",
                    name="确认并发送",
                    exact=True,
                ).is_visible()
                assert page.evaluate("window.__calls.videoDispatch") == 0
                assert page.evaluate("window.__sideEffects") == {
                    "reserveConfirm": 0,
                    "persistedWrites": 0,
                    "preflightVideo": 0,
                    "generateVideo": 0,
                }
                assert not console_errors
            finally:
                browser.close()


def _assert_storyboard_entry(page: Page) -> None:
    main_entry = page.locator("#product-main").get_by_role(
        "button",
        name="准备镜头视频",
        exact=True,
    )
    assert main_entry.count() == 1
    assert main_entry.is_visible()
    assert page.locator(".agent-primary-action").get_by_text("准备镜头视频").is_visible()
    assert page.get_by_text("镜头 01").first.is_visible()
    assert page.get_by_text("已生成媒体 1 / 3").is_visible()
    page.wait_for_function(
        "document.querySelector('.shot-media img')?.naturalWidth > 0"
    )
    page.evaluate("window.__deferCompilePreview = true")
    main_entry.click()
    setup = page.locator(".video-generation-setup")
    assert setup.is_visible()
    assert setup.get_by_label("视频生成方式").input_value() == "reference_conditioned"
    for label in (
        "主体动作弧",
        "空间位移",
        "互动对象",
        "镜头运动",
        "环境动态",
        "节奏",
        "起始状态",
        "结束状态",
        "叙事目的",
    ):
        assert setup.get_by_label(label).input_value()
    setup.get_by_role("button", name="预览视频准备", exact=True).click()
    assert setup.get_by_role(
        "button",
        name="正在准备…",
        exact=True,
    ).is_visible()
    assert page.locator(".video-admission-panel").is_visible()
    assert page.evaluate("window.__calls.compilePreview") == 1
    page.evaluate("window.__releaseCompilePreview()")
    page.get_by_text("确认视频准备", exact=True).wait_for()
    assert page.get_by_text("参考图约束视频", exact=False).last.is_visible()
    assert page.get_by_text("角色甲、月台甲、怀表甲").is_visible()
    assert page.evaluate("window.__calls.videoDispatch") == 0


def _assert_two_step_confirmation(page: Page) -> None:
    page.get_by_role("button", name="确认", exact=True).click()
    assert page.locator("#product-main").get_by_role(
        "button",
        name="确认镜头视频",
        exact=True,
    ).is_visible()
    page.locator(".agent-primary-action").get_by_text("确认镜头视频").wait_for()
    page.get_by_role("button", name="预览并确认生成").click()
    page.get_by_text("确认发送镜头 01 视频", exact=True).wait_for()
    card = page.locator(".image-admission-review")
    for text in (
        "doubao-seedance-2-0（非 fast）",
        "720p",
        "6 秒",
        "1 次发送",
        "自动重试 0",
        "$2.00 项目停止线",
        "角色甲、月台甲、怀表甲",
    ):
        assert card.get_by_text(text, exact=False).is_visible()
    assert page.get_by_role("button", name="确认并发送").is_visible()
    assert page.evaluate("window.__calls.videoDispatch") == 0


def _contract_html() -> str:
    return r"""
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link rel="stylesheet" href="/apps/studio/styles/tokens.css" />
    <link rel="stylesheet" href="/apps/studio/styles/base.css" />
    <link rel="stylesheet" href="/apps/studio/styles/shell.css" />
    <link rel="stylesheet" href="/apps/studio/styles/product-shell.css" />
    <link rel="stylesheet" href="/apps/studio/styles/asset-bible.css" />
    <title>Creator Video Entry Contract</title>
  </head>
  <body>
    <div id="app" class="product-mode">
      <div id="product-shell-root"></div>
      <div id="overlay-root"></div>
    </div>
    <script type="module">
      import { createProductShell } from "/apps/studio/src/product-shell.js";

      localStorage.setItem("afs_auth_session_token", "browser-contract-token");
      window.__calls = {
        compilePreview: 0,
        compileConfirm: 0,
        reservePreview: 0,
        agentConversation: 0,
        videoDispatch: 0,
      };
      window.__sideEffects = {
        reserveConfirm: 0,
        persistedWrites: 0,
        preflightVideo: 0,
        generateVideo: 0,
      };
      window.__rebuildEffects = {
        recompilePreview: 0,
        recompileConfirm: 0,
        oldManifestArchived: 0,
      };
      const projectId = "browser-video-entry";
      const approvedLedgerState = ["#approved", "#approved-mismatch"].includes(window.location.hash);
      const approvedGraphState = window.location.hash === "#approved";
      const bible = {
        schema_version: "afs.asset_bible.v0.1",
        status: "locked",
        version: 9,
        current_revision_id: "asset-bible-r9",
        locked_revision_id: "asset-bible-r9",
        candidate_set: {
          script_revision_id: "script-r1",
          scene_count: 1,
          shot_count: 3,
        },
        art_direction: {
          visual_style: "写实电影",
          medium: "电影摄影",
          palette: "冷暖对比",
          lighting: "月台侧光",
          confirmed_at: "2026-07-26T00:00:00Z",
        },
        recognition_quality: { status: "pass", issues: [] },
        coverage: {
          coverage_pass: true,
          quality_pass: true,
          scene_total: 1,
          scene_covered: 1,
          shot_total: 3,
          shot_covered: 3,
          unresolved_required: 0,
        },
        assets: [
          {
            stable_id: "character-01", asset_type: "character", display_name: "角色甲", review_state: "approved",
            visual_identity: "稳定面部轮廓", positive_traits: ["深灰外套"], pending_fields: [],
            continuity_states: [{ label: "造型连续", status: "confirmed" }],
            occurrences: { scene_ids: ["scene-01"], shot_ids: ["shot-01", "shot-02", "shot-03"] },
          },
          {
            stable_id: "scene-01", asset_type: "scene", display_name: "月台甲", review_state: "approved",
            visual_identity: "旧站月台空间", positive_traits: ["黄昏侧光"], pending_fields: [],
            continuity_states: [{ label: "空间连续", status: "confirmed" }],
            occurrences: { scene_ids: ["scene-01"], shot_ids: ["shot-01", "shot-02", "shot-03"] },
          },
          {
            stable_id: "prop-01", asset_type: "prop", display_name: "怀表甲", review_state: "approved",
            visual_identity: "蓝铜表壳", positive_traits: ["明确氧化纹理"], pending_fields: [],
            continuity_states: [{ label: "道具连续", status: "confirmed" }],
            occurrences: { scene_ids: ["scene-01"], shot_ids: ["shot-01", "shot-02", "shot-03"] },
          },
        ],
      };
      const workspace = {
        status: "ready",
        project_id: projectId,
        graph_version: approvedGraphState ? 16 : 14,
        graph_digest: approvedGraphState ? "graph-v16" : "graph-v14",
        storyboard: {
          graph_version: approvedGraphState ? 16 : 14,
          graph_digest: approvedGraphState ? "graph-v16" : "graph-v14",
        },
        sequence: {
          script_revisions: [{ node_id: "script-r1", state: "active", metadata: { source_digest: "source" } }],
          sequences: [{ node_id: "sequence-01", state: "active", metadata: { name: "制作序列" } }],
          characters: [{ node_id: "character-01", state: "active", metadata: { display_name: "角色甲" } }],
          scenes: [{ node_id: "scene-01", state: "active", metadata: { name: "月台甲" } }],
          props: [{ node_id: "prop-01", state: "active", metadata: { display_name: "怀表甲" } }],
          reference_sets: [],
          production_aids: [],
          shots: [
            { node_id: "shot-01", state: "active", metadata: { title: "镜头 01", duration_seconds: 6, intent: "推进到怀表" } },
            { node_id: "shot-02", state: "active", metadata: { title: "镜头 02", duration_seconds: 7, intent: "修复过程" } },
            { node_id: "shot-03", state: "active", metadata: { title: "镜头 03", duration_seconds: 5, intent: "完成修复" } },
          ],
          approved_media: [
            {
              media_node_id: "approved-shot-01",
              media_kind: "image",
              preview_url: "/projects/browser-video-entry/image-assets/keyframe-approved/preview",
              target_node_ids: ["shot-01"],
            },
            ...(approvedGraphState ? [{
              media_node_id: "approved-video-shot-01",
              media_kind: "video",
              preview_url: "/projects/browser-video-entry/approved-video-assets/video-media-approved/preview",
              mime_type: "video/webm",
              container: "video/webm",
              width: 1280,
              height: 720,
              duration_sec: 6.04,
              codec: "vp9",
              model: "doubao-seedance-2-0",
              resolution: "720p",
              generation_mode: "first_frame",
              approval_graph_version: 16,
              target_node_ids: ["shot-01"],
              lineage: {
                source_kind: "approved_video_receipt",
                target_relation: "approved_video",
              },
            }] : []),
          ],
          dependencies: [
            { from_id: "scene-01", to_id: "shot-01", relation_type: "contains" },
            { from_id: "scene-01", to_id: "shot-02", relation_type: "contains" },
            { from_id: "scene-01", to_id: "shot-03", relation_type: "contains" },
            ...(approvedGraphState ? [{
              from_id: "shot-01",
              to_id: "approved-video-shot-01",
              relation_type: "approved_video",
            }] : []),
          ],
          tasks: [],
          candidates: [],
          selections: [],
          reviews: [],
          delivery_plan: [],
          version_history: [],
        },
      };
      const source = {
        production_graph: { version: 14, graph_digest: "graph-v14" },
        shot: { shot_id: "shot-01", label: "镜头 01" },
        keyframe: {
          image_asset_id: "keyframe-approved",
          label: "已批准关键帧",
          aspect_ratio: "16:9",
        },
        references: [
          { image_asset_id: "character-image", label: "角色甲" },
          { image_asset_id: "scene-image", label: "月台甲" },
          { image_asset_id: "prop-image", label: "怀表甲" },
        ],
        prompt_contract: {
          provider_prompt: "角色甲在月台甲修复怀表甲，镜头缓慢推进。",
          camera_movement: "缓慢推进",
        },
        generation_mode: {
          mode: "reference_conditioned",
          label: "参考图约束视频",
          selection_reason: "使用批准资产约束身份与连续性，不锁定首帧。",
        },
        temporal_staging: {
          subject_action_arc: "角色甲拿起怀表，打开后盖并完成一次校准",
          spatial_displacement: "角色从长椅一端起身移向月台工作灯",
          interaction_object: "双手持续操作怀表与修表工具",
          camera_movement: "镜头平稳侧移并在校准完成时停住",
          environment_dynamics: "远处蒸汽掠过月台，灯光随列车震动轻晃",
          pacing: "前段克制，中段加快，结尾停顿",
          start_state: "角色独坐月台检查无法走动的怀表",
          end_state: "怀表重新走动，角色抬头望向远处铁轨",
          narrative_purpose: "完成孤独修复任务并建立继续前行的转折",
        },
      };
      const providerContract = {
        service_id: "seedance_i2v",
        model: "doubao-seedance-2-0",
        model_variant: "non_fast",
        create_endpoint: "/volc/v1/contents/generations/tasks",
        query_endpoint: "/volc/v1/contents/generations/tasks/{id}",
        resolution: "720p",
        duration_sec: 6,
        candidate_count: 1,
        max_dispatches: 1,
        auto_retry: 0,
      };
      const budgetContract = {
        hard_ceiling_usd: "2.00",
        classification: "program_stop_ceiling_not_provider_enforced_estimate_or_actual",
      };
      const providerInputContract = {
        mode: "reference_conditioned",
        first_frame: null,
        last_frame: null,
        reference_images: source.references.map((item) => ({
          ...item,
          role: "reference_image",
          mime_type: "image/png",
          width: 1280,
          height: 720,
          byte_count: 1024,
        })),
        frame_role_cardinality: {
          first_frame: 0,
          last_frame: 0,
          reference_image: 3,
        },
        excluded_grounding_reference_count: 1,
      };
      const compiledManifest = {
        status: "locked",
        manifest_id: "video-manifest",
        manifest_hash: "a".repeat(64),
        source,
        provider_input_contract: providerInputContract,
        provider_contract: providerContract,
        budget_contract: budgetContract,
        budget: { dispatches_reserved: 0, remaining_dispatches: 1 },
        item: { item_id: "video-shot-01", state: "planned" },
        provider_dispatch_count: 0,
      };
      const approvedManifest = {
        ...compiledManifest,
        version: 3,
        manifest_id: "video-manifest-approved",
        manifest_hash: "d".repeat(64),
        source: {
          ...source,
          production_graph: { version: 15, graph_digest: "graph-v15" },
        },
        item: {
          ...compiledManifest.item,
          state: "approved",
          candidate: {
            job_id: "video-job-approved",
            candidate_id: "candidate-approved",
            preview_url: "/projects/browser-video-entry/video-generations/video-job-approved/candidates/candidate-approved/preview",
            sha256: "e".repeat(64),
            byte_count: 678,
            technical_qa: {
              status: "pass",
              container: "video/webm",
              width: 1280,
              height: 720,
              duration_sec: 6.04,
              codec: "vp9",
              decode_probe: "passed",
            },
            usage_evidence: {
              actual_charge_verification: "unverified",
            },
          },
          promotion: {
            graph_version: 16,
            graph_digest: "graph-v16",
          },
        },
        budget: { dispatches_reserved: 1, remaining_dispatches: 0 },
        provider_dispatch_count: 1,
      };
      const newRoundManifest = {
        ...compiledManifest,
        version: 3,
        manifest_id: "video-manifest-new-round",
        manifest_hash: "c".repeat(64),
        round_contract: {
          kind: "independent_after_provider_rejection",
          prior_round_preserved: true,
          prior_round_replay_allowed: false,
        },
      };
      const comparisonManifest = {
        ...compiledManifest,
        version: 4,
        manifest_id: "video-manifest-comparison",
        manifest_hash: "f".repeat(64),
        source: {
          ...source,
          production_graph: { version: 16, graph_digest: "graph-v16" },
        },
        round_contract: {
          kind: "independent_comparison",
          prior_round_preserved: true,
          prior_round_replay_allowed: false,
          prior_approved_result_immutable: true,
        },
      };
      const rejectedManifest = {
        ...compiledManifest,
        version: 2,
        item: {
          ...compiledManifest.item,
          state: "reconcile_required",
          provider_job_id: "old-rejected-job",
          network_disposition: "may_have_dispatched",
        },
        budget: { dispatches_reserved: 1, remaining_dispatches: 0 },
        provider_dispatch_count: 1,
      };
      const recompiledManifest = {
        ...compiledManifest,
        version: 2,
        manifest_id: "video-manifest-v15",
        manifest_hash: "b".repeat(64),
        source: {
          ...source,
          production_graph: { version: 15, graph_digest: "graph-v15" },
        },
      };
      const preview = (command) => ({
        preview_digest: `${command.type}-digest`,
        command,
        result: {
          manifest: command.type === "compile"
            ? { ...compiledManifest, status: "draft" }
            : command.type === "create_new_round"
              ? newRoundManifest
            : command.type === "create_comparison_round"
              ? comparisonManifest
            : command.type === "recompile_current"
              ? recompiledManifest
            : {
                ...compiledManifest,
                item: { ...compiledManifest.item, state: "reserved", reservation_token: "reservation" },
                budget: { dispatches_reserved: 1, remaining_dispatches: 0 },
              },
        },
      });
      let persistedVideoAdmission = null;
      const runtime = {
        projectId,
        workspaceOverview() {
          return Promise.resolve({
            projects: [{ project_id: projectId, project_type: "production" }],
          });
        },
        projectOverview() {
          return Promise.resolve({
            project: { project_id: projectId, name: "视频入口验收", status: "in_progress" },
          });
        },
        sequenceWorkspace() {
          return Promise.resolve(workspace);
        },
        loadAssetBible() {
          return Promise.resolve({
            authority_mode: "canonical_production_graph",
            asset_bible: bible,
          });
        },
        loadImageAdmission() {
          return Promise.resolve(imageAdmission);
        },
        loadVideoAdmission() {
          return Promise.resolve(persistedVideoAdmission);
        },
        health() {
          return Promise.resolve({
            provider_gates: { llm: true, image: true, video: true },
          });
        },
        previewVideoAdmissionCommand(request) {
          if (request.command.type === "compile") window.__calls.compilePreview += 1;
          if (request.command.type === "reserve_dispatch") window.__calls.reservePreview += 1;
          if (request.command.type === "recompile_current") {
            window.__rebuildEffects.recompilePreview += 1;
          }
          if (request.command.type === "create_new_round") {
            return Promise.resolve(preview(request.command));
          }
          if (request.command.type === "create_comparison_round") {
            return Promise.resolve(preview(request.command));
          }
          if (request.command.type === "compile" && window.__deferCompilePreview) {
            return new Promise((resolve) => {
              window.__releaseCompilePreview = () => {
                window.__deferCompilePreview = false;
                resolve(preview(request.command));
              };
            });
          }
          if (request.command.type === "reserve_dispatch" && window.__deferReservePreview) {
            return new Promise((resolve) => {
              window.__releaseReservePreview = () => {
                window.__deferReservePreview = false;
                resolve(preview(request.command));
              };
            });
          }
          if (request.command.type === "recompile_current" && window.__deferRecompilePreview) {
            return new Promise((resolve) => {
              window.__releaseRecompilePreview = () => {
                window.__deferRecompilePreview = false;
                resolve({
                  ...preview(request.command),
                  impact: {
                    current_graph_version: 15,
                    prepared_graph_version: 14,
                    source_manifest_archived: true,
                    keyframe_reuse: "verified_current",
                    affected_objects: ["镜头 01 视频来源未受此次更新影响"],
                  },
                });
              };
            });
          }
          return Promise.resolve(preview(request.command));
        },
        confirmVideoAdmissionCommand(request) {
          if (request.command.type === "compile") window.__calls.compileConfirm += 1;
          if (request.command.type === "reserve_dispatch") window.__sideEffects.reserveConfirm += 1;
          if (request.command.type === "recompile_current") {
            window.__rebuildEffects.recompileConfirm += 1;
            window.__rebuildEffects.oldManifestArchived += 1;
            persistedVideoAdmission = {
              status: "locked",
              manifest: recompiledManifest,
              readiness: {
                status: "ready",
                shot_id: "shot-01",
                shot_label: "镜头 01",
                first_frame_label: "已批准关键帧",
                reference_count: 3,
              },
              lineage: {
                status: "current",
                prepared_graph_version: 15,
                current_graph_version: 15,
              },
              capability: { configured: true },
              provider_dispatch_count: 0,
            };
            return Promise.resolve({
              result: { manifest: recompiledManifest },
              provider_dispatch_count: 0,
            });
          }
          if (request.command.type === "create_new_round") {
            persistedVideoAdmission = {
              status: "locked",
              manifest: newRoundManifest,
              readiness: {
                status: "ready",
                shot_id: "shot-01",
                shot_label: "镜头 01",
                first_frame_label: "已批准关键帧",
                reference_count: 3,
              },
              lineage: {
                status: "current",
                prepared_graph_version: 14,
                current_graph_version: 14,
              },
              capability: { configured: true },
              provider_dispatch_count: 0,
            };
            return Promise.resolve({
              result: { manifest: newRoundManifest },
              provider_dispatch_count: 0,
            });
          }
          if (request.command.type === "create_comparison_round") {
            persistedVideoAdmission = {
              status: "locked",
              manifest: comparisonManifest,
              readiness: {
                status: "ready",
                shot_id: "shot-01",
                shot_label: "镜头 01",
                first_frame_label: "已批准关键帧",
                reference_count: 3,
              },
              lineage: {
                status: "current",
                prepared_graph_version: 16,
                current_graph_version: 16,
              },
              capability: { configured: true },
              provider_dispatch_count: 0,
            };
            return Promise.resolve({
              result: { manifest: comparisonManifest },
              provider_dispatch_count: 0,
            });
          }
          if (request.command.type === "compile") {
            window.__sideEffects.persistedWrites += 1;
            persistedVideoAdmission = {
              status: "locked",
              manifest: compiledManifest,
              readiness: videoAdmission.readiness,
              capability: { configured: true },
              provider_dispatch_count: 0,
            };
          }
          return Promise.resolve({
            result: { manifest: compiledManifest },
            provider_dispatch_count: 0,
          });
        },
        preflightVideo() {
          window.__sideEffects.preflightVideo += 1;
          throw new Error("video preflight must not run in preview-only browser coverage");
        },
        generateVideo() {
          window.__sideEffects.generateVideo += 1;
          window.__calls.videoDispatch += 1;
          throw new Error("video generation must not run in preview-only browser coverage");
        },
        agentChatConversation(payload) {
          window.__calls.agentConversation += 1;
          if (
            payload.canvas_summary.video_readiness_status !== "ready"
            || payload.canvas_summary.video_selected_shot_ready !== 1
            || payload.canvas_summary.video_reference_count !== 3
          ) {
            throw new Error("agent conversation did not receive same-graph video readiness");
          }
          return Promise.resolve({
            mode: "llm",
            provider_calls_started: true,
            reply: "当前镜头已有已批准关键帧和 3 张参考图。请使用页面上的“准备镜头视频”入口审核真实确认卡；我没有创建清单或发送任务。",
            suggested_actions: ["准备镜头视频"],
            provider_lineage: { service_id: "server_codex" },
          });
        },
      };
      const studioState = {
        meta: { projectId, projectName: "视频入口验收" },
        nodes: {},
        edges: {},
        selection: { nodeIds: [], edgeId: null },
        production: {},
        assetBible: bible,
        ui: { projectIdentity: { status: "ready" } },
      };
      const imageAdmission = {
        status: "locked",
        manifest: {
          status: "locked",
          provider_dispatch_count: 1,
          budget: { dispatches_reserved: 0 },
          items: [{
            item_id: "approved-keyframe",
            item_type: "shot_keyframe",
            label: "镜头 01 关键帧",
            aspect_ratio: "16:9",
            size: "1280x720",
            occurrence_references: { shot_ids: ["shot-01"] },
            reference_media_ids: ["角色甲", "月台甲", "怀表甲"],
            state: "approved",
          }],
        },
      };
      const startPlanned = ["#planned", "#stale", "#rejected"].includes(window.location.hash);
      const startStale = window.location.hash === "#stale";
      const startRejected = window.location.hash === "#rejected";
      const videoAdmission = {
        status: startPlanned || approvedLedgerState ? "locked" : "empty",
        manifest: approvedLedgerState
          ? approvedManifest
          : startRejected
            ? rejectedManifest
            : startPlanned
              ? compiledManifest
              : null,
        readiness: {
          status: approvedLedgerState
            ? "comparison_ready"
            : startStale
              ? "stale"
              : startRejected
                ? "new_round_ready"
                : "ready",
          shot_id: "shot-01",
          shot_label: "镜头 01",
          first_frame_label: "已批准关键帧",
          reference_count: 3,
          generation_modes: [
            {
              mode: "reference_conditioned",
              label: "参考图约束视频",
              supported: true,
              reason: "使用批准资产约束身份与连续性，不锁定首帧。",
            },
            {
              mode: "first_frame",
              label: "首帧图生视频",
              supported: true,
              reason: "仅在明确要求从关键帧开始时使用。",
            },
            {
              mode: "text_to_video",
              label: "文生视频（仅文字叙事）",
              supported: false,
              reason: "当前服务未开放。",
            },
          ],
          suggested_generation_mode: "reference_conditioned",
          suggested_mode_reason: "使用批准资产约束身份与连续性，不锁定首帧。",
          temporal_staging_template: {
            subject_action_arc: "角色甲拿起怀表，打开后盖并完成一次校准",
            spatial_displacement: "角色从长椅一端起身移向月台工作灯",
            interaction_object: "双手持续操作怀表与修表工具",
            camera_movement: "镜头平稳侧移并在校准完成时停住",
            environment_dynamics: "远处蒸汽掠过月台，灯光随列车震动轻晃",
            pacing: "前段克制，中段加快，结尾停顿",
            start_state: "角色独坐月台检查无法走动的怀表",
            end_state: "怀表重新走动，角色抬头望向远处铁轨",
            narrative_purpose: "完成孤独修复任务并建立继续前行的转折",
          },
          next_action: "选择生成方式并补全镜头叙事。",
          ...(startRejected ? {
            new_round_allowed: true,
            next_action: "建立新的单次视频清单；旧失败记录保持不变。",
          } : {}),
          ...(approvedLedgerState ? {
            comparison_round_allowed: true,
            next_action: "准备一个不覆盖旧结果的叙事镜头对照。",
          } : {}),
        },
        lineage: approvedLedgerState
          ? {
              status: "current",
              prepared_graph_version: 15,
              current_graph_version: 16,
              keyframe_reuse: "verified_current",
              affected_objects: [],
              rebuild_allowed: false,
              approved_result_current: true,
            }
          : startStale
          ? {
              status: "stale",
              prepared_graph_version: 14,
              current_graph_version: 15,
              keyframe_reuse: "verified_current",
              affected_objects: ["镜头 01 视频来源未受此次更新影响"],
              rebuild_allowed: true,
            }
          : {
              status: startPlanned ? "current" : "empty",
              prepared_graph_version: startPlanned ? 14 : 0,
              current_graph_version: 14,
              rebuild_allowed: false,
            },
        capability: { configured: true },
        provider_dispatch_count: 0,
      };
      persistedVideoAdmission = videoAdmission;
      window.__videoCanvasShell = document.createElement("div");
      window.__videoCanvasShell.id = "studio-editor-shell";
      const studioStore = {
        get: () => studioState,
        set: (mutate) => mutate(studioState),
        setRuntimePersistenceMode: () => {},
      };
      const shell = createProductShell({
        getStudioState: () => studioState,
        getRuntime: () => runtime,
        getStore: () => studioStore,
        getCanvasShell: () => window.__videoCanvasShell,
        formatError: (error) => String(error?.message || error),
      });
      const authUser = { user_id: "browser-owner", display_name: "Owner" };
      await shell.refresh(runtime, authUser);
      shell.setSection("storyboard");
      window.__refreshVideoEntry = async () => {
        await shell.refresh(runtime, authUser);
        shell.setSection("storyboard");
      };
      window.__setVideoSection = (section) => shell.setSection(section);
      window.__videoStudioState = studioState;
      window.__persistedVideoState = () => ({
        status: persistedVideoAdmission?.manifest?.status || persistedVideoAdmission?.status || "",
        itemState: persistedVideoAdmission?.manifest?.item?.state || "",
        reserved: persistedVideoAdmission?.manifest?.budget?.dispatches_reserved ?? -1,
        remaining: persistedVideoAdmission?.manifest?.budget?.remaining_dispatches ?? -1,
        dispatches: persistedVideoAdmission?.manifest?.provider_dispatch_count ?? -1,
      });
      window.__videoEntryReady = true;
    </script>
  </body>
</html>
"""
