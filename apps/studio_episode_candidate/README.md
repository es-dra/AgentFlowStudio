# Episode workspace productization candidate

This isolated candidate implements the selected information architecture:

```text
Project / Episode shell
  -> Storyboard-centered production workspace
  -> Contextual decision inspector
```

It is not mounted into the production Studio. It contains no representative
episode fixture, fake project, local persistence, provider integration, or
synthetic progress. This Wave is GET-only: the page reads a server projection anchored to exact facts
from `afs_episode_production_aggregate.v0.1` through:

```text
GET /projects/{project_id}/episode-production-aggregate
```

The GET request uses `credentials: "include"`. There is no frontend mutation
route in this candidate. Every action that would change project facts is
disabled with a visible read-only explanation. Browser QA may intercept the GET
route with the authoritative fixture, but must display the `test` evidence
marker.

Mutation activation is an explicit later dependency: first integrate and freeze
the aggregate API plus Review/Delivery service, then define a bounded command
API lane, rebase this candidate, inspect the real route table/OpenAPI, and only
then enable mutations. This Wave does not prove a production vertical slice,
runtime mutation, save/recovery write, or end-to-end delivery.

At this rebased branch base, the checked-in route table and OpenAPI expose the
authenticated aggregate path with GET and PUT. This candidate intentionally
uses GET only. PUT is an aggregate replacement surface, not a creator-action
command contract, so it is not used to activate any mutation in this Wave. A
post-integration evaluator must still verify the exact-ref-anchored workspace
projection against the live route before production mounting.

## Visual contract

- Deep rain-blue project shell, true white/neutral storyboard paper, copper
  decision accent.
- Desktop: compact scene/problem rail, dominant storyboard, contextual
  inspector.
- Mobile: one-column shot/task cards followed by contextual detail; no wide
  table or compressed desktop console.
- Guided behavior is limited to the one next action, recovery cue, and natural
  errors. Timeline, infinite canvas, and global agent chat are absent.

The Image Gen concept used as the visual specification remains outside the repo
at:

```text
C:\Users\chenzy\.codex\generated_images\019f6302-d4f4-7493-b58a-a3f6af85286d\exec-7fa7cb22-ba4d-40db-95b6-e6df461f1554.png
```

This candidate is structure/evaluator evidence only. It is not production
integration, provider or media quality evidence, human acceptance, business
validation, or release readiness.
