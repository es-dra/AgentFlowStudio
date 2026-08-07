# Long-script stability — analysis notes

## Protocol choice

Deliberately **not** precision/recall. Understanding accuracy on long text is
already covered by aliases + indirect-mentions. This dimension is a checklist:

1. free-path bit-determinism
2. discovery volume ceilings
3. paid budget truncation (mock judge)
4. crash-free

## 2026-08-06 real run

- Corpus: 2 long + 3 generalization scripts
- Remote LLM calls: **0** (mock judge)
- Wall time: ~0.05s
- Checklist: **25/25 probes passed**

| Script | chars | discovery | /1k chars | notes |
|---|---:|---:|---:|---|
| L1 echo_inn | 3238 | 6 | 1.85 | long |
| L2 night_post | 2898 | 12 | 4.14 | densest discovery |
| G1 office | 557 | 4 | 7.18 | short but quote-dense |
| G2 campus | 457 | 3 | 6.56 | |
| G3 lab | 400 | 4 | 10.0 | highest density (short) |

Volume insight: short generalization scripts can show **higher discovery density
per 1k chars** than long scripts (quote/noise density), while absolute counts
remain small (≤12). Soft ceiling 40 / hard 80 are comfortable for this corpus;
they are operability tripwires, not accuracy targets.

Budget: `max_calls=3` truncates correctly on **eligible** mentions after
known-identity suppression. First probe draft wrongly expected
`skipped = discovered - N` and falsely failed L1/L2; fixed to
`eligible = discovered - suppressed`.

## Limits

- Does not claim remote LLM judgment repeatability.
- Does not re-score alias/indirect accuracy on long text.
- Ceilings are corpus-informed heuristics; open NER would break them by design.
