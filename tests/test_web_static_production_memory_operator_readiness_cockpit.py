from __future__ import annotations

import json
import subprocess
from pathlib import Path

from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_operator_loop import (
    build_production_memory_operator_loop_run,
    write_production_memory_operator_loop_run,
)


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def test_web_static_operator_loop_builds_start_readiness_cockpit(tmp_path: Path) -> None:
    loop = load_production_memory_loop(EXAMPLE_PATH)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-03T10:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )
    write_production_memory_operator_loop_run(
        result,
        tmp_path,
        write_run_package=True,
        write_run_package_check=True,
        write_next_operator_start_packet=True,
    )
    manifest_ref = json.dumps(str(tmp_path / "production_memory_operator_loop_run.json"))

    script = f"""
import {{ parseFiles, normalizeWorkspace }} from "./apps/web/artifact-workspace.js";
import {{ buildMemoryWorkbenchView }} from "./apps/web/memory-workbench-controller.js";
import {{ renderStudioStatus }} from "./apps/web/memory-workbench-studio-render.js";
import {{ readFile }} from "node:fs/promises";

function element(tagName) {{
  return {{
    tagName,
    className: "",
    children: [],
    _text: "",
    set textContent(value) {{ this._text = String(value); }},
    get textContent() {{
      return [this._text, ...this.children.map((child) => child.textContent || "")].join("");
    }},
    append(...children) {{ this.children.push(...children); }},
    replaceChildren(...children) {{ this.children = children; }},
  }};
}}
globalThis.document = {{ createElement: element }};

const file = {{
  name: "production_memory_operator_loop_run.json",
  text: async () => await readFile({manifest_ref}, "utf8"),
}};
const workspace = normalizeWorkspace(await parseFiles([file]));
const view = buildMemoryWorkbenchView(workspace, "selected_files");
const elements = {{ memoryStudioStatus: element("div") }};
renderStudioStatus(elements, view, {{ statusLabels: {{}}, noDetails: "" }});

console.log(JSON.stringify({{
  state: view.state,
  projectFormat: view.project.format,
  assetCount: view.assets.length,
  boundaryCount: view.protocol_summary.boundaries.length,
  memoryCount: view.memory_loaded.length,
  studioStatus: elements.memoryStudioStatus.textContent,
}}));
"""
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        encoding="utf-8",
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["state"] == "operator loop ready"
    assert payload["projectFormat"] == "agentflow_production_memory_operator_loop_run"
    assert payload["assetCount"] >= 1
    assert payload["boundaryCount"] >= 1
    assert payload["memoryCount"] >= 1
    assert "Current view" in payload["studioStatus"]
    assert "operator loop ready" in payload["studioStatus"]
    assert "Assets" in payload["studioStatus"]
    assert "Do not claim" in payload["studioStatus"]
