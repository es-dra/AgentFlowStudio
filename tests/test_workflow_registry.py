from __future__ import annotations

import pytest

from agentflow_studio.workflow_engine import NodeRegistry


def test_node_registry_registers_and_returns_handler() -> None:
    registry = NodeRegistry()

    def handler(step, context):
        return None

    registry.register("example", handler)

    assert registry.get("example") is handler


def test_node_registry_raises_for_unknown_node_type() -> None:
    registry = NodeRegistry()

    with pytest.raises(KeyError, match="Unknown workflow node type"):
        registry.get("missing")
