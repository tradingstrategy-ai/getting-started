## 1. Do the heading's claims match the outputs?

| Heading claim | Finding |
|---|---|
| All tested configurations reject / none pass rule v2 | Supported. Cell 27 reports `passes_v2 = False` for every row. |
| Dial curve figures: 7.8% / 13.9% / 11.8% / 4.3% CAGR at 0.5 / 0.7 / 0.85 / 1.0 | Supported by Cell 29: 7.762%, 13.896%, 11.756%, 4.279%. |
| `core_0.7_n3`: 21.48% CAGR, 1.170 Sharpe, 16.41 pp sacrifice | Supported by Cell 27. It passes only the CAGR floor; it also fails volatility, ulcer, beta, deployment and placebo evaluability. |
| `core_0.7_n5`: -23.0% CAGR, -1.347 Sharpe, young P&L -$11,714 | Supported by Cells 27 and 34. |
| Pure evidence book: -14.6% CAGR, -1.27 Sharpe | Supported for this NB18 configuration by Cell 27. Its comparison with NB16 is not evidenced inside this extract. |
| Centre realised core weight is 0.657 versus 0.700 | Supported by Cell 36, but it is a post-normalisation target weight, not demonstrated executed/held weight. |
| Centre core: 53 positions, +$1,225, mean score 0.986; satellite: 36, +$12,597, score 0.656 | The supplied Cell 36 output contains only the core row: `53 / 1224.544243 / 0.986027`. The satellite row is absent from the extract, so its figures and the ensuing $41,990 calculation are unsupported here. More importantly, the attribution method is incorrect; see section 2. |
| “About 24×” satellite outperformance | The arithmetic is correct conditional on the stated inputs: $1,225 / 0.70 ≈ $1,750; $12,597 / 0.30 ≈ $41,990; ratio ≈ 24.0. But the satellite input is absent and both sleeve P&Ls are misclassified by the code. |
| `core_0.7_n3` is the only positive young-cohort result | Contradicted by Cell 34. It shows positive young P&L for `core_0.7_n4` (+$904.92), `core_0.85_n4` (+$3,261.07), and `core_1.0_n4` (+$3,224.95), as well as `core_0.7_n3` (+$6,450.51). |
| Fewer core names “work far better” because they exclude marginal evidence names | The n3/n5 performance contrast is real, but the causal claim is unsupported. Moving 3→5 changes both core membership and the satellite sleeve from three slots to one, plus concentration and pool-cap interactions. |
| N3 is the best configuration “anywhere in the plan” | It is the best NB18 row by CAGR in Cell 27. This notebook does not contain NB16/NB17 outputs, so the wider-plan superlative is not independently established here. |
| N3 is only a plateau neighbour, with no own plateau, LOO or bootstrap | Supported by the run geometry in Cell 25. The notebook runs n3 once only; Cell 31’s leave-one-vault-out is for n4. |
| Earlier diagnostic corruption was fixed, with 126 populated entries and genuine overlap | The new dedicated log avoids the original framework overwrite, but this extract contains no output validating “126” entries, uniqueness, or overlap. Those are unsupported assertions in this notebook. |

## 2. Correctness of the code that produced the numbers

The strategy-performance panel is substantially more reliable than the sleeve attribution.

Decision-time feature reads are correctly one bar behind the decision. `decide_trades()` uses `input.indicators.get_indicator_value(...)`; the framework implementation explicitly says it “does not return the current timestamp value” and that the default returns the previous available candle. Thus the core ranking, satellite ranking, gate, and sizing inputs do not have a direct look-ahead issue.

The original diagnostic collision is genuinely avoided. The framework later executes:

```python
state.visualisation.add_calculations(
    timestamp,
    {'unallocatable_signals': alpha_model.get_unallocatable_signals()},
)
```

whereas the replacement writes to the separate module-level `SLEEVE_LOG`. The framework cannot overwrite that separate dictionary.

For the executed order, cross-run contamination is also unlikely:

- Placebo and anchor runs use `core_fraction=None`, so they do not write `SLEEVE_LOG`.
- Every actual sleeve variant is called through `run_and_record()`, which clears before the run and snapshots afterwards.
- The centre snapshot is taken before the later leave-one-vault-out run clears the log.

However, this is not fully hardened. `run_variant()` itself does not clear `SLEEVE_LOG`; it relies on its caller. `max(SLEEVE_LOG)` also has no assertion that it is strictly the immediately preceding timestamp, and there is no assertion that keys are unique or that the expected 126 entries were produced. A direct core-enabled `run_variant()` call outside this wrapper could silently inherit a prior run’s final sleeve assignment.

The material bug is Cell 36’s attribution:

```python
all_core_ids = set()
for c in calc_by_ts.values():
    all_core_ids.update(c.get("core_ids", []))

sleeve = "core" if position.pair.internal_id in all_core_ids else "satellite"
```

This labels a whole position “core” if its vault was core in any cycle. A position can remain open while its vault moves between core and satellite. Its full realised P&L, and its original entry score, are then assigned to the later-or-earlier union classification rather than to the sleeve that owned the capital over time. Therefore the reported sleeve P&Ls, position counts, mean entry scores, and the “24×” inference are not valid sleeve attribution.

There are two further attribution defects:

- `core_fraction_realised` is recorded after `alpha_model.normalise_weights()`, but before target positions and trade execution. It is the realised normalised target allocation after risk caps, not necessarily the actual sleeve share held after thresholds, suppressed trades, cash constraints, and execution.
- Entry score is reconstructed from `executed_at - one day`, not the recorded decision timestamp that selected the sleeve. If execution occurs after the decision timestamp, this can read information unavailable when the decision was made. It must instead use the logged decision timestamp and the framework’s previous-bar accessor.

The sleeve construction itself is mostly coherent: core is ranked by the evidence score, satellite is filled from incumbent ordering after core picks, and each sleeve is separately normalised before the portfolio normaliser. Validation for positive `core_fraction` and valid `core_assets` is present.

Two edge cases remain silent:

- A hold-protected former core position whose present core score is NaN is excluded from `core_ranked_all`; it is therefore not truly reserved to its former sleeve.
- There is no assertion that each sleeve reaches its requested number of assets. If the core is short, subsequent portfolio normalisation can give the surviving sleeve more capital than its nominal fraction.

Finally, with a two-day decision cycle and `minimum_hold_days = 1`, a position opened on one decision is normally already too old to be protected at the next decision. The hold-protection repair is structurally sensible, but likely inactive in this run; the heading does not demonstrate otherwise.

## 3. Statistical interpretation

The reject verdict is justified under the implemented pre-registered rule. Cell 27 shows every variant fails `passes_v2`; n3, the strongest CAGR result, has:

- CAGR 21.48%: passes the 20% floor;
- Sharpe 1.170: fails the 2.060 non-inferiority threshold;
- volatility 18.00%: exceeds anchor 15.43%;
- ulcer 2.37%: exceeds the required maximum of roughly 1.53%;
- beta 0.0742: exceeds anchor 0.0458;
- deployment 89.44%: misses the 90% floor;
- placebo: not evaluable because its volatility lies outside the frontier range, which correctly fails under v2.

So “still a REJECT” is sound, although the heading understates how comprehensively n3 fails.

The heading is appropriately cautious that n3 is a single, post-hoc standout introduced as a plateau neighbour rather than a pre-registered candidate. It is nevertheless too promotional to call it the plan’s “best lead” without immediately foregrounding that it is a multiple-tested in-sample winner, has roughly 125 decision cycles across a polling-regime discontinuity, and fails six of seven adoption constraints. The later family-wise result of p = 1.000 reinforces that it is not evidence for adoption.

Young-cohort P&L is not independent confirmation of sleeve attribution. `hidden_cohort_reach()` sums `position.get_total_profit_usd()` over positions classified by age at entry. Cell 36 sums that same position-level P&L over a flawed sleeve classification. The dimensions overlap: a young position may be core or satellite, and the same P&L can support both narratives. A core/satellite × young/old cross-tab with time-consistent capital/P&L attribution is required before interpreting the two tables together.

## 4. What should be re-run or checked before these results are trusted

1. Rebuild sleeve attribution at decision/trade level. Record each decision timestamp, sleeve, target weight, executed position change, and subsequent P&L interval. Do not classify positions using the union of all historical `core_ids`.

2. Recompute the Cell 36 table from that ledger, including a young/old × core/satellite cross-tab. Withdraw the current $1,225, $12,597, score-gap, and 24× claims until this passes reconciliation to total portfolio P&L.

3. Add and display log invariants for every sleeve run: clear-at-run-start, expected cycle count, unique strictly increasing timestamps, disjoint core/satellite IDs, slot counts, and confirmation that every protected incumbent remains in its previous sleeve.

4. Audit the score at the actual logged decision timestamp, using the prior-bar indicator value. Compare it against the score used by `decide_trades`, rather than inferring it from `executed_at`.

5. Re-run the centre and n3/n5 configurations with the log invariants enabled and compare equity curves, trades, selected IDs, and target weights against this run. This tests whether correcting the diagnostics changes any hold-protection path.

6. Treat n3 as a new hypothesis, not an adoption candidate. Any follow-up neighbourhood, leave-one-vault-out, and statistical testing should be explicitly pre-registered and evaluated independently of this in-sample search.

## 5. Verdict

**RESULTS STAND WITH CAVEATS**

The central result — no NB18 configuration meets the pre-registered adoption rule and the notebook’s verdict is REJECT — stands.

The per-sleeve attribution does not stand: its union-of-ever-core-IDs classification is wrong, its satellite output is absent from the supplied extract, and its entry-score timing is not decision-aligned. The claim that n3 is uniquely positive on young-cohort P&L is directly contradicted by Cell 34.