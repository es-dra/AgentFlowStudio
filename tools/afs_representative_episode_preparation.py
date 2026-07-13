from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentflow_studio.production.representative_episode import (
    RepresentativeEpisodeError,
    preparation_evidence,
    validate_representative_episode,
    write_preparation_evidence,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a provider-free representative AFS episode preparation package."
    )
    parser.add_argument("package", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        validated = validate_representative_episode(args.package)
    except RepresentativeEpisodeError as exc:
        print(f"Representative episode preparation failed closed: {exc}", file=sys.stderr)
        return 1
    if args.output:
        write_preparation_evidence(validated, args.output)
    print(json.dumps(preparation_evidence(validated), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
