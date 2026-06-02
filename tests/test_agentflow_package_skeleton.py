from __future__ import annotations

import importlib
import tomllib
from pathlib import Path


def test_agentflow_package_skeleton_imports_without_runtime_side_effects() -> None:
    agentflow = importlib.import_module("agentflow")

    assert agentflow.PACKAGE_NAME == "agentflow"
    assert agentflow.PACKAGE_SCOPE == "platform_contract_layer"
    assert agentflow.RUNTIME_STATUS == "not_implemented"
    assert agentflow.__all__ == ("PACKAGE_NAME", "PACKAGE_SCOPE", "RUNTIME_STATUS")


def test_agentflow_namespace_packages_are_reserved_but_empty() -> None:
    for module_name in [
        "agentflow.contracts",
        "agentflow.router",
        "agentflow.skills",
    ]:
        module = importlib.import_module(module_name)

        assert module.PACKAGE_SCOPE == "reserved_namespace"
        assert module.RUNTIME_STATUS == "not_implemented"


def test_agentflow_harness_namespace_hosts_platform_validators_without_runtime() -> None:
    harness = importlib.import_module("agentflow.harness")

    assert harness.PACKAGE_SCOPE == "platform_harness_layer"
    assert harness.RUNTIME_STATUS == "not_implemented"


def test_agentflow_memory_namespace_hosts_contract_helpers_without_runtime() -> None:
    memory = importlib.import_module("agentflow.memory")

    assert memory.PACKAGE_SCOPE == "platform_memory_helper_layer"
    assert memory.RUNTIME_STATUS == "not_implemented"


def test_agentflow_packages_are_included_in_setuptools_discovery() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    project = pyproject["project"]
    scripts = project["scripts"]
    package_find = pyproject["tool"]["setuptools"]["packages"]["find"]

    assert project["name"] == "agentflow-studio"
    assert scripts == {"afs": "apps.cli.main:app"}
    assert package_find["where"] == ["."]
    assert "agentflow*" in package_find["include"]
    assert "agentflow_studio*" in package_find["include"]
    assert not any("narrato" in package for package in package_find["include"])


def test_existing_agentflow_validator_imports_stay_in_agentflow_studio_harness() -> None:
    router = importlib.import_module("agentflow_studio.harness.agentflow_router")
    skill = importlib.import_module("agentflow_studio.harness.agentflow_skill")

    assert hasattr(router, "validate_router_decision_dry_run")
    assert hasattr(skill, "validate_skill_invocation_result_replay")
