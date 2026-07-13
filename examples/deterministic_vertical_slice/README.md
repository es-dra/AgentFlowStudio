# Deterministic Production Vertical Slice

This fixture exercises a provider-free AFS production path:

```text
project/IP -> script + character assets -> storyboard + shots
  -> deterministic text candidates -> creator selection/revision
  -> explicit quality review -> delivery + lineage evidence
```

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe tools\afs_deterministic_vertical_slice.py `
  --project examples\deterministic_vertical_slice\project.example.json `
  --creator-decision examples\deterministic_vertical_slice\creator_decision.example.json `
  --quality-review examples\deterministic_vertical_slice\quality_review.example.json `
  --output <temporary-output-directory>
```

`expected_export/production_delivery.json` is a concrete deterministic
deliverable. `expected_export/evidence.json` records creator involvement,
quality-gate state, recovery metadata, lineage, a delivery checksum, and
protected non-claims.

The fixture review permits deterministic export testing only. It does not
prove provider smoke, generated-media quality, human creative acceptance,
business validation, release readiness, or rule promotion.
