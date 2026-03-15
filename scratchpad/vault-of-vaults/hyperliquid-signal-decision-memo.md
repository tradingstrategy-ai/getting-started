# Hyperliquid Vault Signals: Decision Memo and Test Matrix

Date: 2026-03-14

## 1. Objective

We want a portfolio weighting signal for Hyperliquid vaults that is balanced rather than max-CAGR chasing.

The signal must:

- handle short and unequal track records
- avoid young-vault spikes and unstable rebalances
- preserve enough cross-sectional dispersion for weights to matter
- control concentration risk without relying on accidental cash drag
- allow `age` and `TVL` as credibility and investability inputs, not as raw alpha

This memo is based primarily on the opening markdown/comment sections of notebooks `48` through `65`, with notebook-to-notebook links used when a later notebook summarizes an earlier result.

## 2. What We Learned From NB48-NB65

### Ratio fixes: NB48-NB50

| Cluster | Hypothesis | What changed | What improved | What broke | Verdict |
| --- | --- | --- | --- | --- | --- |
| NB48 alternative ratios | Replace max drawdown with smoother downside denominators | UPI, pain, CDaR, exp-decay Calmar, log compression, weak Bayesian shrinkage | UPI, pain, and exp-decay smoothed established vaults and reduced rolling-window cliff effects | Young vaults still exploded because all return/drawdown ratios fail when drawdown is near zero; CDaR was worse than raw; weak shrinkage did not help | Good diagnosis, but not a real solution |
| NB49 small-denominator fixes | Attack the true root cause directly | Sterling floor, log-Sterling, confidence weighting, rank, James-Stein | `log_sterling` bounded ratio blow-ups better; `confidence_weighted` produced the smoothest ramp-up; rank was safest | James-Stein failed because the whole cross-section was already inflated; conservative fixes gave up a lot of upside | Real local improvement, but still ratio-centric |
| NB50 consolidated review | Compare all Calmar transforms in one place | Brought 14 transforms together | Clarified the trade-off between aggressiveness and robustness | Confirmed that no Calmar variant fully solved the structural form problem | Useful synthesis notebook |

Key takeaway:

- The main problem was never just max-drawdown discontinuity.
- The dominant problem was ratio-form instability under tiny denominators.
- `log_sterling` and `confidence_weighted` were the best local patches, but they did not fully escape the structural weakness of return/drawdown ratios.

### Non-ratio signals and robust experiments: NB51-NB53

| Cluster | Hypothesis | What changed | What improved | What broke | Verdict |
| --- | --- | --- | --- | --- | --- |
| NB51 non-ratio signals | Move away from return/drawdown ratios entirely | Equity-curve `R^2`, PSR, percentile-rank composites, multiplicative composite | Bounded signals avoided denominator blow-ups by construction | Composite construction risk remained high; no clear production winner emerged from the intro notes alone | Important conceptual pivot |
| NB52 robust signal experiments | Use regularization, shrinkage, and confidence-aware estimation | elastic Calmar, Bayesian credibility, EWM RMS DD, bootstrap confidence, inverse variance, PSR | Bayesian credibility and PSR introduced a better language for unequal data lengths | Several variants were still built on Calmar/Stirling foundations, so the core fragility was only softened, not removed | Best bridge toward a better design |
| NB53 PSR allocation | Use PSR directly for concentration control | PSR floor and multiplier sweep | PSR naturally penalized small samples and heavy tails | It addressed sizing more than ranking; it was not yet a full signal solution | Promising control layer, not a full portfolio signal |

Key takeaway:

- NB51 was the first clean break from the ratio family.
- NB52 introduced the most important idea in the whole series: treat short histories as an estimation problem and shrink noisy vaults toward a prior.
- PSR was more useful as a confidence-aware statistic than as a second layer stacked on top of an already-shrunk signal.

### PSR concentration and window search: NB54-NB57

| Cluster | Hypothesis | What changed | What improved | What broke | Verdict |
| --- | --- | --- | --- | --- | --- |
| NB54 PSR-based concentration | Replace manual vault quality tiers with PSR-based concentration caps | `max_concentration = min(PSR * multiplier, 1)` with floor | Raw and log looked best once PSR capped extremes | This likely made earlier ratio fixes look redundant because PSR was already doing part of the regularization work | Mixed: good sizing idea, confounded signal comparison |
| NB55 PSR window search | Tune PSR lookback separately | Added `psr_window` search | Longer PSR windows looked better in averages | Best pick was unchanged from NB54; sampling was uneven | Weak evidence |
| NB56 long-window diagnosis | Check if long windows were real or artifact | Expanded windows and inspected the optimizer behavior | Identified that `volatility_window >= 240` exceeded the backtest and turned the signal into an expanding-window fit | Backtest performance was inflated by lookbacks longer than available history; one searched parameter was inert | One of the most important notebooks |
| NB57 short-window search | Restrict windows to feasible values | Capped windows at 180, removed inert param, locked waterfall off | Restored realism by forcing the indicator to actually roll | Lower reported metrics showed how much earlier results were overstated | Strong methodological correction |

Key takeaway:

- NB56/57 changed the interpretation of most earlier performance numbers.
- Any result built on windows longer than the available history is not reliable evidence.
- This is the clearest artifact in the full notebook chain.

### Adaptive and Bayesian signals: NB58-NB61

| Cluster | Hypothesis | What changed | What improved | What broke | Verdict |
| --- | --- | --- | --- | --- | --- |
| NB58 adaptive signal comparison | Compare signals designed for unequal track lengths | raw, elastic Calmar, Bayesian credibility, EWM RMS DD | Later notebooks report Bayesian credibility clearly beat the others | Still partly inherited the ratio stack through log-Sterling | Most useful signal-comparison stage |
| NB59 linear PSR allocation | Replace hard PSR floors with smooth linear mapping | Linear PSR concentration above a floor | Bayesian credibility became the clear leader in the search summary; metrics became more realistic | PSR was still another certainty layer on top of a certainty-aware signal | Good refinement, but likely redundant |
| NB60 Bayesian credibility deep search | Focus only on Bayesian credibility and tune its constants | Search over Bayesian halflife and windows, plus robustness analysis | Strengthened the case that Bayesian credibility was the best family so far | Signal still inherited several nonlinear compressions before weights saw it | Strong local winner |
| NB61 Bayesian credibility without PSR | Remove PSR caps entirely | Fixed concentration cap, no PSR | Similar Calmar to NB60 with much higher CAGR and slightly worse drawdown; supported the "double-penalization" diagnosis | Concentration risk remained a concern; profits clustered in a few vaults | Very important portfolio-level result |

Key takeaway:

- Bayesian credibility is the best idea that survived the notebook gauntlet.
- Removing PSR after already shrinking by data length improved the portfolio result materially.
- That strongly suggests PSR and Bayesian shrinkage were overlapping penalties rather than complementary ones.

### Weighting experiments: NB62-NB64

| Cluster | Hypothesis | What changed | What improved | What broke | Verdict |
| --- | --- | --- | --- | --- | --- |
| NB62 cash deployment | Deploy more idle cash without hurting risk | Compared equal, passthrough, and log weights | Slightly higher allocation improved a little | Signal-proportional weights increased drawdowns sharply; equal-weight's geometric decay acted as a risk buffer | Important allocator insight |
| NB63 softmax and blended allocation | Find a smooth middle ground between equal and passthrough | Softmax and equal/proportional blends | Mild softmax and high-equal blends were less bad than passthrough | Every step toward stronger signal-responsiveness worsened drawdown more than it helped returns | No sweet spot found |
| NB64 threshold-linear allocation | Cut weak vaults while weighting stronger vaults proportionally | Threshold plus linear weighting above threshold | None | Same monotonic deterioration pattern; even mild thresholding hurt badly | Strong evidence against aggressive weight tilts with the current signal |

Key takeaway:

- Equal-weighting was not winning because equal weights are universally best.
- It was winning because the current signal was too noisy or too compressed to justify concentration.
- More weight responsiveness magnified noise faster than it captured true information.

### Signal-quality diagnosis: NB65

| Cluster | Hypothesis | What changed | What improved | What broke | Verdict |
| --- | --- | --- | --- | --- | --- |
| NB65 signal quality analysis | The weights are not the core problem; the signal is over-processed | Planned direct comparison of simple vs complex signals across multiple weight maps | Clear diagnosis of likely cause: max drawdown, Sterling floor, `log1p`, and Bayesian shrinkage each reduce dispersion | Notebook findings section was still empty, so the diagnosis is a hypothesis, not a completed result | Correct next question, unfinished evidence |

Key takeaway:

- NB65 asks the right next question.
- The most plausible explanation for NB62-NB64 is signal over-compression, not a mysterious superiority of equal weight.

## 3. Failure Modes

### 3.1 Small-denominator drawdown explosion

All return/drawdown ratios become unstable when young or lucky vaults have positive returns and almost no drawdown. NB48 and NB49 identified this correctly. Smoother downside measures helped established vaults but did not solve this.

### 3.2 Young-vault overreaction

Very short histories were treated as if they were equally informative as mature vaults. Confidence weighting and Bayesian credibility helped, but the series repeatedly showed that young-vault handling must be built into the estimation logic, not patched on afterward.

### 3.3 Windows longer than available history

NB56 showed that several "best" results were effectively whole-sample fits because the lookback never truly rolled. This is the biggest backtest artifact in the notebook chain.

### 3.4 Double-penalization of uncertainty

Bayesian credibility already shrinks young vaults toward a prior. Adding PSR-based caps on top often penalized the same uncertainty twice. NB61 is the clearest evidence for this.

### 3.5 Signal over-compression

By the later notebooks, the signal pipeline stacked:

1. downside-risk denominator
2. floor constant
3. logarithmic compression
4. cross-sectional shrinkage

That likely collapsed useful cross-sectional dispersion. Signal-responsive weights then behaved like noisy versions of equal weight.

### 3.6 Weighting noise amplification

NB62-NB64 showed that when the signal is weak, proportional, softmax, and threshold-linear weights mostly amplify estimation error. Equal weighting won because it was more robust to signal error, not because it extracted more information.

## 4. Recommended New Approaches

These are the next candidates worth testing. They are deliberately fewer and cleaner than the notebook search space so we can learn faster.

### A. Hierarchical skill score

Default production candidate.

- **Signal definition**
  - Estimate each vault's latent expected return or risk-adjusted return with partial pooling across vaults.
  - Use posterior mean and posterior uncertainty to form a conservative score such as:
    - posterior lower credible bound, or
    - posterior mean minus uncertainty penalty
- **Where age enters**
  - `age` or days of live history controls shrinkage strength
  - young vaults stay closer to the cross-sectional prior
  - mature vaults earn more idiosyncratic signal
- **Where TVL enters**
  - TVL does not increase score directly
  - TVL affects a soft investability penalty or a max-cap rule
- **Weight mapping**
  - rank vaults by score
  - equal weight across top `k`, or a mild capped linear tilt
  - no aggressive passthrough
- **Expected strengths**
  - directly addresses unequal history length
  - avoids drawdown denominator pathologies
  - interpretable and consistent with the best notebook insight from Bayesian credibility
- **Expected failure mode**
  - if the prior is too strong, winners may be under-recognized
  - if the prior is too weak, young-vault noise returns

Rationale from literature:

- Jones and Shanken show that learning across funds shrinks extreme alpha estimates toward an aggregate belief and avoids unrealistic posterior extremes when many noisy histories are compared ([NBER 9392](https://www.nber.org/papers/w9392)).
- Efron and Morris provide the classical empirical-Bayes foundation for shrinking noisy estimates toward a shared prior ([Biometrika](https://academic.oup.com/biomet/article-abstract/59/2/335/325580)).

### B. Metadata-assisted rank composite

Conservative backup candidate.

- **Signal definition**
  - Cross-sectional percentile rank composite over:
    - rolling return
    - downside deviation or drawdown duration
    - signal stability or bootstrap reliability
    - age percentile
    - TVL percentile
- **Where age enters**
  - age rank rewards vaults with more evidence
  - can also serve as a minimum eligibility gate
- **Where TVL enters**
  - TVL rank gives a mild investability preference
  - can also trigger soft caps for very small vaults
- **Weight mapping**
  - equal weight over top quantile or top `k`
  - optional small tilt within the selected set
- **Expected strengths**
  - bounded and robust
  - avoids denominator blow-ups
  - easy to maintain and explain
- **Expected failure mode**
  - loses cardinal information
  - may lag when a truly strong new vault emerges

Rationale from literature:

- The notebook series already found rank-like methods to be safer under noisy signals.
- Kaniel, Lin, Pelger, and Van Nieuwerburgh show that fund characteristics can help differentiate future performance, which supports using metadata as auxiliary predictors or ranking inputs rather than pure return history alone ([NBER 29723](https://www.nber.org/papers/w29723)).

### C. PSR-with-gates

Clean alternative to the current PSR usage.

- **Signal definition**
  - Use PSR or a lower-confidence Sharpe-style statistic as the primary score
  - do not stack another credibility transform on top
- **Where age enters**
  - age can be a minimum eligibility threshold
  - age can also determine whether PSR is computed at all or replaced with a prior score
- **Where TVL enters**
  - TVL acts as a gate or cap modifier
  - low TVL reduces capacity, not alpha
- **Weight mapping**
  - top-set equal weight, or mild capped tilt by PSR
- **Expected strengths**
  - directly uncertainty-aware
  - better aligned with short-track-record inference than raw Sharpe or Calmar
- **Expected failure mode**
  - still noisy with very short or nonstationary data
  - can become redundant again if too many extra gates are layered in

Rationale from literature:

- Bailey and Lopez de Prado explicitly motivate PSR as an uncertainty-adjusted skill statistic that depends on track-record length and higher moments, not just point-estimate Sharpe ([Journal of Risk summary](https://www.risk.net/journal-of-risk/technical-paper/2223785/the-sharpe-ratio-efficient-frontier), [Bailey site PDF mirror](https://www.davidhbailey.com/dhbpapers/sharpe-frontier.pdf)).

### D. Online expert weighting

Exploratory research candidate.

- **Signal definition**
  - Treat vaults as experts
  - update weights sequentially from realized returns using exponential-weights style learning
- **Where age enters**
  - new vaults start with low trust or a probation cap
- **Where TVL enters**
  - TVL directly limits concentration and possibly selection
- **Weight mapping**
  - the learner produces raw weights
  - wrap them with hard concentration caps and minimum diversification rules
- **Expected strengths**
  - adaptive to regime change
  - avoids hard-coded ratio engineering
- **Expected failure mode**
  - can chase noise without strong caps
  - less interpretable than the first three approaches

Rationale from literature:

- Cesa-Bianchi and Lugosi's expert-advice framework is the right conceptual base when the problem is sequentially allocating among a changing set of managers without assuming a stable data-generating process ([Prediction, Learning, and Games](https://cesa-bianchi.di.unimi.it/predbook/)).

## 5. Testing Protocol

Every candidate should go through one common test harness. No candidate gets its own custom optimizer story.

### 5.1 Universe rules

Hold fixed across all tests:

- same Hyperliquid vault universe construction
- same quarantine periods
- same rebalance schedule
- same transaction assumptions
- same per-vault concentration rules
- same treatment of unavailable or not-yet-live vaults

### 5.2 Train/test structure

Use walk-forward or rolling-origin evaluation instead of a single full-period search.

Recommended structure:

- split the sample into sequential train/test slices
- fit or tune on the train slice only
- evaluate on the next holdout slice
- roll forward and repeat

Hard rule:

- no effective lookback may exceed the amount of data available inside the relevant training slice

This is the direct methodological fix for the NB56 artifact.

### 5.3 Parameter policy

Keep the search intentionally small.

- use small discrete grids only
- prefer theory-driven defaults over broad optimizer sweeps
- tune only a few high-value parameters
- report untuned baseline results next to tuned ones

Suggested parameter limits:

- one core lookback family
- one or two shrinkage-strength settings
- one or two top-`k` or percentile-selection settings
- one mild-tilt setting plus equal-weight baseline

### 5.4 Metrics

Primary metrics:

- CAGR
- max drawdown
- Sharpe
- Calmar

Portfolio-construction diagnostics:

- turnover / rebalance churn
- average and maximum concentration
- capital utilization
- contribution of top 3 vaults to total PnL

Signal diagnostics:

- cross-sectional dispersion of the score
- rank stability through time
- entry speed for new vaults
- realized position share of young vaults

### 5.5 Young-vault checks

Each candidate must answer:

- how quickly can a new vault enter the portfolio?
- can a 2- to 4-week winning streak create an outsized weight?
- is the maturity effect smooth or cliff-like?
- does the method still allow genuinely strong young vaults to graduate over time?

### 5.6 TVL checks

Each candidate must answer:

- are very small vaults filtered or softly capped?
- does TVL improve capacity control?
- does TVL accidentally dominate the ranking and just favor incumbents?

### 5.7 Weight-map policy

Every candidate should be compared under the same three mapping rules:

1. equal weight over selected vaults
2. mild capped linear tilt
3. high-temperature softmax

Do not test low-temperature softmax or fully proportional passthrough unless the signal first proves that it has materially more dispersion and stability than the current pipeline.

### 5.8 Baselines

Keep these baselines in every report:

- current equal-weight Bayesian credibility baseline
- naive equal weight across eligible vaults
- one conservative rank-based baseline

## 6. Recommendation

### Default production candidate

**Hierarchical skill score with age-aware shrinkage and TVL-aware caps**

Why:

- it keeps the best insight from NB52-NB61
- it removes the Calmar/Sterling dependency
- it directly addresses unequal history length
- it should preserve more usable dispersion than the current over-compressed stack

Recommended initial implementation shape:

- score = posterior mean of expected return or downside-adjusted return minus uncertainty penalty
- select top `k` or top quantile
- equal weight within selection at first
- apply TVL-based max-cap overlay

### Conservative backup

**Metadata-assisted rank composite**

Why:

- simplest robust design
- bounded by construction
- easiest to explain and maintain
- least likely to recreate young-vault blow-ups

### Exploratory research candidate

**Online expert weighting with hard metadata caps**

Why:

- best path if the underlying environment is highly nonstationary
- most adaptive candidate
- worth testing only after the first two are established

## 7. Acceptance Criteria

A candidate is promising only if it satisfies most of the following:

- matches or beats the current equal-weight Bayesian baseline on risk-adjusted return
- does not rely on infeasible windows or whole-sample effects
- keeps concentration and drawdown under control without depending on accidental idle cash
- produces enough cross-sectional dispersion that weights are informed by signal rather than noise
- handles young vaults smoothly
- remains interpretable enough to maintain

## 8. Recommended First Test Matrix

Start with a narrow matrix instead of another broad search.

| Candidate | Core variants | Selection rule | Weight rules | Metadata use |
| --- | --- | --- | --- | --- |
| Hierarchical skill score | 2 shrinkage settings x 2 return definitions | top `k`, top quantile | equal, mild tilt | age in shrinkage, TVL in cap |
| Metadata-assisted rank composite | 2 feature sets x 2 stability terms | top `k`, top quantile | equal, mild tilt | age and TVL as ranks and gates |
| PSR-with-gates | 2 lookbacks x 2 gate settings | top `k`, top quantile | equal, mild tilt | age and TVL as eligibility/cap |

That is enough to learn whether the next iteration should be:

- more Bayesian
- more ordinal
- or more adaptive

without repeating the optimizer sprawl from the current notebook chain.

## 9. Concrete Experiments To Run Next Using The NB65 Framework

These are concrete follow-up experiments that can be implemented inside the existing `65` template:

- keep the same `Parameters` class and optimizer flow
- keep the same `decide_trades()` structure
- add new `signal_variant`, `gate_variant`, or `weight_function` categories
- add new indicators in the same `IndicatorRegistry`
- reuse the same portfolio analytics, trade summary, equity curves, heatmaps, feature importance, and chart rendering sections

Do not create new notebooks from this memo yet. The point is to define what the next notebooks should test in a way that fits the existing harness.

### Experiment 1: Dual-signal gate plus weight

This is the most direct extension of NB65's conclusion.

Hypothesis:

- Bayesian Sterling is best at deciding which vaults deserve inclusion.
- Simpler signals such as rolling Sharpe are better at deciding how much to allocate once the universe has already been filtered.

Implementation shape:

- Add a new `gate_signal_variant` parameter alongside `weight_signal_variant`
- Gate first, weight second
- Only vaults passing the gate are sent into the weight assignment step

#### Strategy parameters to search

- `gate_signal_variant`
  - `bayesian_sterling`
  - `raw_sterling`
  - `rolling_sharpe`
- `weight_signal_variant`
  - `rolling_sharpe`
  - `rolling_returns`
  - `raw_sterling`
  - `bayesian_sterling` as the control
- `gate_mode`
  - `positive_only`
  - `top_quantile`
  - `top_k`
- `gate_quantile`
  - `0.3`
  - `0.5`
  - `0.7`
- `gate_top_k`
  - `5`
  - `8`
  - `12`
- `weight_function`
  - `weight_equal`
  - `weight_softmax_2.0`
  - `weight_blend_0.5`
  - `weight_passthrough` only as a stress test
- `volatility_window`
  - `60`
  - `90`
  - `120`
  - `150`
- `bayesian_halflife`
  - `30`
  - `60`
  - `90`
- `sterling_constant`
  - `0.05`
  - `0.10`
  - `0.20`

#### Used indicators

- Existing:
  - `rolling_returns`
  - `rolling_sharpe`
  - `rolling_sterling_floor`
  - `rolling_calmar_transformed`
  - `age`
  - `tvl`
  - `inclusion_criteria`
- New optional helper indicators:
  - `gate_signal_rank`
  - `weight_signal_rank`
  - `gate_pass_mask`
  - `cross_sectional_signal_spread`

#### Used weighting methods

- `weight_equal`
- `weight_softmax_2.0`
- `weight_blend_0.5`
- `weight_passthrough` only to detect whether the gate is strong enough to support aggressive weighting

#### Extra analysis and charts

- Gate vs weight signal scatter plot for selected vaults by rebalance date
- Time series of number of vaults passing the gate
- Cross-sectional signal dispersion before and after the gate
- Rank overlap chart:
  - top gate vaults vs top realized contributors
- Age distribution of gated-in vaults over time
- TVL distribution of gated-in vaults over time
- Top-3 contribution share vs total portfolio PnL
- Heatmap of `gate_signal_variant x weight_signal_variant`
- Position concentration chart:
  - max weight
  - Herfindahl index
  - top-3 combined weight

Success condition:

- improved Sharpe or Calmar over `bayesian_sterling + weight_equal`
- without allowing young or small vaults to dominate immediately

### Experiment 2: Metadata-adjusted simple signal

This experiment tries to keep the ranking quality of simple signals while borrowing only the credibility part of age and TVL, not the full Bayesian compression.

Hypothesis:

- Rolling Sharpe and rolling returns contain more useful ranking dispersion than the Bayesian pipeline.
- Their main weakness is poor selection of young or tiny vaults.
- A lightweight credibility multiplier from `age` and `TVL` can fix selection without destroying dispersion.

Implementation shape:

- Add a new indicator:
  - `metadata_credibility_multiplier`
- Add a new signal family:
  - `credibility_adjusted_signal = base_signal * age_multiplier * tvl_multiplier`
- Use smooth curves rather than hard gates where possible

#### Strategy parameters to search

- `base_signal_variant`
  - `rolling_sharpe`
  - `rolling_returns`
  - `raw_sterling`
- `age_curve_mode`
  - `linear`
  - `sigmoid`
  - `halflife`
- `age_halflife_days`
  - `14`
  - `30`
  - `60`
  - `90`
- `age_min_floor`
  - `0.25`
  - `0.50`
  - `0.75`
- `tvl_curve_mode`
  - `none`
  - `log_scaled`
  - `soft_cap`
- `tvl_soft_cap_usd`
  - `25_000`
  - `50_000`
  - `100_000`
  - `250_000`
- `tvl_exponent`
  - `0.25`
  - `0.50`
  - `1.00`
- `weight_function`
  - `weight_equal`
  - `weight_softmax_2.0`
  - `weight_blend_0.5`
- `volatility_window`
  - `60`
  - `90`
  - `120`
  - `150`

#### Used indicators

- Existing:
  - `rolling_returns`
  - `rolling_sharpe`
  - `rolling_sterling_floor`
  - `age`
  - `tvl`
  - `inclusion_criteria`
- New:
  - `age_multiplier`
  - `tvl_multiplier`
  - `metadata_credibility_multiplier`
  - `credibility_adjusted_signal`

#### Used weighting methods

- `weight_equal` as control
- `weight_softmax_2.0`
- `weight_blend_0.5`

#### Extra analysis and charts

- Decomposition chart per vault:
  - base signal
  - age multiplier
  - TVL multiplier
  - final adjusted score
- Entry-ramp chart for new vaults:
  - days since inception vs final score
- Score vs age scatter
- Score vs TVL scatter
- Portfolio exposure by age bucket
- Portfolio exposure by TVL bucket
- Signal dispersion before and after metadata adjustment
- Realized return contribution by age bucket and TVL bucket
- Stability chart:
  - how often top-ranked vaults change relative to the unadjusted signal

Success condition:

- rolling-Sharpe-like weighting remains stronger than equal weight
- but young-vault blow-ups and low-TVL over-allocation are materially reduced

### Experiment 3: Rank composite with metadata and top-k selection

This experiment leans into the notebook finding that ordinal methods are safer when score magnitudes are noisy.

Hypothesis:

- Relative ordering is more reliable than raw magnitude.
- A rank composite can preserve robustness while still allowing age and TVL to improve selection.

Implementation shape:

- Build one or two composite rank signals
- Use top-`k` or top-quantile selection
- Compare equal weight against only mild tilts

#### Strategy parameters to search

- `rank_feature_set`
  - `returns + sharpe + age + tvl`
  - `returns + sharpe + drawdown + age + tvl`
  - `returns + sterling + drawdown + age + tvl`
- `rank_weight_scheme`
  - `equal_feature_weights`
  - `performance_heavy`
  - `credibility_heavy`
- `selection_mode`
  - `top_k`
  - `top_quantile`
- `selection_k`
  - `5`
  - `8`
  - `12`
- `selection_quantile`
  - `0.2`
  - `0.3`
  - `0.5`
- `weight_function`
  - `weight_equal`
  - `weight_blend_0.5`
  - `weight_softmax_2.0`
- `volatility_window`
  - `60`
  - `90`
  - `120`
  - `150`
- `sterling_constant`
  - `0.05`
  - `0.10`
  - `0.20`

#### Used indicators

- Existing:
  - `rolling_returns`
  - `rolling_sharpe`
  - `rolling_sterling_floor`
  - `drawdown_from_peak`
  - `age`
  - `tvl`
- New:
  - `drawdown_duration`
  - `feature_rank_dataframe`
  - `rank_composite_signal`

#### Used weighting methods

- `weight_equal`
- `weight_blend_0.5`
- `weight_softmax_2.0`

#### Extra analysis and charts

- Feature contribution heatmap to final rank score
- Rank correlation matrix among component features
- Membership stability plot:
  - fraction of vaults staying in top `k` at each rebalance
- Top-k turnover chart
- PnL contribution by final rank decile
- Exposure by age and TVL decile
- Drawdown plot conditioned on number of selected vaults
- Comparison chart of raw composite score spread vs final allocated weights

Success condition:

- lower drawdown and turnover than the aggressive Sharpe-weighted variants
- while matching or beating the Bayesian equal-weight baseline on Calmar

### Experiment 4: Dispersion-aware weighting switch

This is a more structural experiment aimed directly at the NB65 diagnosis.

Hypothesis:

- Signal-responsive weighting should only be used when the cross-sectional signal spread is high enough to justify concentration.
- When dispersion is weak, the strategy should automatically fall back to equal weight.

Implementation shape:

- Compute a dispersion statistic each rebalance
- If dispersion is below threshold:
  - use `weight_equal`
- If dispersion is above threshold:
  - use `weight_softmax_2.0` or `weight_blend_0.5`

#### Strategy parameters to search

- `base_signal_variant`
  - `rolling_sharpe`
  - `raw_sterling`
  - `bayesian_sterling`
- `dispersion_metric`
  - `std`
  - `p90_minus_p10`
  - `top1_minus_median`
- `dispersion_threshold`
  - low
  - medium
  - high
- `responsive_weight_function`
  - `weight_softmax_2.0`
  - `weight_blend_0.5`
- `fallback_weight_function`
  - `weight_equal`
- `volatility_window`
  - `60`
  - `90`
  - `120`
  - `150`

#### Used indicators

- Existing:
  - `rolling_sharpe`
  - `rolling_sterling_floor`
  - `rolling_calmar_transformed`
- New:
  - `cross_sectional_signal_std`
  - `cross_sectional_p90_p10_spread`
  - `weighting_mode_switch`

#### Used weighting methods

- `weight_equal`
- `weight_softmax_2.0`
- `weight_blend_0.5`

#### Extra analysis and charts

- Time series of cross-sectional dispersion
- Weighting-mode switch timeline
- Performance conditioned on high-dispersion vs low-dispersion periods
- Max-weight and concentration plots around switch dates
- Rank-spread vs next-period return scatter
- Event study around large dispersion spikes

Success condition:

- responsive weighting is used only in the periods where it is actually rewarded
- drawdown remains closer to equal-weight behavior in low-dispersion periods

### Recommended order

If starting with only three experiments, run them in this order:

1. dual-signal gate plus weight
2. metadata-adjusted simple signal
3. rank composite with metadata and top-k selection

Experiment 4 is worth doing immediately after if the first three show that weight responsiveness only helps in specific regimes.

## 10. Sources

Notebook evidence:

- `48`-`65` top markdown/comment sections in `scratchpad/vault-of-vaults`

Literature and reference sources:

- Bailey, Lopez de Prado, and del Pozo, "The strategy approval decision: A Sharpe ratio indifference curve approach"  
  https://econpapers.repec.org/article/risiosalg/0026.htm
- Bailey and Lopez de Prado, "The Sharpe Ratio Efficient Frontier"  
  https://www.risk.net/journal-of-risk/technical-paper/2223785/the-sharpe-ratio-efficient-frontier  
  https://www.davidhbailey.com/dhbpapers/sharpe-frontier.pdf
- Jones and Shanken, "Mutual Fund Performance with Learning Across Funds"  
  https://www.nber.org/papers/w9392
- Kaniel, Lin, Pelger, and Van Nieuwerburgh, "Machine-Learning the Skill of Mutual Fund Managers"  
  https://www.nber.org/papers/w29723
- Kacperczyk, Van Nieuwerburgh, and Veldkamp, "Time-Varying Fund Manager Skill"  
  https://www.nber.org/papers/w17615
- Cesa-Bianchi and Lugosi, "Prediction, Learning, and Games"  
  https://cesa-bianchi.di.unimi.it/predbook/
- Efron and Morris, "Empirical Bayes on Vector Observations: An Extension of Stein's Method"  
  https://academic.oup.com/biomet/article-abstract/59/2/335/325580
