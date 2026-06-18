from pathlib import Path


STUDIO_ROOT = Path("apps/studio")


def _source() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in STUDIO_ROOT.rglob("*.js"))


def _styles() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in STUDIO_ROOT.rglob("*.css"))
