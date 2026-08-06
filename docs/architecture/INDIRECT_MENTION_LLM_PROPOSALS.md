# Indirect Mention LLM Proposals (Paid Path)

Indirect-mention proposals find character names that appear only by reference
(letters, phone calls, photo backs, hearsay) and are not on-stage in the
current scene.

## Cost warning (read this first)

This path is **not** like the free deterministic proposal flags:

| Flag | Cost |
|---|---|
| `AFS_ENABLE_ALIAS_LINK_PROPOSALS` | Free / deterministic |
| `AFS_ENABLE_SCENE_NAME_NORMALIZATION_PROPOSALS` | Free / deterministic |
| `AFS_ENABLE_INDIRECT_MENTION_LLM_PROPOSALS` | **Paid remote LLM** per judged mention |

Enabling `AFS_ENABLE_INDIRECT_MENTION_LLM_PROPOSALS` issues real chat-completion
calls through the provider registry (`prompt_optimizer` by default). It also
requires the normal remote gates (`AFS_ALLOW_REMOTE_LLM`, `AFS_PROVIDER_CONFIG`).

Call budget:

- `AFS_INDIRECT_MENTION_LLM_MAX_CALLS` (default `12`) caps LLM calls per extract.
- Mentions beyond the budget are returned as
  `indirect_mention_budget_skipped` with `status=budget_skipped_unjudged`
  (never silently dropped).

## Judgment semantics

Discovery is structural wide recall (quotes + mention cues; no open CJK NER).
The LLM answers two independent fields:

- `refers_to_real_character` — is the mention string itself a real story person?
- `is_present_in_scene` — is that person on-stage in the given window?

Derived: `is_indirect_mention = refers && !present`.

Only that combination is emitted as an `indirect_mention_proposals` entry with:

- `status: candidate`
- `authority: non_authoritative_proposal`
- `cost_class: paid_remote_llm`
- `review_action: use_core_asset_command_create_manual_character`

Extract never creates character assets from these proposals and never writes
Production Graph state.

## Human confirmation (only authority path)

```text
POST /projects/{project_id}/core-assets/commands/preview
POST /projects/{project_id}/core-assets/commands/confirm
command_type: create_manual_character
patch.display_name / patch.mention: <name>
patch.evidence_spans: optional spans from the proposal
patch.proposal_id: optional proposal id for lineage
```

Ordinary analysis-asset review (`confirm` / `reject` on extracted named
characters) does **not** promote indirect-mention proposals.

Exact identity guard on `create_manual_character`:

- Preview/confirm rejects (409 `manual_character_identity_exists`) when the
  requested surface exactly matches an active character's `display_name`,
  `name`, or `aliases` on the same revision.
- Callers should use `merge_alias` for nicknames of an existing character.
- True homonyms (two distinct people who share the same surface string) must
  set `patch.allow_duplicate_display_name=true`. Different names that only
  share a surname (e.g. 陈默 vs 陈明) are unaffected.

Studio thin entry: `/manual-character <name>` (same preview → confirm loop;
no auto-accept).

## Known-identity suppression (proposal emit)

Mentions that exactly match an extracted canonical name or a known confirmed
identity surface (revision asset name/aliases) are **not** emitted as
`create_manual_character` proposals. They appear under
`indirect_mention_suppressed_known_identity` with
`status=suppressed_known_identity` so the signal is explicit, not silent.

## Known limitations (intentionally not fixed here)

- **悦安-class alias-on-stage boundary**: when a nickname refers to an on-stage
  character but the judge cannot safely prove present-in-scene from the
  mention string alone, the conservative outcome can be
  `refers=true, present=false` (proposal emitted). Operators should treat this
  as a review signal, not automatic identity merge.
- **Long quoted clauses containing a name**: live e2e saw the model mark
  `第七格——顾衡案——不得夜班单独开启。` as `refers=true`. Production now applies a
  post-judgment `_is_person_name` shape gate so such clauses are not emitted as
  proposals (the embedded short name like `顾衡` can still be proposed from its
  own discovery hit).
- Open unquoted CJK NER remains disabled (~500–600 hits per long script).
- LLM quality depends on the configured remote model; budget skips are honest
  when the call cap is hit.
- Other person-shaped mentions that are narratively ambiguous (e.g. `晚晚`,
  `苏衡`, already-extracted names reappearing in quotes) may still become
  proposals and require human review via `create_manual_character`.
