# AgentFlow Studio Positioning And Knowledge Feedback Reset

Status: strategic positioning projection for the next AFS landing phase.

Date: 2026-06-02

This document is an execution-facing projection inside the AgentFlow Studio
repository. It does not replace the local Company knowledge base and does not
promote any rule, lesson, or candidate into durable company memory.

## Purpose

Recent production-memory pilot work proved that AgentFlow Studio can ingest,
organize, and display real production evidence. It also exposed a direction
risk: the pressure sample can start to look like the product itself.

AFS is the project to land. Project-specific production samples should remain
evidence sources. The local Company knowledge base remains the source of rules,
strategy, and memory-promotion decisions. AFS should execute those rules,
validate them in project work, and return candidate improvements for human
review.

## Current Positioning

The near-term product positioning is:

```text
AgentFlow Studio is a memory-driven AI content production workbench.
```

A more explicit internal version is:

```text
AgentFlow Studio helps AI content production teams turn production evidence,
human feedback, and project decisions into reusable memory for the next pass.
```

This is clearer for the current landing phase than leading with broader terms
such as `Memory OS` or `Evidence-backed Context Runtime`.

## Naming Layers

Use three language layers.

| Layer | Recommended name | Use |
|---|---|---|
| Product | Memory-driven AI content production workbench | User-facing and roadmap language |
| Current architecture | Production Memory Architecture | Engineering planning and architecture docs |
| Long-term vision | Memory OS | Internal strategic vision after the system matures |

`Evidence-backed Context Runtime` should not be the primary narrative. When the
idea is needed, describe it plainly:

```text
Assemble the right context for the next AI task from verified production
evidence, human feedback, and approved project memory.
```

If a shorter engineering label is needed, use `context assembly layer`.

## What AFS Should Prove First

The near-term proof is narrow and concrete:

```text
project input
-> artifact ledger
-> review / feedback
-> memory or asset candidate
-> explicit promotion decision
-> next context bundle
-> next production pass
```

The proof should show that the next pass is less manual, more traceable, and
more consistent because the project reused reviewed evidence instead of
starting from scratch.

## What AFS Should Not Claim Yet

Do not claim:

- durable Memory OS completion;
- automatic Company knowledge-base writes;
- general-purpose agent operating system readiness;
- autonomous creative approval;
- business validation;
- final content quality proof from tests alone;
- project-specific production engineering as product maturity.

The current system can claim structural traceability, local no-provider
protocol execution, static workbench review, and explicit human gates.

## Pressure-Sample Feedback

Real production samples produced useful feedback because they were messy in the
same way production work is messy:

- story, character, scene, and provider-route work can become fragmented;
- some outputs are useful candidates but are not approved memory;
- generated candidates, review notes, manifests, and prompts can spread across
many files;
- the missing human decision layer is often the real blocker, not another
generation command.

The product lesson is:

```text
AFS should reduce production-memory fragmentation.
```

AFS should make current state, usable evidence, blocked candidates, approved
memory, and next action visible without forcing the operator to inspect many
local files.

## Knowledge-Base Feedback Loop

The intended loop is:

```text
Company knowledge base
-> AFS project rules and architecture
-> real AFS execution
-> evidence and failures
-> candidate knowledge-base improvements
-> human review
-> Company memory / rules / project notes
```

AFS must not write into the Company knowledge base automatically. It should
produce candidate feedback that the user can review and promote manually.

Candidate feedback should be grouped as:

- product positioning feedback;
- architecture naming feedback;
- workflow and agent-collaboration feedback;
- quality-gate feedback;
- memory-promotion and anti-pattern feedback;
- project-specific technical-note updates.

## Landing Priorities

Priority 1: Product path consolidation

- Define the one real operator loop AFS should support first.
- Make the workbench show that loop clearly.
- Keep raw artifact inspection secondary.
- Make state transitions visible: no plan, planned, review ready, feedback
  captured, candidate drafted, promotion ready, blocked.

Priority 2: Production-memory contracts

- Keep artifact ledger, feedback, candidate memory or candidate asset update,
  promotion decision, profile version, and next context bundle as the core
  contract chain.
- Reduce project-specific paths.
- Convert pressure-sample lessons into generic fixture coverage only when
  needed.

Priority 3: Knowledge-base feedback candidates

- Produce candidate-only feedback documents for Company review.
- Mark all items as candidates, not confirmed company memory.
- Separate facts, interpretations, recommended rule changes, and open
  decisions.

Priority 4: Mainline integration and slimming

- Preserve useful evidence.
- Replay generic lessons into product slices.
- Retire or archive project-specific surfaces that do not support the generic
  AFS landing path.

Priority 5: Browser-level product validation

- Verify the workbench as a real local operator surface, not only through
  static tests.
- Keep provider calls gated.
- Keep human acceptance separate from tests.

## Current Boundary

This document is a candidate strategic projection. It is safe for AFS planning,
but it is not durable company memory, not business validation, and not human
acceptance.
