# Feedback Contract

`feedback.jsonl` records human or agent review decisions about clips,
candidates, packages, and runs. It is the smallest bridge from AgentFlow Studio
delivery results to future AgentFlow Memory.

AgentFlow Studio `v0.1.0` does not implement a memory runtime. This contract only
defines the local event shape that future tools can append and read.

## Event Fields

- `schema_version`: contract version, currently `"0.1"`.
- `feedback_id`: stable event id.
- `target_type`: `clip`, `candidate`, `package`, or `run`.
- `target_id`: id from the relevant artifact.
- `decision`: `accepted`, `rejected`, `needs_revision`, or `note`.
- `rating`: optional integer from 1 to 5.
- `reason_tags`: short machine-readable reasons.
- `user_note`: optional human note.
- `created_at`: ISO timestamp.

## Example

See [`../examples/contracts/feedback.example.jsonl`](../examples/contracts/feedback.example.jsonl).

## Agent Notes

Agents should not silently overwrite feedback. Append new JSONL events and keep
the original package/run artifacts unchanged. A future memory layer can then
promote repeated feedback patterns into user preferences.
