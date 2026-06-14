# Company OS Feedback Candidate - AFS Joint QA

## Candidate

For paid-provider closeout work, use checkpoint review as a bounded evidence
gate, not as step-by-step co-piloting.

## Evidence

The AFS MVP joint QA run used Claude checkpoints for:

- pre-live provider gate review;
- live-call cap review;
- planned closeout review.

This helped keep evidence boundaries explicit while Codex continued execution.
The useful pattern was the hard-call ledger:

- LLM calls, including format retries, count against the cap;
- image arms and retry count count against the image cap;
- video submit and video poll are separate counters;
- ASR and external downloads stay at zero unless explicitly scoped.

## Proposed Rule Shape

When a task opens remote model/provider gates:

1. Define capability-specific caps before live execution.
2. Treat retries as provider calls unless the provider contract proves otherwise.
3. Save checkpoint prompts/responses as sanitized evidence outside repo raw runs.
4. Record only safe summaries in the project repo.
5. Do not claim human acceptance from provider smoke or AI role pre-acceptance.

## Limits

This is candidate guidance only. It should not be promoted to an active Company
OS rule without human review across more than one provider-heavy project.
