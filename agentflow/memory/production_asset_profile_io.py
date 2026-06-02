from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow.memory.production_asset_profile_constants import PROVIDER_VALIDATION_BLOCKERS_KIND
from agentflow.memory.production_asset_profile_render import (
    package_markdown,
    readiness_markdown,
    rubric_markdown,
    tester_feedback_template,
)
from agentflow.memory.production_loop import SCHEMA_VERSION
from narratocut.utils import write_json


def write_asset_profile_test_package(bundle: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    written = [
        write_json(output_root / "asset_profiles.json", {"profiles": bundle["asset_profiles"]}),
        write_json(output_root / "asset_profile_readiness.json", bundle["readiness"]),
        write_json(output_root / "asset_test_package.json", bundle["test_package"]),
        write_json(output_root / "provider_validation_plan.json", bundle["provider_validation_plan"]),
        write_json(
            output_root / "provider_validation_blockers.json",
            {
                "kind": PROVIDER_VALIDATION_BLOCKERS_KIND,
                "artifact_type": PROVIDER_VALIDATION_BLOCKERS_KIND,
                "schema_version": SCHEMA_VERSION,
                "blockers": bundle["provider_validation_blockers"],
            },
        ),
    ]
    if bundle.get("provider_validation_result") is not None:
        written.append(write_json(output_root / "provider_validation_result.json", bundle["provider_validation_result"]))
    markdown_files = {
        "asset_profile_readiness.md": readiness_markdown(bundle["readiness"]),
        "asset_test_package.md": package_markdown(bundle["test_package"]),
        "asset_consistency_rubric.md": rubric_markdown(),
        "tester_feedback_template.md": tester_feedback_template(),
    }
    for name, body in markdown_files.items():
        path = output_root / name
        path.write_text(body, encoding="utf-8")
        written.append(path)
    return written


__all__ = ("write_asset_profile_test_package",)
