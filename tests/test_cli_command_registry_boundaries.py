from __future__ import annotations

from pathlib import Path


PRODUCT_REGISTRY = Path("apps/cli/command_registry.py")
SUPPORT_REGISTRY = Path("apps/cli/support_command_registry.py")


def test_product_command_registry_has_no_direct_provider_or_demo_registrations() -> None:
    source = PRODUCT_REGISTRY.read_text(encoding="utf-8")

    assert "kling_video_command" not in source
    assert "minimax_image_command" not in source
    assert "memory_demo_commands" not in source
    assert "kling-i2v-smoke" not in source
    assert "minimax-image-smoke" not in source
    assert "memory-advantage-demo-012" not in source
    assert "memory-advantage-demo-015" not in source
    assert "memory-video-pipeline-package" in source
    assert "production-memory-loop-next-operator-start-packet" in source
    assert "production-memory-loop-record-next-operator-start" in source
    assert "production-memory-loop-record-next-operator-action-result" in source


def test_support_command_registry_keeps_hidden_provider_and_demo_surface() -> None:
    source = SUPPORT_REGISTRY.read_text(encoding="utf-8")

    assert "hidden=True" in source
    assert "kling-i2v-smoke" in source
    assert "minimax-image-smoke" in source
    assert "memory-advantage-demo-012" in source
    assert "memory-advantage-demo-015" in source
