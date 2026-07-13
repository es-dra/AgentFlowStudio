from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agentflow_studio.production.vertical_slice import DeterministicProductionSlice


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the provider-free deterministic AFS production vertical slice.")
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--creator-decision", type=Path, required=True)
    parser.add_argument("--quality-review", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    paths = DeterministicProductionSlice.from_files(
        args.project,
        args.creator_decision,
        args.quality_review,
        args.output,
    )
    for name, path in paths.items():
        print(f"{name}={path}")
    print("claim_level=deterministic_local_structure_and_flow")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
