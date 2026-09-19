## Findings

| Severity | Cell(s) | Finding | Fix |
|---|---:|---|---|
| Material | 47, 48, 0 | The unlimited-floor family is described incorrectly. Cell 47 says the 33% concentration cap “is the sleeve” and “at most three names can fill the book”. A per-name cap does not limit the number of names; it sets a maximum weight. The executed unlimited capped book holds 24.7 names without the floor and 14.3 at floor 1.0. The heading then incorrectly says it is “holding EVERY vault above 1.0”, although about 20.3 qualify and only 14.3 are realised holdings on average. | Describe this as an unlimited-capacity, capped-weight implementation with no cash sleeve. Remove “at most three” and “every vault”; report qualifying versus realised holdings. The run still supports failure of this specific unlimited variant, not a claim about investing in every qualifying vault. |
| Material | 0, finding 4 | “The extra return is concentration, not selection” exceeds the evidence. Cell 42 establishes that the four-name books’ capital is in vaults also held by the anchor; it does not isolate the effect of reducing N/reweighting from selecting a different subset or from changed trade timing. | Say the high overlap and much higher weights are consistent with concentration being a major contributor. Do not present it as an identified causal decomposition. |
| Minor | 0 | The opening summary over-generalises: it says all six-name leads overlap the anchor by 95–99% of capital and all four-name leads hold the engine position at twice the weight. The cited outputs substantiate this for `thr150`/`measured_8` and the relevant N=4 runs, but not `thr100` or `thr100_n4`; `thr100` differs on 51.6% of decisions and `thr100_n4` does not hold the June–August engine position. | Scope these statements to the named runs for which the numbers are shown. |
| Minor | 0, robustness section | “The floor’s damage is not a coverage artefact” is too categorical. The anchor-held coverage is high (734 of 756 holding-decisions), and the important engine position is measured, so the evidence is strong that coverage is not the whole explanation. But 79 of 148 candidates per decision are unmeasured and automatically excluded, so coverage remains part of the construction’s effect. | State that poor coverage is not sufficient to explain the main engine-position loss, while retaining that unmeasured candidates are excluded by design. |

## Checks that pass

- The first- and second-round repairs are present: matched unlimited comparator, matched N-neighbours, two-sided plateau handling, survivor reconstruction, full engine-position listing, and correctly limited aligned-P&L language.
- The quality score is causal through the T−1 interface; its row-window/freshness guards and zero-return treatment are internally consistent.
- The floor is correctly placed after the crash filter and before ranking. The empty-book path is supported by the smoke test and realised close-out behaviour.
- Sleeve arithmetic is sound, and the full-run table is honestly worded as realised deployment no greater than intended deployment.
- Cycle Sharpe and volatility use the native two-day clock with sample standard deviation.
- The third-round heading mostly avoids formal re-verdicting of post-hoc grid points. `thr175` is correctly framed as exploratory sensitivity, and aligned attribution is not called causal.

## Overall verdict

**Not ready to sign off as written, but no blocking backtest or sleeve-implementation error was found.** The direct result remains supported: this floor-and-cash-sleeve construction is not rescued by the standing-gate calculations. The unlimited-family description and the concentration/selection causal wording need correction before the notebook can be treated as an accurate forensic interpretation.