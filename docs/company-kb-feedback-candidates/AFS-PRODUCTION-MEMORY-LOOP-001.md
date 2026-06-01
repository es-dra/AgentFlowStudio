# AFS-PRODUCTION-MEMORY-LOOP-001 Feedback Candidates

Status: candidate list only. Do not auto-promote.

Source slice: `AFS-PRODUCTION-MEMORY-LOOP-001`

## Candidate Items

| Candidate | Why It May Matter | Promotion Boundary |
|---|---|---|
| Separate feedback, memory candidate, and promotion decision in every production-memory loop. | Prevents raw feedback from being treated as reusable memory. | Candidate only until reviewed against the Company memory governance rules. |
| Require `context_bundle.included_refs` and `context_bundle.blocked_refs`. | Makes next-context assembly auditable and shows why rejected or pending refs were excluded. | Candidate only; needs comparison with other project loops before becoming a company-wide rule. |
| Run no-provider Contract+CLI before any provider validation. | Keeps product architecture independent from live image/video provider availability. | Candidate only; provider policy belongs in the Company source KB after review. |
| Keep Web memory canvas read-only for this slice. | Reduces risk of accidental provider calls, browser persistence, or hidden writes while the loop contract is still forming. | Candidate only; future write actions need a separate approval model. |
| Treat project feedback to Company KB as a candidate queue, not an automatic memory write. | Supports a positive feedback loop while the local Company KB is being restructured. | Candidate only; do not write Company source files from AFS without explicit user approval. |
| Review promotion decisions as an overlay before rebuilding next context. | Lets the operator test a promoted or rejected feedback-derived candidate in the next-pass bundle without mutating the source loop. | Candidate only; needs more project loops before it becomes a company-wide memory workflow rule. |

## Explicit Non-Promotions

- This file does not promote AgentFlow Studio evidence to Company memory.
- This file does not define durable Memory OS behavior.
- This file does not claim human acceptance or business validation.
- This file does not authorize provider calls.
