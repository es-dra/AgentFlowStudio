# AFS Script Review Flow Mainline Deploy

Date: 2026-06-22
Status: completed

## Scope

- Merged `codex/studio-script-review-flow-20260622` into `master`.
- Pushed feature branch and `master` to GitHub.
- Fast-forwarded server `/home/afs-ops/AgentFlowStudio` and
  `/opt/afs/AgentFlowStudio`.
- Restarted `afs-runtime` and `afs-codex-image-worker`.
- Verified local, GitHub, server repository state, and Runtime health.

## Mainline Commit

Feature commit:

```text
dddf984 feat(studio): gate storyboard review before assets
```

The commit adds the Runtime storyboard-breakdown route, editable text/script and
asset-card node bodies, manual storyboard-to-asset gating, and keyframe-layer
gating behind an existing asset layer.

## Verification Before Push

```text
pytest -> 592 passed / 520 deselected / 2 warnings
npm run check:studio-js -> 107 files passed
python -m apps.cli.main --help -> passed
python -m apps.cli.main version -> 0.1.0
python tools/maintenance_audit.py -> failed=0, warnings only
python tools/studio_full_coverage_browser_qa.py --timeout-ms 30000 -> passed
git diff --check -> passed
```

## Server Deployment

Server code directories were clean and fast-forwarded from `44e7edc` to
`dddf984`:

```text
/home/afs-ops/AgentFlowStudio
/opt/afs/AgentFlowStudio
```

Runtime services after restart:

```text
afs-runtime -> active
afs-codex-image-worker -> active
http://127.0.0.1:8790/health -> status=ready, studio_static.status=ready
```

## Boundaries

- No provider secret, provider config, signed URL, raw provider response, local
  media bytes, invite code, session token, or Company OS private source content
  was written.
- Provider gates were not changed by this deployment.
- This is code/runtime/browser/server verification, not human acceptance,
  business validation, provider smoke, video smoke, or durable memory
  promotion.

