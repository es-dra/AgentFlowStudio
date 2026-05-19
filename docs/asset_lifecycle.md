# Asset Lifecycle

NarratoCut runs create many local files. This lifecycle vocabulary keeps raw
inputs, generated evidence, final package assets, and future published assets
separate for humans, agents, and Web UI code.

## States

- `raw`: user-provided source media, scripts, or local BGM.
- `derived`: extracted or transformed evidence, such as audio WAV files,
  transcripts, OCR timelines, candidate windows, and score reports.
- `generated`: media created by workflow execution, such as clips, subtitles,
  covers, and assembled videos.
- `packaged`: final package assets indexed by `finished_package_manifest.json`
  and summarized by `package_report.md`.
- `published`: assets that a future integration has uploaded or released.
- `archived`: assets retained for history but no longer current.

## Current Directory Mapping

```text
data/raw/                  raw
data/processed/runs/       derived, generated, packaged run outputs
data/processed/packages/   packaged future package directories
data/processed/cache/      derived reusable cache
data/reports/              acceptance and delivery reports
```

## Agent Notes

Agents should not infer that every file in a run is final. Prefer this order:

1. `run_manifest.json` for run artifact references.
2. `finished_package_manifest.json` for package assets.
3. `package_report.md` for human-readable summary.
4. `quality_report.json` and `review_report.json` for trust state.
5. `delivery_readiness.json` for release or handoff state.
