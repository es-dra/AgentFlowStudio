# AFS-COMPANY-KB-FEEDBACK-PACKET-001 Feedback Candidates

Status: candidate list only. Do not auto-promote.

Source slice: `AFS-COMPANY-KB-FEEDBACK-PACKET-001`

## Candidate Items

| Candidate | Why It May Matter | Promotion Boundary |
|---|---|---|
| Generate a Company KB feedback candidate packet from a production-memory session report. | Gives AFS a concrete project-to-Company feedback artifact without editing the source Company knowledge base. | Candidate only until reviewed in the Company memory governance process. |
| Keep `writes_company_kb: false`, `promotion_status: candidate_only`, and `requires_human_review: true` on the packet root and item level. | Prevents project lessons from silently becoming company memory during KB restructuring. | Candidate only; Company source writes require explicit user instruction. |
| Derive candidate items from session-level evidence instead of raw private notes. | Keeps the repo projection sanitized while preserving reusable engineering lessons. | Candidate only; do not copy private strategy, costs, customer details, or provider secrets. |
| Record source KB status as metadata. | Lets the packet remain useful while the source Company KB is being restructured. | Candidate only; source KB state is not a product validation claim. |

## Explicit Non-Promotions

- This file does not promote AgentFlow Studio evidence to Company memory.
- This file does not write the local Company source knowledge base.
- This file does not define durable Memory OS behavior.
- This file does not claim human acceptance or business validation.
- This file does not authorize provider calls.
