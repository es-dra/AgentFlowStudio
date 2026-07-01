# AFS Studio Frontend Reference Plan - 2026-06-17

## Scope

This note records a read-only frontend reference pass for the live AFS Studio
site and LibTV. It is a planning artifact only. It does not claim human
acceptance, provider smoke, business validation, or durable memory promotion.

## Inputs

- AFS live site: https://afstudio.art/studio/
- LibTV site: https://www.liblib.tv/
- LibTV CLI page: https://www.liblib.tv/cli
- Current local branch state at capture time: `master...origin/master`, clean.

Screenshots were captured outside the repository as local evidence and are not
committed.

## Observations

### AFS Live Studio

- The live Studio is reachable and opens directly into the production canvas.
- The current product surface already behaves like a professional workbench:
  left asset/node drawer, central infinite canvas, bottom action dock, node
  result cards, persisted project state, and provider job state projection.
- The first impression is functional but opaque. A new user sees nodes and a
  generated image, but the intended workflow is not obvious without prior
  context.
- The mobile layout currently shows the left drawer and canvas, but the canvas
  content is mostly off-screen. It is usable as a diagnostic surface, not yet a
  serious mobile workflow.
- Visible text/title extraction showed mojibake in machine-readable text. Some
  rendered Chinese looks correct in screenshots, but DOM/title/accessibility
  text needs an encoding audit.
- A desktop console pass observed one `404 Not Found` resource on AFS. The
  missing resource should be identified before visual polish work.

### LibTV Site

- LibTV's public homepage is not primarily an editor. It is a creation portal
  plus content gallery: brand header, campaign banner, large visual carousel,
  primary CTAs, categories, search, and TV Show cards.
- LibTV makes "start creating" and "quick experience" highly visible before
  asking the user to understand workflow details.
- The mobile homepage compresses the product into a feed-like creation portal:
  promo banner, login, carousel, two main CTAs, category chips, search, then
  content cards.
- LibTV CLI page is especially relevant to AFS because it presents Agent entry
  clearly: one central promise, install mode tabs, copyable prompt/command, and
  supported Agent list.
- LibTV also has its own console warnings, so it should be used as a product
  reference, not as a technical quality baseline to copy blindly.

## Frontend Direction

AFS should not copy LibTV's public gallery-first layout inside `/studio/`.
AFS's differentiator is a Runtime-backed agent-native production workbench.
However, AFS should borrow LibTV's clarity in three places:

1. A clear entry route before deep canvas work.
2. Highly visible primary creation actions.
3. Agent/provider capability presentation that users can understand without
   reading backend concepts.

## Proposed Work Waves

### Wave UI-0: Live Site Hygiene

- Fix HTML/title/DOM mojibake and verify UTF-8 delivery from Runtime static
  serving.
- Identify and fix the live `404` resource.
- Add a small non-provider smoke route for `/studio/` that checks title,
  language, core containers, console errors, and mobile overflow.
- Keep provider gates untouched.

### Wave UI-1: Production Workbench Clarity

- Add a Studio landing/empty-state layer inside `/studio/` for first-time or
  empty projects: "start from script", "create character", "create scene",
  "generate keyframe", "continue video".
- Add a persistent Job Center for LLM/image/keyframe/video job states.
- Convert the current left drawer into a clearer asset/workflow navigator:
  canvas elements, fixed assets, drafts, jobs, history.
- Add a right inspector for selected node/asset/job with safe manifest,
  context refs, prompt, result, feedback, and retry boundary.
- Keep the canvas as the main workspace after the user starts working.

### Wave UI-2: LibTV-Informed Creation Flow

- Add storyboard/shot-strip projection from canvas nodes.
- Add guided mode for beginners while preserving free canvas mode for advanced
  users.
- Promote asset-card drafting UX: character, scene, and video asset draft
  states are visible but cannot enter context until confirmed.
- Present provider/Agent capabilities like LibTV CLI does: clear capability
  names, gate state, supported workflows, and explicit human authorization
  boundary.

### Wave UI-3: Quality And Revision Loop

- Add compare view for before/after and A/B/C results.
- Add image/video quality feedback panels with bounded scoring fields.
- Add drift and continuity cards for video revision attempts.
- Keep feedback as raw evidence until human-reviewed promotion.

## Verification Route

- `node --check` for changed Studio JS files.
- `python -m pytest tests/test_web_studio_static.py -q`
- Focused Runtime tests for any new safe state contract.
- Browser QA against `http://127.0.0.1:8790/studio/` and
  `https://afstudio.art/studio/` where appropriate.
- `python tools/maintenance_audit.py`
- `git diff --check`

## Non-Claims

- This pass is frontend reference research, not implementation.
- It is not provider smoke.
- It is not human acceptance.
- It is not business validation.
- It does not promote any COS/GFR rule to durable active memory.
