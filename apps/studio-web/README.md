# AFS Studio Web vertical slice

This package is the isolated React + TypeScript product-shell slice for the
v0.2 Chinese interface direction.

## Runtime

```powershell
npm install
npm run dev
npm run typecheck
npm run test
npm run build
```

The default URL reads the Runtime Service through the same origin:

```text
/?project_id=studio-1785154250742-86s0uf&surface=overview
```

For local visual QA without a running Runtime Service, use the explicitly
non-authoritative canonical fixture:

```text
/?project_id=studio-1785154250742-86s0uf&surface=overview&source=fixture
```

## Typed adapter assumptions

- Runtime Studio v0.1 accepts only `canvas`, `script`, `storyboard`,
  `asset-bible`, `review`, and `delivery`. The UI-only `overview` route reads
  the `canvas` envelope for shared project/version/recovery facts.
- The current envelope has no `event_cursor`, `surface_summary`,
  `focused_entity`, controlled media URL, delivery summary, or
  command-preview/confirm route. The live UI therefore renders only fields
  present in the envelope and shows an explicit unavailable/empty state for
  missing capabilities.
- The canonical v0.2 fixture is used only when `source=fixture` is present. It
  is visual/test data, never a fallback after a live request fails.
- `allowed_actions` currently exposes inspection actions only. Candidate
  adoption, local rework confirmation, and delivery creation remain disabled;
  the rework surface is preview-only.
- Authorization reuses the existing local session key
  `afs_auth_session_token`. Runtime overrides are accepted only for the current
  origin or loopback hosts so a bearer token cannot be redirected to an
  arbitrary host.

These assumptions are intentionally contained in `src/api/studioClient.ts` and
`src/api/studioAdapter.ts`; surfaces do not assemble Runtime internals directly.
