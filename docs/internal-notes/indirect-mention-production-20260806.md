# Indirect mention → production candidates (2026-08-06)

Status: **production-ready behind paid flag** (default off). Not pushed / no PR.

## What shipped

| Item | Detail |
|---|---|
| Flag | `AFS_ENABLE_INDIRECT_MENTION_LLM_PROPOSALS` default **off** |
| Budget | `AFS_INDIRECT_MENTION_LLM_MAX_CALLS` default `12`; over-budget → `budget_skipped_unjudged` |
| Cost class | `paid_remote_llm` — **not** free like alias / scene-normalization flags |
| Emit rule | `refers_to_real_character && !is_present_in_scene` (+ `_is_person_name` shape gate) |
| Authority | `create_manual_character` preview→confirm only; ordinary review does not promote |
| Studio | `/manual-character` thin entry |

## Regression

- Focused: discovery + proposals unit + candidate extraction API — green
- OpenAPI snapshot regenerated — includes `IndirectMentionProposal` / `create_manual_character`
- Full non-browser suite: **2171 passed**, 9 skipped
- `git diff --check`: clean on touched paths

## Live API e2e (paid)

Script: `tools/indirect_mention_live_e2e.py`  
Report: `docs/internal-notes/indirect-mention-live-e2e-20260806.json`

| Check | Result |
|---|---|
| Flag off | proposals absent, `provider_dispatch_count=0` on all 5 scripts |
| Flag on gold | 沈岚 / 江澄 / 顾衡 / 柯衡 all proposed |
| Noise deny-list | 别自己拆 / 默记修缮 / 晚上见 / … not proposed |
| Authority | review of 刘正 did not create 顾衡; `create_manual_character` did |

### New issues found in live e2e (honest)

1. **Long quoted clause false positive** (fixed before finalizing): LLM marked  
   `第七格——顾衡案——不得夜班单独开启。` as refers=true.  
   Mitigation: post-judgment `_is_person_name` gate (unit-tested).
2. **悦安** still proposed on echo_inn (known alias-on-stage boundary; not fixed).
3. Other person-shaped proposals appeared and need human review: `苏衡`, `晚晚`, `陈默`  
   (not in the gold set; not auto-authoritative).

## Honest verdict

**Not “fully solved.”** The production path is wired to the same candidate / confirm
standard as alias & scene-normalization, with clear paid-cost labeling and a human
authority gate. Validated gold cases work end-to-end.

Remaining boundaries: 悦安 present-in-scene conservatism; residual person-shaped
ambiguous mentions; LLM still costs real money/latency per extract when enabled;
open CJK NER still off.
