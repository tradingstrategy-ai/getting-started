## Overall verdict

The second-round fixes largely work. The core observed results remain supported: both anchor sells are open-valued partial catches; the collapse losses are open-to-close; `gate12_2d` underperforms; and `anchor_1d` fails gate 7.

| Severity | Cell | Finding | Concrete fix |
|---|---:|---|---|
| Material | 36 | `AUGUST_CAUGHT` verifies only that `planned_mid_price == decision_bar_open`. Unlike the cell-34 fill predicate, it does not require `market_feed_delay == 0`, matching non-async flags, or `executed_at == decision`. A delayed, forward-filled price could therefore satisfy the equality and wrongly stop the one-day/cluster branches. | Apply the same fail-closed checks to the 19-Aug gate trade: zero feed delay, non-async pair, decision-time execution, finite/open match, and assert it was held entering the decision and removed by its own tighter gate. |
| Minor | 26 | The async branch does not consistently handle all three advertised flags. It treats the first two pair flags as the agreement test but ignores `settlement_override` when they are true. Thus a true pair-async status with a false override is accepted rather than being classified as disagreeing. This path was unreachable for the two displayed sells. | Define the override as either a separate configuration fact or include it consistently in the agreement predicate; test the async path directly. |
| Minor | 34 | The supposedly rule-selected rank-churn example is selected through `anchor_ledger["exit_reason"]`, which remains the known imperfect ranking reconstruction. The later exact churn classifier is not used to choose it. This does not affect the fill conclusion, because no four-way catch label is assigned to this trade. | Select the earliest sub-four-day closure whose address is present in the in-trade pool log at its closing decision; call it an “in-pool sell”, not a verified rank exit. |
| Minor | 32 | `first_strike_table()` evaluates every UTC day for the union of vaults that were candidates on any logged two-day decision. It does not require a vault to be a candidate on the particular classified day. The table is descriptive and ungated, but its sample is broader than “every candidate vault” naturally implies. | State that its cohort is the union of the two-day pool-log candidates, evaluated on all days; do not describe it as contemporaneous candidate-day evidence. |

What checks out:

- Cell 26’s pool-keyed ranking cache fixes the mixed-clock reconstruction issue.
- `churn_pnl_exact()` correctly recovers the tighter gate’s pool from the anchor pool logger: in this configuration, momentum threshold is the only run-dependent candidate-pool condition. The threshold recheck is therefore appropriate.
- The pre-decision holding predicate in cells 26/32 — `opened < t` and `closed is None or closed >= t` — is correct, as is using the prior statistics timestamp for weight. The erroneous 2026-01-01 newly opened position is gone.
- Cell 34 uses candle-row `open`, not a tautological pricing lookup. The raw archive in cell 30 independently supports that these two candle opens are the first marks of their days, not forward-fills.
- The two-day-grid Sharpe construction in cell 39 is correct: no missing anchor timestamps, then `cycle_returns()` gives 182.5 periods/year.
- The heading’s key figures agree with cells 30–41, and its revised language no longer attributes the whole-book outcome to the fire table or generalises beyond the tested variants.

The only material gap is the unverified gate12 fill condition used for the stop rule. Fix that before treating the skipped one-day and cluster runs as procedurally justified.