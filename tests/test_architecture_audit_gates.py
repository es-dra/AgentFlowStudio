from __future__ import annotations

import ast
from pathlib import Path


SOURCE_ROOTS = ("agentflow", "agentflow_studio", "apps")

KNOWN_AGENTFLOW_STUDIO_IMPORT_DEBT: set[tuple[str, str]] = set()

KNOWN_HIDDEN_COMMAND_DEBT = {
    "production-memory-loop-asset-profile-context-projection",
    "production-memory-loop-asset-profile-readiness",
    "production-memory-loop-capture-operator-feedback",
    "production-memory-loop-check-operator-manifest",
    "production-memory-loop-check-operator-run-package",
    "production-memory-loop-company-kb-candidates",
    "production-memory-loop-draft-acceptance-feedback-candidate",
    "production-memory-loop-draft-asset-profile-update-candidate",
    "production-memory-loop-draft-feedback",
    "production-memory-loop-draft-next-pass-result-no-provider",
    "production-memory-loop-draft-operator-feedback-candidate",
    "production-memory-loop-next-context-handoff",
    "production-memory-loop-next-operator-start-packet",
    "production-memory-loop-next-task-packet",
    "production-memory-loop-operator-handoff-packet",
    "production-memory-loop-provider-validation-gate",
    "production-memory-loop-record-acceptance-feedback",
    "production-memory-loop-record-action-result-acceptance-feedback",
    "production-memory-loop-record-asset-feedback",
    "production-memory-loop-record-next-operator-action-result",
    "production-memory-loop-record-next-operator-start",
    "production-memory-loop-review-acceptance-feedback-candidate",
    "production-memory-loop-review-asset-consistency",
    "production-memory-loop-review-asset-profile-update-candidate",
    "production-memory-loop-review-next-pass",
    "production-memory-loop-review-next-pass-promotion",
    "production-memory-loop-review-operator-feedback-candidate",
    "production-memory-loop-review-promotion",
    "production-memory-loop-run-acceptance-feedback-candidate-reviewed-no-provider",
    "production-memory-loop-run-asset-test-package",
    "production-memory-loop-run-next-pass-reviewed-feedback-no-provider",
    "production-memory-loop-run-no-provider",
    "production-memory-loop-run-operator-feedback-candidate-reviewed-no-provider",
    "production-memory-loop-run-operator-no-provider",
    "production-memory-loop-run-real-asset-test-harness",
    "production-memory-loop-run-reviewed-feedback-no-provider",
    "production-memory-loop-session-report",
    "production-memory-loop-two-round-context-runtime-validation",
    "production-memory-loop-validate",
}

def test_runtime_service_does_not_depend_on_cli_or_legacy_web_bridge() -> None:
    forbidden = _import_pairs(Path("apps/api"), ("apps.cli", "apps.web_bridge"))

    assert forbidden == set()


def test_legacy_web_bridge_package_is_retired() -> None:
    assert not Path("apps/web_bridge").exists()


def test_apps_use_platform_json_helper_not_studio_utils() -> None:
    forbidden = _import_pairs(Path("apps"), ("agentflow_studio.utils",))

    assert forbidden == set()


def test_agentflow_core_does_not_depend_on_studio_layer() -> None:
    actual = _import_pairs(Path("agentflow"), ("agentflow_studio.",))

    assert actual <= KNOWN_AGENTFLOW_STUDIO_IMPORT_DEBT


def test_package_level_cycles_are_not_allowed() -> None:
    cycles = {frozenset(cycle) for cycle in _package_cycles(_package_edges())}

    assert cycles == set()


def test_hidden_cli_surface_debt_is_frozen() -> None:
    actual = _hidden_cli_commands()

    assert actual <= KNOWN_HIDDEN_COMMAND_DEBT


def test_no_new_numbered_memory_advantage_demo_modules() -> None:
    actual = set(Path("agentflow_studio").glob("memory_advantage_demo_*.py"))

    assert actual == set()


def _module_name(path: Path) -> str:
    return ".".join(path.with_suffix("").parts)


def _python_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)


def _import_pairs(root: Path, prefixes: tuple[str, ...]) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for path in _python_files(root):
        module = _module_name(path)
        for imported in _imports(path):
            if imported.startswith(prefixes):
                pairs.add((module, imported))
    return pairs


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def _package_edges() -> dict[str, set[str]]:
    edges: dict[str, set[str]] = {}
    for root in SOURCE_ROOTS:
        for path in _python_files(Path(root)):
            source = _package_name(_module_name(path))
            for imported in _imports(path):
                if not imported.startswith(SOURCE_ROOTS):
                    continue
                target = _package_name(imported)
                if source != target:
                    edges.setdefault(source, set()).add(target)
    return edges


def _package_name(module: str) -> str:
    parts = module.split(".")
    return ".".join(parts[:2]) if len(parts) >= 2 else module


def _package_cycles(edges: dict[str, set[str]]) -> list[set[str]]:
    nodes = set(edges) | {target for targets in edges.values() for target in targets}
    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    cycles: list[set[str]] = []

    def visit(node: str) -> None:
        nonlocal index
        indices[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for target in edges.get(node, set()):
            if target not in indices:
                visit(target)
                lowlinks[node] = min(lowlinks[node], lowlinks[target])
            elif target in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[target])
        if lowlinks[node] != indices[node]:
            return
        component: set[str] = set()
        while True:
            item = stack.pop()
            on_stack.remove(item)
            component.add(item)
            if item == node:
                break
        if len(component) > 1:
            cycles.append(component)

    for node in sorted(nodes):
        if node not in indices:
            visit(node)
    return cycles


def _hidden_cli_commands() -> set[str]:
    names: set[str] = set()
    for path in (Path("apps/cli/production_memory_command_registry.py"),):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if _is_hidden_helper_call(node):
                names.add(_constant_arg(node, 1))
                continue
            command_name = _hidden_app_command_name(node)
            if command_name:
                names.add(command_name)
    return names


def _is_hidden_helper_call(node: ast.Call) -> bool:
    return isinstance(node.func, ast.Name) and node.func.id == "_hidden" and len(node.args) >= 2


def _constant_arg(node: ast.Call, index: int) -> str:
    value = node.args[index]
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        return value.value
    raise AssertionError("hidden CLI command names must be string literals")


def _hidden_app_command_name(node: ast.Call) -> str | None:
    if not isinstance(node.func, ast.Attribute) or node.func.attr != "command":
        return None
    hidden = False
    name: str | None = None
    for keyword in node.keywords:
        if keyword.arg == "hidden" and isinstance(keyword.value, ast.Constant):
            hidden = keyword.value.value is True
        if keyword.arg == "name" and isinstance(keyword.value, ast.Constant):
            name = keyword.value.value
    return name if hidden and isinstance(name, str) else None
