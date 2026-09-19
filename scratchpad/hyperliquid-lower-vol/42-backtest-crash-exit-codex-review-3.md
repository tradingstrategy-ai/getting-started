## Review findings

| Severity | Cell | Finding | Concrete fix |
|---|---:|---|---|
| Material | 41 | Window A runs are invoked directly through `run_variant()` and stored only in `WINDOW_RESULTS`; they are not added to `runs` / `run_by_label`. This breaches standing rule 7 and makes the Window A table and heading claims non-auditable through the notebook’s required single source of truth. | Record each Window A run with distinct labels via the recorder, retain states/equity/returns and logs, then build `window_a` solely from those entries. Include their labels in the manifest. |
| Minor | 26, used in 31 | `bucket_coverage()` resamples only between a vault’s first and last observed mark after filtering. Empty four-hour buckets at either regime boundary are omitted. Therefore the reported 4.5% dense and 81.2% sparse empty-bucket figures are not necessarily coverage over the stated full regime. | Reindex bucket counts to the explicit expected four-hour grid for the requested interval (and define whether coverage is over the regime or actual holding intervals), counting endpoint gaps as zero-mark buckets. Regenerate the cell-31 and heading figures. |
| Minor | 26 | The async consistency predicate tests only `is_async_vault` and `has_delayed_vault_redemption`; `settlement_override` is excluded from the disagreement test, despite the plan describing three flags. The executed path is unaffected—all three displayed flags are false—but the advertised fail-closed async branch is not fully implemented. | Either include the override consistently in the agreement predicate, or explicitly define it as a separate configuration assertion and remove it from the advertised three-flag agreement rule. |

## Checks that pass

- Cell 34 uses the decision candle’s `open`, not a tautological price lookup. The raw first-mark tables in cell 30 independently support that both opens equal the prior closes; the -29.6% and -32.2% moves are open-to-close.
- The third-round `sold_at_decision_open()` fix in cell 36 now checks non-async status, zero feed delay, execution at the decision, the 1e-9 open match, prior holding, and the tighter gate condition. The August stop rule is procedurally justified.
- The pool-keyed ranking cache and `churn_pnl_exact()` repair are correct. For the tighter gate, momentum threshold is the only run-dependent pool-construction condition; the threshold recheck is appropriate.
- The pre-decision holding rule in the fire counts is correct, including positions closed at the decision. Cell 32’s `(lo, hi]` interval and T-1 indicator read are correct.
- The one-day comparison correctly reindexes onto the anchor’s timestamps, asserts no missing timestamps, and annualises the resulting two-day grid at 182.5 periods/year.
- The first-strike table uses the intended strict T-1 three-return window, disjoint classes, and first entries. Its cohort and descriptive status are stated honestly.
- The heading’s substantive figures and verdicts match cells 30–39. The revised wording no longer attributes the full-book result to the fire table or generalises beyond the tested variants. The live-fill optimism limitation is correctly stated and explicitly not quantified beyond the two collapse days.

## Overall verdict

No blocking defect and no remaining material error in the fill, stop-rule, churn, clock, or headline-result logic. The core conclusion is supported: on this backtest engine the incumbent’s two collapse exits are open-valued partial catches, `gate12_2d` underperforms, and `anchor_1d` fails gate 7.

However, cell 41 needs repair before the notebook fully complies with its audit rules; its Window A claims currently bypass the required run ledger.