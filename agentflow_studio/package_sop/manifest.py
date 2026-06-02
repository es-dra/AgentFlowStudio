from __future__ import annotations

from pathlib import Path

from agentflow_studio.schemas import FinishedPackageAsset, FinishedPackageManifest


FINISHED_PACKAGE_MANIFEST = "finished_package_manifest.json"


def build_finished_package_manifest(
    *,
    package_id: str,
    final_video_path: str | Path,
    optional_assets: dict[str, str | Path | None] | None = None,
    evidence: dict[str, str | Path | None] | None = None,
) -> FinishedPackageManifest:
    assets: list[FinishedPackageAsset] = []
    errors: list[str] = []

    primary = _asset("final_video", final_video_path, required=True)
    assets.append(primary)
    if not primary.exists:
        errors.append("final_video_missing")

    for role, path in (optional_assets or {}).items():
        if path:
            assets.append(_asset(role, path, required=False))

    return FinishedPackageManifest(
        status="failed" if errors else "succeeded",
        package_id=package_id,
        primary_video=primary,
        assets=assets,
        evidence={key: _display_ref(path) for key, path in (evidence or {}).items() if path},
        errors=errors,
        warnings=[],
        manifest_path=FINISHED_PACKAGE_MANIFEST,
    )


def _asset(role: str, path: str | Path, *, required: bool) -> FinishedPackageAsset:
    ref = _display_ref(path)
    file_path = Path(path)
    exists = file_path.is_file()
    return FinishedPackageAsset(
        role=role,
        path=ref,
        required=required,
        exists=exists,
        size_bytes=file_path.stat().st_size if exists else None,
    )


def _display_ref(value: str | Path) -> str:
    return str(value).replace("\\", "/")
