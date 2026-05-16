from __future__ import annotations

from collections.abc import Callable
from typing import TypeAlias

from narratocut.workflow_engine.context import WorkflowContext
from narratocut.workflow_engine.definitions import WorkflowStepDefinition


NodeHandler: TypeAlias = Callable[[WorkflowStepDefinition, WorkflowContext], list[str]]


class NodeRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, NodeHandler] = {}

    def register(self, node_type: str, handler: NodeHandler) -> None:
        self._handlers[node_type] = handler

    def get(self, node_type: str) -> NodeHandler:
        try:
            return self._handlers[node_type]
        except KeyError as exc:
            raise KeyError(f"Unknown workflow node type: {node_type}") from exc
