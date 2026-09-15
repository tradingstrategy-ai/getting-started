# Volatility tail-exclusion plan: the one lead, gated properly

- **Status**: DRAFT 2, 2026-09-16, after Codex CLI review
  ([34-volatility-tail-exclusion-plan-codex-review.md](34-volatility-tail-exclusion-plan-codex-review.md),
  `gpt-6-astra`: "makes sense as exploratory research, but its claim to be 'the one lead, gated
  properly' is premature"). Two blocking and seven material findings applied; see §Review log.
- **Rules**: [RESEARCH-RULES.md](RESEARCH-RULES.md), with the amendments in §Rule changes. They
  are EVIDENCE-INFORMED REVISIONS made after NB28-NB33 and frozen before NB34 runs. Freezing them
  now stops further tuning during this plan; it does not make them independent of the results
  that motivated them, and the earlier verdicts under the old rules stand as recorded.
- **Track**: `hyperliquid-lower-vol`, NB34-NB36. Supersedes
  [28-stable-selection-plan.md](28-stable-selection-plan.md), which closed with nothing shortlisted.
- **Anchor**: [02-better-format.ipynb](02-better-format.ipynb), which is
  `~/code/strategies/strategy/hyper-ai.py` (v6) parameter for parameter, verified in
  [_build/verify-hyperai-window.ipynb](_build/verify-hyperai-window.ipynb).

## One sentence

Before the incumbent ranks its candidates, remove the eight most volatile of those whose
volatility can actually be measured; change nothing else; test whether that clears the nine
gates. **Eight is an exploratorily selected count, now frozen.** The three windows it has been
run on overlap heavily and are sensitivity checks, not independent confirmation; NB33's
post-July segment has it at -2.3% against the anchor's -2.1%. What this plan can produce is a
defensible shortlist for prospective evaluation. It cannot turn the search that found the
count into confirmation of it.

## What the previous research established, and what this plan does with it

| finding | where | consequence here |
|---|---|---|
| Trailing 90-day volatility predicts forward 30-day volatility at signed Spearman 0.70 (simultaneous lower bound 0.55 over 39 hypotheses) and forward downside at 0.65. No other price metric does better and the whole family is collinear with it. | NB28 | The signal is `inverse_vol`. The screen is re-run once, for coverage and for the restricted regime below, not to choose a signal. |
| No price metric establishes any association with forward event concentration; a perfect-foresight oracle needs all three targets to pass the clause, and volatility foresight alone fails it because the two targets correlate +0.07. | NB28 | Gate 5 drops the concentration target. Requiring it made the gate unpassable by any price signal. |
| The gate-5 return clause, a non-inferiority test on a MEAN forward return, has a half-width 20-60x its margin because the cross-section contains -13 log-return blow-ups. | NB28 | The return clause becomes a median-based contrast. |
| Ranking by any stability measure destroys return (best 8.9% CAGR of thirty configurations); excluding the volatile TAIL and letting the incumbent rank improves everything. | NB32, NB26, NB29 | The mechanism is a prefilter, never a ranker. |
| `measured_8` beats the incumbent on all six headline metrics on three windows - the track window, the incumbent's own window, and the full data period - and retains 0.860 of its Sharpe under the single-vault mask against the incumbent's 0.825. | NB26, NB29, NB33 | It is the centre. It was never gated as a candidate because its signal could not pass the old gate 5. |
| Excluding the UNMEASURED candidates as well changes nothing, to 0.0 on every metric and every cycle return. | NB29 | The prefilter is permissive. The strict variant is a diagnostic. |
| The return floor is worse than the incumbent on the incumbent's own window and flips sign between 15% and 20%; the floor-plus-drop combination is worse than either alone. | NB33 | Neither is in this plan. |
| The candidate pool is young: 21% of candidate-dates are under 90 days old, 43% under 180, 72% under 360. Before 2026-04-01, 99% of 180-day-old vaults had fewer than 60 price-changing marks in 180 days. | 2026-09-15 check | Windows are 90 rows with a fresh-mark guard; path-dependent metrics are not scored on the sparse regime; gate 5 is evaluated on post-break decisions only. |
| Under uncorrelated zero-mean increments, the expected squared multi-day jump equals the sum of the daily variances it spans, so forward-filled calendar variance is not systematically biased by sparse polling in EXPECTATION; it loses effective observations, and the identity says nothing about drift, serial dependence, noisy marks or the demeaned sample standard deviation actually computed. Path metrics - downside, drawdown, concentration - lose their information irrecoverably in the gaps. | 2026-09-15 check | The signal stays on the calendar clock with a minimum fresh-mark count as a heuristic for observation adequacy, not as a correction that establishes estimator validity. Event-time sampling is not used. |
| Gate 8's "mean holdings at least the anchor's 6.00" rejected a candidate at 5.992 while four of five diversification measures were better. | NB29 | Gate 8 gets an OPERATIONAL tolerance, stated as such: 5.992 really is below 6.000, and the tolerance is a policy choice about how often a five-name book is acceptable, not an arithmetic fix. |
| The engine's stored redemption fee differs from `10% x max(profit, 0) + 10 bps` on 734 of 1,653 redemptions, always in the engine's favour, cause undetermined. | NB29, NB31 | A common formula error does NOT cancel between configurations with different turnover and redemption timing. NB35 and NB36 quantify the DIFFERENTIAL fee error, candidate minus anchor, and a SHORTLIST requires it to be small against the claimed edge (§Rule changes, 6). |

## Rule changes, evidence-informed and frozen before NB34

Six amendments to [RESEARCH-RULES.md](RESEARCH-RULES.md), recorded in that file in the same
commit as this draft. Each responds to a defect found in NB28-NB33; none is independent of
those results, and the verdicts reached under the old rules are not revised.

1. **Gate 5 targets.** Forward volatility and forward downside variation over `(T, T + 30d]`
   from the NAV carried at T. Forward event concentration is dropped because its measurement is
   compromised - the raw share is bounded below by 5/n and the path inside an unobserved gap is
   not identifiable - which is a narrowing of the objective, not a claim that concentration is
   unpredictable in principle. Both targets must clear a simultaneous lower bound of zero over
   the family of 2 x (signals screened), on shared date-block and vault-cluster resamples, with
   complete 30-day forward windows only.
2. **Gate 5 return clause: typical-vault return non-inferiority.** Per date, the median forward
   30-day log NAV return of the retained set minus that of the excluded set, at the mechanism's
   OWN exclusion (the eight most volatile measured candidates, determined from decision-time
   information before any row is dropped for a missing outcome), averaged over dates, same
   shared bootstrap, one simultaneous family across both screened signals. Its lower bound must
   exceed **-0.005** (half a percentage point of 30-day log return). This is an economic
   tolerance - about 6% a year of typical-vault return given up for stability - and it is a
   fresh choice. The clause protects against "stable because dead"; it does NOT protect
   expected portfolio return or crash exposure, because a median ignores a minority of
   catastrophic outcomes. So the share of retained and excluded vaults with forward return
   below -0.5 log is reported beside it as a DIAGNOSTIC, together with the provenance of the
   extreme observations.
3. **Gate 8 tolerance.** `mean_holdings` must be at least **5.95**: a five-name book on no more
   than one decision in twenty. The other four measures are unchanged. This is 6.25x the
   shortfall NB29 observed, and it is a policy choice about breadth, stated as one.
4. **Gate 3 scope.** The concentration leg of gate 3 uses a 180-row trailing indicator that is
   not identifiable on this archive: a post-break decision still carries a mostly forward-filled
   180-row history until late September, past the end of the data. Gate 3 is therefore scored
   on its VOLATILITY leg alone - capital-weighted own realised volatility of the held book,
   lower than the anchor's, on decisions from 2026-04-01 - and both concentration indicators are
   reported beside it as DIAGNOSTIC with their coverage. If the volatility leg has fewer than 40
   evaluable dates, gate 3 is unevaluable and FAILS.
5. **Gate 9 null: scope and count.** Nineteen seeds, so that beating every draw is an add-one
   permutation p of 1/20 = 0.05. The null permutes the finite signal values within each date,
   which destroys ranking information AND temporal persistence; a pass therefore means the
   centre cleared a random-exclusion hurdle with matched missingness, not that volatility
   information is isolated as the cause. The null runs' turnover and basket persistence are
   reported beside the centre's so that difference is visible. A failure means "did not clear
   this hurdle", not "selects on no information".
6. **Fee differential.** For every candidate, NB35 and NB36 compute the net signed discrepancy
   between the engine's stored redemption fee and `10% x max(gross - released cost basis, 0) +
   10 bps`, in dollars, and subtract the anchor's. A SHORTLIST additionally requires that
   differential, expressed as a share of the candidate-minus-anchor final-equity difference, to
   be below **0.25** in absolute value. Above that, the verdict is DIAGNOSTIC: the claimed edge
   is within the range the fee error could account for.

And one scope statement: **gate 5 is evaluated on decisions on or after 2026-04-01 only.** Forward
downside is a path metric; before the polling-density break the path inside a 30-day window is
mostly unobserved. That leaves roughly 65 eligible decisions with complete forward windows,
about four months, and very few non-overlapping 30-day horizons; the plan says so and does not
claim more resolution than that gives. Pre-break decisions are screened separately as a
DIAGNOSTIC.

## The mechanism

`stability_prefilter` from `blocks_prefilter.py`, unchanged, with one signal:

```python
    stability_prefilter_signal = "calm_score"        # inverse_vol behind a fresh-mark guard
    stability_prefilter_direction = "low"
    stability_prefilter_count = 8                    # centre; neighbours 6 and 10
    stability_prefilter_strict = False               # permissive - unmeasured candidates are kept
```

`calm_score` is `blocks_floor.py`'s indicator: `1 / rolling 90-row std of daily returns`, NaN
unless at least 30 of those rows are price-changing marks AND the last one is within 10 rows.
It is `inverse_vol` made honest about how many observations it has. Two things it is NOT:

- not a ranker - after the exclusion, `cagr_sortino_weight` ranks and `inverse_variance` sizes
  exactly as `hyper-ai.py` does;
- not event-time - under uncorrelated increments the calendar estimate is not systematically
  biased by sparse polling, only starved of effective observations; the guard is a heuristic
  minimum on those observations, not a proof that the estimator is valid.

The guard cannot increase coverage: `calm_score` is `inverse_vol` with additional candidates
masked, so it covers a SUBSET. Its purpose is that an exclusion is never decided by an estimate
built on fewer than 30 real observations; NB34 reports how many candidate-dates the guard masks
and why. Under permissive exclusion the guard PROTECTS unmeasured vaults from exclusion; it is
not a defence against holding them.

The plan also carries `measured_8` itself - the same exclusion on raw `inverse_vol` without the
guard - as the CALENDAR REFERENCE, because it is the configuration with the three-window
record, and it goes through every gate the centre does, including its own null and
leave-one-vault-out runs. If both are shortlisted the tie-break applies; if only `measured_8`
is, the guard is not adopted.

## Hypotheses, pre-registered

- **H1** (NB34). `calm_score` and `inverse_vol` both clear gate 5's two stability targets on
  post-break decisions. `calm_score` covers a subset of `inverse_vol`'s candidate-dates; the
  masked share is reported and is expected to be a few percent.
- **H2** (NB35). At the centre, on the track window, the prefilter meets gates 1-4 and 6-9 and
  the fee-differential condition, and is SHORTLISTED. Written now: gate 6 is expected to pass
  (NB26's family was flat from 6 to 10); gate 2 to pass (retention 0.860 measured); gate 8 to
  pass under amendment 3; gate 3 on its volatility leg to pass. Gates 9 and the fee differential
  are open: neither has been run for this mechanism.
- **H3** (NB35). The same configuration is better than the anchor on cycle Sharpe, cycle
  volatility and max drawdown on the incumbent's window and on the full data period. A
  consistency check on overlapping windows, not a gate and not independent confirmation.
- **H4** (NB35). The strict variant is inert to 0.0 on cycle returns.

What would refute the plan: gate 9 failing means the centre did not clear a random-exclusion
hurdle with matched missingness; gate 6 failing means eight is a spike; the fee differential
exceeding 0.25 means the edge is within the fee error; H3 failing means the track-window result
does not travel. None of these would establish that the mechanism is equivalent to random
removal - only that this protocol did not demonstrate an advantage.

## Verdict vocabulary

SHORTLIST / REJECT / DIAGNOSTIC. No ADOPT: every historical result is in-sample, and the screen
and the backtest still share the 30-day windows. A SHORTLIST is admission to a frozen
prospective specification, and the deployment decision is the operator's after the shadow
period, not the plan's.

## Experiment track

### NB34 - research: coverage and the two-target screen

**File**: `34-research-calm-score-screen.ipynb`. Verdict DIAGNOSTIC.

1. Logging run; panel of every candidate-date with `calm_score`, `inverse_vol`, the two forward
   targets and the forward return; missing-reason counts.
2. **Coverage table**: per decision date, candidates with finite `inverse_vol`, finite
   `calm_score`, both, neither; split at 2026-04-01. Vault age and fresh-mark distributions of
   the uncovered.
3. Screen on post-break decisions only, with the corrected `harness_rules_v2.py` machinery:
   evaluated-family max-T, shared resamples, add-one p-values. Family: 2 signals x 2 targets.
4. **Tail-aligned contrast at the ACTUAL exclusion** - the eight most volatile measured
   candidates per date, determined from decision-time information before any row is dropped
   for a missing outcome - on both stability targets, one simultaneous family of 2 x 2.
5. Return clause per amendment 2 at the same actual exclusion, one simultaneous family of 2,
   with the catastrophic-loss share diagnostic.
6. Pre-break decisions screened separately and labelled DIAGNOSTIC.
7. Manifest with provenance, both screens, coverage, tail contrasts.

### NB35 - backtest: the prefilter through the nine gates

**File**: `35-backtest-calm-tail-exclusion.ipynb`. Verdict SHORTLIST / REJECT.

Runs, all with `run_and_record()` from `harness_rules.py` so `PREFILTER_LOG` is cleared:

| label | signal | count | strict | window |
|---|---|---|---|---|
| `calm_6`, `calm_8`, `calm_10` | `calm_score` | 6, 8, 10 | no | track |
| `calm_8_strict` | `calm_score` | 8 | yes | track (DIAGNOSTIC) |
| `measured_6/8/10` | `inverse_vol` (raw) | 6, 8, 10 | no | track (calendar reference) |
| `calm_6/8/10__lovo`, `measured_6/8/10__lovo` | leave-one-vault-out, full re-simulation | | | track |
| `calm_8_null0..18`, `measured_8_null0..18` | within-date permutation of finite values, 19 seeds each | 8 | no | track |
| `calm_8`, `measured_8`, `anchor` | | | | incumbent window, full data period |

Gates in order: 1, 7, 4, 5 (from NB34's manifest, per signal), 3 (volatility leg, post-break
dates, per amendment 4), 8 (amendment 3), 6, then 2 and 9 only if all cheaper gates pass, then
the fee differential (amendment 6). Every Boolean listed; every failure string printed in full;
unexecuted is False. Inertness for every run. Null effectiveness asserted on distinct
cycle-return series; null runs' turnover and basket persistence reported beside the centre's.
Both concentration indicators reported as diagnostics with coverage.

`measured_8` is scored through the same gates, with its own null and leave-one-vault-out runs.

### NB36 - close-out

**File**: `36-backtest-calm-closeout.ipynb`. Re-runs every executed configuration in one kernel,
asserts provenance against both upstream manifests before using them, re-derives gate 5 from a
rebuilt panel and every other gate from the re-run states, cross-checks at 1e-9, audits every
run for integrity, recomputes the fee independently and reports the candidate-minus-anchor
differential against the equity difference (amendment 6), and writes the frozen prospective
specification: signal, count, permissive, comparator (the anchor on the same new data), and
the monitoring protocol. The 90-day horizon is a monitoring choice, not a claim of statistical
resolution: at its end the specification calls for EXTENSION if the candidate's cycle Sharpe is
within 0.5 of the anchor's on the same cycles and its drawdown no deeper, REJECTION if it is
worse than that on both, and otherwise another 90 days - with the explicit statement that a
deployment decision on 90 days of two-day cycles is the operator's judgement, not the data's.

## Out of scope, deliberately

- **Cadence and stale-mark hold rules.** The sketch-versus-engine gap (27% against 3.5%,
  unexplained by fees or the pool cap) points at two-day re-evaluation and inverse-variance
  sizing. That is the next plan, not this one; changing the mechanism and the cadence together
  would leave nothing attributable.
- **Structural signals** (leverage, largest-position share, leader fraction). Coverage is 16%
  of rows for the position fields. Not usable as a screen yet.
- **The return floor and the combination.** Rejected by NB33.
- **The fee schedule and the CAUSE of the one-sided fee discrepancy.** Track-level. Its
  DIFFERENTIAL effect between candidate and anchor is in scope (amendment 6); its cause is not.

## What I expect

`calm_score` and `inverse_vol` both pass the two-target screen on post-break decisions;
`calm_score` covers a few percent fewer candidate-dates. `calm_8` and `measured_8` are within
0.05 Sharpe of each other on the track window. The plateau holds and gate 2 passes. Three things
are genuinely open: gate 9 (the drop family has never been nulled, and NB26's random-removal
result is a warning, not a null distribution); the fee differential (never measured for any
candidate); and gate 3's volatility leg on post-break dates only (never measured on that
restriction). If gate 9 fails, the outcome is REJECT and what the track has established is that
this protocol did not demonstrate an advantage over random exclusion with matched missingness -
not that the mechanism is equivalent to it.

## Definition of done

- [x] Plan reviewed by Codex CLI; findings verified against the text before applied.
- [x] `RESEARCH-RULES.md` amended (six amendments and the post-break scope) in the same commit
      as Draft 2, before any notebook is built.
- [ ] NB34 built from `_build/build_34.py`, run, reviewed, heading generated from its manifest.
- [ ] NB35 likewise; every gate Boolean present; failure strings complete.
- [ ] NB36 likewise; provenance asserted; 1e-9 cross-check; specification written.
- [ ] Verdict stated with no more strength than the gates support.

## Review log

- **Draft 1**, 2026-09-15. Written after NB33 and the coverage check of the same day.
- **Codex CLI review** (`gpt-6-astra`, medium), 2026-09-15: "makes sense as exploratory research,
  but its claim to be 'the one lead, gated properly' is premature." Two blocking: gate 3's
  trailing 180-row concentration indicator is not repaired by restricting decision dates, and a
  common fee error does not cancel across configurations with different turnover. Seven
  material: the count is exploratory and the windows overlap; the rule changes are
  evidence-informed revisions, not non-adaptive; "unbiased" is conditional; the median margin
  relaxes the policy and needs economic justification; the null destroys persistence too and
  ten seeds is p = 0.09; H1 contradicted the guard's definition; several protocol gaps.
- **Draft 2**, 2026-09-16. All applied: the count frozen as exploratory; rule changes reframed
  and old verdicts preserved; the variance claim made conditional; gate 3 scored on its
  volatility leg with concentration as diagnostic (amendment 4); the return margin halved to
  -0.005, named, economically justified, with a catastrophic-loss diagnostic; gate 8's
  tolerance set operationally at 5.95; nineteen null seeds with turnover reported; the fee
  differential made a SHORTLIST condition (amendment 6); H1 corrected; the tail contrast at the
  actual exclusion; `measured_8` given its own null and mask runs; the oracle dropped as
  unnecessary; the monitoring protocol given decision criteria; the rejection language
  narrowed. Also corrected: NB33's finding 4 said both combination components beat the anchor
  on its window; `floor15` did not.
