## Review outcome

The **REJECT verdict is correct**. `drop_30` and `drop_35` genuinely pass constraints 1–6 and the late-period check, but neither has two qualifying neighbours; no leave-one-vault-out run was therefore eligible to run, and the fail-closed adoption logic rejects all centres.

The principal concern is reproducibility: the displayed bootstrap output cannot be produced by the displayed code.

## Actual errors

- **Blocking — cells 18 and 36:** `bootstrap_margin_table()` cannot produce the shown output.

  `reference_label = ...idxmax()` returns a label string such as `"drop_30"`. The next line accesses `reference_label.name`, which raises `AttributeError`. Yet cell 36 shows successful output.

  This means either the executed code differs from the supplied cell 18, or the displayed output is not from this notebook version. The bootstrap claims citing cell 36 are not auditable until this discrepancy is resolved.

  Fix:

  ```python
  reference_label = family.loc[
      family["cycle_vol"] <= float(entry["panel"]["cycle_vol"]),
      "cycle_sharpe",
  ].idxmax() if len(family[family["cycle_vol"] <= float(entry["panel"]["cycle_vol"])]) else None

  name = str(reference_label) if reference_label is not None else str(family["cycle_vol"].idxmin())
  ```

- **Material — cells 18 and 36:** the bootstrap’s reported “observed Sharpe difference” is not the same statistic as the notebook’s cycle-Sharpe difference.

  `panel()` uses the usual sample standard deviation (`ddof=1`, via pandas/the key-metric helper), while `bootstrap_paired_sharpe_diff()` uses NumPy’s population standard deviation (`ddof=0`). This explains the discrepancy exactly:

  - table metrics: `2.747391 - 2.159792 = +0.587599`;
  - bootstrap output: `+0.589964`.

  The same issue gives `drop_35` `+0.141880` rather than its displayed-metric difference of `+0.141312`. The boundary conclusions do not change here, but the reported point estimates and bootstrap intervals are on a slightly different scale from adoption constraint 2.

  Fix both observed and resampled calculations to use `ddof=1`, ideally using the same Sharpe helper as `panel()`.

  ```python
  c_std, x_std = sample[:, 0].std(ddof=1), sample[:, 1].std(ddof=1)
  ```

  Also calculate `observed` with the same convention.

- **Minor — cell 35:** “seed and draw count printed by the harness” is false for the displayed result.

  The result dict contains `seed` and `draws`, but cell 36 discards both. Neither is printed in the output table.

  Fix: include `"draws": result["draws"]` and `"seed": result["seed"]` in each output row, or replace the sentence with “configured in the harness”.

- **Minor — cells 0 and 41:** the plateau markdown table does not give the complete failure set for each neighbouring run it names.

  For example, centre 30 says only “lower neighbour `drop_25` fails”, although `drop_25` fails the ulcer condition and the late-period check. The full family table elsewhere is correct, but this table’s binding-constraint strings are abbreviated despite the standing reporting rule.

  Fix `binding_constraints` to include the neighbour’s full constraint failure string and late status, e.g. `lower neighbour drop_25 fails: ulcer (not material); late period`.

## Correct claims that need tighter wording

- **Material wording issue — cell 0:** “`drop_5` is bit-identical to the anchor” is not established by the cited evidence.

  Cells 25 and 42 show equal panel metrics, including CAGR and Sharpe, but they do not compare full equity series, return series, trades, or selected baskets bit-for-bit. The assertion that its removals “never come near the traded top six” is also not supported by `VOL_DROP_LOG`, which records candidates and removals but not final selections.

  Replacement:

  > `drop_5` matches the anchor on every reported panel metric. Its five removed candidates per cycle appear not to alter the realised backtest outcome, but this notebook does not assert bit-identical trades or selected baskets.

- **Minor wording issue — cells 24 and 35:** a family member is not necessarily compared against itself in the observed-control calculation.

  Each row is included in its own eligible comparator set, so `control_ref >= cycle_sharpe` and constraint 7 is indeed impossible to pass. But a higher-Sharpe, no-noisier member may be the actual comparator. For the two displayed bootstrap rows it happens to be self-comparison; the general prose is too broad.

  Replacement:

  > Each family member is included in its own comparator set, so the reference is at least its own Sharpe and the +0.10 requirement is impossible. For `drop_30` and `drop_35`, the selected observed-control comparator is the row itself.

- **Minor wording issue — cell 0:** “same snapshot as the previous plan” overclaims what cell 23 establishes. Reproducing four aggregate figures is strong behavioural parity, but not proof that every input file is byte-identical.

  Replacement:

  > The checked previous-plan reference outputs reproduce within tolerance despite the archive re-download.

- **Minor wording issue — cells 0 and 21:** “drop the N highest-volatility candidates” is not literally the implemented rule.

  The code drops the lowest `inverse_vol` values and encodes unavailable volatility estimates as `0.0`. The notebook later explains this correctly, but the opening definition should not imply a pure measured-volatility screen.

  Replacement:

  > Drop the N lowest-`inverse_vol` candidates before ranking, with unavailable volatility estimates encoded as 0.0.

## Checks that passed

- **Central arithmetic and plateau:** correct. For `drop_30`, CAGR, Sharpe, volatility, ulcer, beta and invested fraction all satisfy constraints 1–6; its failure is solely its `drop_25` neighbour plus the consequently absent robustness run. `drop_35` likewise passes 1–6 but fails through `drop_40`.

- **Complete failure strings in the main family table:** correct. The failed sets match the printed full-precision metrics, including all three failures for `drop_40` and `drop_55`.

- **Constraint 7 treatment:** sound and consistently skipped for the actual adoption flags. The table’s `control_ref` is informational, the bootstrap’s observed-control rows are explicitly described as inapplicable, and the notebook acknowledges the asymmetry relative to NB22/NB23.

- **Drop-composition arithmetic:** correct. At N=30, `21.261905 / 30 = 70.873%`; 49,140 total removals and 928 unmatched-age removals are also correct. The notebook keeps missing volatility, zero/unscored signal, and age distinct, and explicitly preserves the unknown-age bucket.

- **No-drop accounting and schedule:** correct. `SCHEDULE` is independently taken from the anchor equity-clock index, not reconstructed from drop logs. All 126 dates are logged at every N, no logged date is off-schedule, and the minimum pool size of 92 exceeds every tested N.

- **Jaccard:** correctly computed as descriptive only and not used in eligibility, adoption, or stopping logic.

- **Leave-one-vault-out:** correctly fails closed in the plateau table, blocking table, and manifest when unexecuted.

- **Clock and pairing:** volatility, Sharpe and beta are computed on cycle returns, not zero-filled daily data. The bootstrap uses common aligned block indices, as required.

## Open questions

- Whether the rendered cell-36 output came from a code version other than the supplied cell 18.
- Whether `drop_5` is genuinely bit-identical at the trade and equity-series level; the available evidence supports equal reported metrics, not that stronger statement.
---

# Verification of the review, and what was applied

Every finding above was checked against `_build/build_21.py`, `_build/harness_stability.py`,
`_build/cell14_enhanced.py` and the executed notebook's own output before anything was changed.
Verdicts and actions follow. Nothing was applied that was not first reproduced.

## 1. BLOCKING, cells 18/36 - `reference_label.name` raises `AttributeError`: **REJECTED**

The review read `family.loc[...idxmax()]` as returning the index label. It does not. `.idxmax()`
returns the label; `family.loc[<label>]` then returns that **row as a Series**, whose `.name`
attribute *is* the label. Reproduced directly:

```
idxmax        -> 'drop_30'  (str)
family.loc[…] -> pandas.core.series.Series
.name         -> 'drop_30'
```

`bootstrap_margin_table()` is correct as written, which is also why cell 36 executed and printed
`against = "observed control drop_30"`. There is no discrepancy between the executed code and the
supplied source, and the associated open question ("did cell 36 come from a different code
version?") is answered: no. No change made.

## 2. MATERIAL, cells 18/36 - ddof mismatch between the bootstrap Sharpe and the panel Sharpe: **CONFIRMED, exactly**

`bootstrap_paired_sharpe_diff()` standardises with NumPy's population standard deviation
(`ndarray.std()`, `ddof = 0`); the panel's `cycle_sharpe` comes from `calculate_sharpe()` ->
quantstats, which uses the sample standard deviation (`ddof = 1`, verified directly against
`pandas.Series.std(ddof=1)`). On the 125 cycle returns of this window the ratio is a constant
`sqrt(125/124) = 1.0040242`, and it reproduces both reported gaps to seven digits:

| run | panel Sharpe difference (cell 25) | bootstrap observed (cell 36) | ratio |
|---|---|---|---|
| `drop_30` | +0.5875992681 | +0.589964 | 1.0040244 |
| `drop_35` | +0.1413116313 | +0.141880 | 1.0040221 |

Not applied as a code change, for two reasons, both recorded in the notebook rather than acted on:
`bootstrap_paired_sharpe_diff()` lives in `harness_stability.py`, which NB20-NB24 all share, so
changing it desynchronises four executed notebooks for a 0.4% rescaling; and no conclusion moves
(+0.590 and +0.588 both clear -0.10; -0.619 and -0.617 both fail it). Written up in full in
"Robustness of results", with the exact numbers, and flagged as a track-level fix.

## 3. MINOR, cell 35 - "seed and draw count printed by the harness" is false: **CONFIRMED**

`bootstrap_margin_table()` builds rows of `run / against / block / boundary / observed_diff /
ci_lo / ci_hi / clears_boundary`. `seed` and `draws` are present in the result dict and discarded.
Fixed in the cell 35 markdown (and in `build_21.py`, identically): the sentence now states that
the seed (0) and draw count (1000) are fixed in `harness_stability.py` and are **not** columns of
the table.

## 4. MINOR, cells 0/41 - the plateau table abbreviates each named neighbour's failure set: **PARTIAL**

Accurate as an observation about `binding_constraints`, which names a failing neighbour without
repeating that neighbour's failures. But the complete failure set for every run is printed in
cell 25, in each neighbour's own row of the blocking table, and in the heading's own family table,
so this is not the track's historic under-reporting error. Changing `binding_constraints` would
change `_build/manifest_21.json`, which NB24 cross-checks, forcing an NB24 re-run for a
presentational gain. Fixed in the heading instead: the plateau table now carries every named
neighbour's COMPLETE failure set in brackets, sourced from cell 25, with a note saying so.

## 5. MATERIAL wording, cell 0 - "`drop_5` is bit-identical to the anchor": **CONFIRMED**

The notebook shows eight panel metrics agreeing with the anchor at full float precision
(0.37897081230942264 / 2.1597920746960435 and six more), which is strong but is not a comparison
of trades, equity series or selected baskets, and `vol_drop_log` records removals rather than
final selections. Heading reworded: it now states what is shown (metric identity at 17 significant
digits, against `drop_10` which already differs in the 5th decimal), separates that from the
inference about the traded top six, and says the notebook does not assert bit-identical trades.

## 6. MINOR wording, cells 24/35 - "self-comparison by construction": **CONFIRMED for cell 24, not for cell 35**

Cell 24's phrasing is loose: `drop_25`'s `control_ref` is 2.747391, i.e. `drop_30`'s Sharpe, not
its own. What is true by construction is that each member is in its own at-or-below volatility
set, so `control_ref >= cycle_sharpe` on every family row and the +0.10 margin is unreachable
either way. Cell 35's version is accurate for the two runs it prints, where the comparator really
is the run itself (`against = "observed control drop_30"` / `"drop_35"`). Cell 24 rewritten to the
precise statement; cell 35 narrowed to "for both runs printed below"; the heading's constraint-7
bullet and Robustness bullet given the same treatment, including the note that the anchor's row is
an ordinary comparison rather than a construction, since the anchor is not a family member.

## 7. MINOR wording, cell 0 - "same snapshot as the previous plan": **CONFIRMED**

Four reproduced figures are behavioural parity, not byte-identity, and cell 20's own provenance
table shows `vault-prices.parquet` was re-downloaded on 2026-09-13. No previous-plan hash was
recorded to compare against. Heading reworded to claim only what cell 23 establishes.

## 8. MINOR wording, cell 0 - "drop the N highest-volatility candidates": **CONFIRMED**

`cell14_enhanced.py` sorts ascending on `inv_vol_by_id.get(pair_id, 0.0)` and drops the first N, so
it drops the N lowest `inverse_vol`, and a missing estimate is stored as `0.0` and sorts first. The
heading corrected this two bullets later but stated it loosely up front; a paragraph now makes the
implementation explicit immediately after the opening description. Cell 37's use of the phrase is
a chart-axis description and was left alone.

## Found during verification, not in the review

- **Two `late_ok` flags near the anchor are float noise.** `drop_10` passes the late-period gate by
  1.21e-6 (late ulcer 0.025266523 against the anchor's 0.025267733, a 0.005% margin) and `drop_20`
  fails it by 1.20e-4. Neither changes a verdict - both already fail constraints 1-6 - and the two
  runs that matter are not marginal (`drop_30` passes by 8.1e-3, `drop_35` by 9.8e-3). Recorded in
  "Robustness of results" so the flag is not read as informative for the near-anchor members.

## Independently re-checked and found correct

- `drop_30`'s empty failure set, against all six constraints individually: CAGR 0.489942 >= 0.20;
  Sharpe 2.747391 >= 2.059792; vol 0.149229 <= 0.154278; ulcer 0.013843 <= 0.015269; beta 0.001055
  < 0.045797; invested 0.971914 >= 0.90. Late period: 0.661276 > 0 and 0.017173 < 0.025268. Real.
- `drop_35` likewise, and `drop_25`'s two failures (ulcer 0.018202 > 0.015269; late ulcer 0.027333
  > 0.025268, with late CAGR positive).
- The plateau rule matches the plan's pre-registration exactly, `centre_ok_of()` returns False for
  an absent run, and absent-is-fail holds in the plateau table, the blocking table and the manifest
  (`masked_runs: []`, `qualifying_centres: []`, `eligible_centres: []`).
- Drop composition: 21.261905/30 = 70.87%; total removals 126 x (5+10+...+60) = 49,140, matching the
  cross-tab; the six joint cells sum to 49,140; 928 unmatched = 1.89%. The three axes are
  constructed from three independent fields and never conflated.
- `inverse_vol` really does need 90 observations: the indicator's own default is 60, but
  `Parameters.inverse_vol_window = 90` overrides it, and `min_periods = lb` makes it a hard floor.
- `SCHEDULE` is derived from `anchor_equity.index`, independently of any drop log; all 126 logged
  dates lie on it at every N (asserted in cell 32), and the minimum pre-drop pool of 92 exceeds
  every tested N, so "never fired" is a real finding and not a log compared against itself.
- Jaccard appears only in its own descriptive cell and in the heading, and gates nothing.
- Cell 36's `clears_boundary` is `ci_lo > boundary` for every row, so "clears" means the same test
  for `drop_30` and `drop_35`; the bootstrap pairs both series on common block indices drawn once
  per draw.

## Outcome

No code cell changed, no number moved, so the notebook was **not** re-run. Anchor parity
(all ten `BASELINE` metrics within 4.0e-7) and the three reference values - `drop_30`
0.489942 / 2.747391, `drop_50` 0.206149 / 2.014857, `drop_60` 0.116576 / 1.472421 - stand as
executed. `_build/manifest_21.json` is byte-unchanged, so NB24 does not need re-running.
The verdict remains REJECT.
