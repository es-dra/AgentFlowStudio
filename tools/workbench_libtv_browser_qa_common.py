from __future__ import annotations

import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Sequence
from typing import Any


def workbench_url(raw_url: str) -> str:
    parsed = urllib.parse.urlparse(raw_url)
    if parsed.path.rstrip("/").endswith("/workbench"):
        return raw_url if raw_url.endswith("/") else f"{raw_url}/"
    return urllib.parse.urljoin(raw_url.rstrip("/") + "/", "workbench/")


def assert_url_available(url: str) -> None:
    try:
        with urllib.request.urlopen(url, timeout=10) as response:  # noqa: S310 - local QA URL.
            if response.status >= 400:
                raise SystemExit(f"Workbench URL returned HTTP {response.status}: {url}")
    except (OSError, urllib.error.URLError) as exc:
        raise SystemExit(f"Workbench URL is not available: {url} ({exc})") from exc


def is_provider_request(url: str, patterns: Sequence[str]) -> bool:
    lowered = url.lower()
    return any(pattern.lower() in lowered for pattern in patterns)


def capture_node_control_feedback(page: Any, *, skipped: bool = False, reason: str | None = None) -> dict[str, Any]:
    if skipped:
        result: dict[str, Any] = {"skipped": True}
        if reason:
            result["reason"] = reason
        return result
    return page.evaluate("""() => {
      const controls = [...document.querySelectorAll('[data-node-control]')];
      const target = controls.find((node) => node.getAttribute('aria-pressed') === 'false');
      if (!target) return { skipped: false, control_count: controls.length, clicked: false, after_pressed: false };
      const summaryBefore = document.querySelector('[data-node-control-summary]')?.innerText || '';
      const group = target.dataset.nodeControl;
      const value = target.dataset.nodeControlValue;
      target.click();
      const selected = [...document.querySelectorAll('[data-node-control]')]
        .find((node) => node.dataset.nodeControl === group && node.dataset.nodeControlValue === value);
      const summary = document.querySelector('[data-node-control-summary]');
      const summaryAfter = summary?.innerText || '';
      return {
        skipped: false,
        control_count: controls.length,
        clicked: true,
        group,
        value,
        after_pressed: selected?.getAttribute('aria-pressed') === 'true',
        summary_count: document.querySelectorAll('[data-node-control-summary]').length,
        summary_after: summaryAfter,
        summary_changed: Boolean(summaryAfter) && summaryAfter !== summaryBefore,
        summary_mentions_value: Boolean(value) && summaryAfter.includes(value),
      };
    }""")


def capture_video_motion_feedback(page: Any, *, skipped: bool = False) -> dict[str, Any]:
    if skipped:
        return {"skipped": True}
    return page.evaluate("""() => {
      const panel = document.querySelector('.video-motion-panel');
      const target = [...document.querySelectorAll('[data-node-control="video-motion"]')]
        .find((node) => node.dataset.nodeControlValue !== '推进');
      if (!panel || !target) return { skipped: false, panel_visible: Boolean(panel), clicked: false };
      const summaryBefore = document.querySelector('[data-node-control-summary]')?.innerText || '';
      const value = target.dataset.nodeControlValue;
      target.click();
      const nextPanel = document.querySelector('.video-motion-panel');
      const nextRect = nextPanel?.getBoundingClientRect();
      const nextStyle = nextPanel ? getComputedStyle(nextPanel) : null;
      const selected = [...document.querySelectorAll('[data-node-control="video-motion"]')]
        .find((node) => node.dataset.nodeControlValue === value);
      const summaryAfter = document.querySelector('[data-node-control-summary]')?.innerText || '';
      return {
        skipped: false,
        panel_visible: Boolean(nextPanel && nextRect.width > 0 && nextRect.height > 0 && nextStyle.display !== 'none' && nextStyle.visibility !== 'hidden'),
        clicked: true,
        value,
        active: selected?.getAttribute('aria-pressed') === 'true',
        summary_after: summaryAfter,
        summary_changed: Boolean(summaryAfter) && summaryAfter !== summaryBefore,
        summary_mentions_value: Boolean(value) && summaryAfter.includes(value),
      };
    }""")


def drag_node_to_safe_bottom(page: Any, node_id: str, stage_box: dict[str, float]) -> dict[str, Any]:
    handle = page.locator(f"[data-node-id='{node_id}'] [data-node-drag-handle]").first
    handle_box = handle.bounding_box()
    if not handle_box:
        return {"selected_node_above_dock": False, "reason": "missing handle"}
    start_x = handle_box["x"] + handle_box["width"] / 2
    start_y = handle_box["y"] + handle_box["height"] / 2
    page.mouse.move(start_x, start_y)
    page.mouse.down()
    page.mouse.move(start_x + 20, stage_box["y"] + stage_box["height"] - 38, steps=10)
    page.mouse.up()
    page.wait_for_timeout(180)
    return page.evaluate("""(id) => {
      const node = document.querySelector(`[data-node-id="${CSS.escape(id)}"]`);
      const dock = document.querySelector('.libtv-bottom-bar');
      const nodeZ = Number(getComputedStyle(node).zIndex || 0);
      const dockZ = Number(getComputedStyle(dock).zIndex || 0);
      const nodeRect = node?.getBoundingClientRect();
      const dockRect = dock?.getBoundingClientRect();
      const intersectsDock = Boolean(nodeRect && dockRect
        && nodeRect.left < dockRect.right && nodeRect.right > dockRect.left
        && nodeRect.top < dockRect.bottom && nodeRect.bottom > dockRect.top);
      return {
        node_z_index: nodeZ, dock_z_index: dockZ,
        selected_node_above_dock: nodeZ > dockZ,
        selected_node_clear_of_dock: !intersectsDock,
        node_rect: nodeRect?.toJSON?.() || null,
        dock_rect: dockRect?.toJSON?.() || null,
      };
    }""", node_id)


def write_stdout(text: str) -> None:
    sys.stdout.buffer.write(text.encode("utf-8"))
    sys.stdout.buffer.write(b"\n")
