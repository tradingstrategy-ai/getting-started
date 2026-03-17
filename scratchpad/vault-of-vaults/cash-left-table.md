# Cash left table

This note summarises the capital deployment bottleneck in [129-hyperliquid-final-age-ramp-backtest.ipynb](/Users/moo/code/getting-started/scratchpad/vault-of-vaults/129-hyperliquid-final-age-ramp-backtest.ipynb) and suggests the next experiments using the notebook history in [README.md](/Users/moo/code/getting-started/scratchpad/vault-of-vaults/README.md) as reference.

## Current deployment snapshot

All figures below come from the final rebalance diagnostic in NB129 on `2026-03-10`.

| Metric | Value | Read |
|---|---:|---|
| Total equity | `165,935.86 USD` | Portfolio value at the end of the run |
| Cash left | `104,785.43 USD` | `63.15%` of total equity stayed in cash |
| Investable equity | `162,617.15 USD` | Capital that wanted deployment after reserves and fees |
| Accepted investable equity | `59,824.37 USD` | Only `36.79%` of investable capital was actually deployed |
| Unaccepted investable equity | `102,792.78 USD` | `63.21%` of investable capital was left undeployed |
| Explicitly rejected for lit liquidity | `3,159.23 USD` | Only `1.94%` of investable capital |
| Structural leftover after liquidity rejection | `99,633.55 USD` | `61.27%` of investable capital was stranded by strategy mechanics |
| Pairs meeting TVL inclusion criteria | `62` | There were enough vaults by raw count |
| Pairs meeting all inclusion criteria | `59` | The live eligible universe was still broad |
| Signals created | `59` | Weighting started from a wide denominator |
| Accepted positions | `15` | Only `15` vaults received non-zero size |
| Signals flagged `individual_trade_size_too_small` | `47` | Main rejection path |
| Signals flagged `capped_by_pool_size` | `4` | Secondary bottleneck only |
| Mean accepted position size | `3,988.29 USD` | Deployed tickets were all roughly `4k USD` |
| Median accepted position size | `4,151.02 USD` | Confirms the strategy settled into small but tradeable clips |
| Max accepted position size | `4,251.99 USD` | Very little size differentiation once mature vaults saturated at `1.0` |

## HLP check

| Metric | Value | Read |
|---|---:|---|
| HLP end position | `4,157.95 USD` | HLP was used |
| HLP share of total equity | `2.51%` | Very small sleeve |
| HLP share of deployed capital | `6.95%` | Normal portfolio member, not a cash sink |
| HLP total PnL | `1,304.58 USD` | Positive contributor, but not large enough to absorb idle cash |

Conclusion: the notebook did deploy to HLP, but only as one ordinary selected vault. It did not act as an overflow or residual-cash sweep vehicle.

## What is actually limiting deployment

| Candidate bottleneck | Evidence in NB129 | Verdict |
|---|---|---|
| Not enough good vaults by count | `59` eligible vaults and `62` passing TVL filter | No |
| TVL caps too tight | Only `4` signals flagged `capped_by_pool_size` | Not the main issue |
| Lit liquidity too weak | Only `3,159.23 USD` explicitly rejected for lit liquidity | Minor issue |
| Weighting denominator too wide | `59` signals created, but only `15` accepted | Yes |
| Minimum trade size clipping the tail | `47` signals flagged `individual_trade_size_too_small` | Yes |
| No strong recycling after drops | `99.6k USD` structural leftover remained after excluding liquidity rejects | Yes |

The practical read is simple: NB129 is not really running out of Hyperliquid vaults. It is spreading age-ramp weight across a broad mature universe, then discarding much of the tail as too small to trade, without reallocating enough of that dropped weight into the survivors.

## Read-through against earlier experiments

| Notebook(s) | Prior finding from README | What it means for NB129 |
|---|---|---|
| `NB08` | Fixing a real idle-cash deployment bug improved results even in a simple strategy | Mechanical deployment fixes are worth testing before inventing new alpha |
| `NB62` to `NB64` | Equal weight consistently beat signal-responsive sizing when cash deployment was the issue | Once the vault set is selected, simple sizing may improve both utilisation and drawdown |
| `NB69` | Idle cash sometimes acted as a natural drawdown buffer; TVL caps were the bottleneck in that branch | Do not target `100%` deployment blindly; some cash is useful |
| `NB72a` | Concentration tiers and HLP absorption had zero effect when the weight function already produced tiny allocations | Fix the weight construction first, not the cap table |
| `NB72b` | Dispersion-aware switching underperformed the always-simple baseline | Avoid adding a complex regime switch unless the current branch shows a much clearer trigger |
| `NB73` | Full HLP cash sweep modes underperformed the baseline and increased drawdown | If HLP is used, keep it residual-only and tightly capped |
| `NB123` | Plain `age_ramp` survived walk-forward and all fancier overlays failed | Keep `age_ramp` as the structural backbone rather than replacing it |
| `NB126` and `NB127` | `min_tvl=15k` is robust and both `age_ramp` and `equal_weight` remain production-worthy families | The best next step is likely a deployment hybrid, not a new signal family |
| `NB128` | Equal weight still dominated training in the widened universe; clustering was interesting but not production-ready | Prefer simple deployment fixes before adding correlation machinery |

## Results from the follow-up notebooks

I ran four concrete notebook variants against the NB129 baseline. The broad result is that only one experiment materially improved capital deployment in a real way, and it did so by accepting noticeably more concentration and drawdown.

| Notebook | Hypothesis | CAGR | Sharpe | Max DD | Cash % of equity | Accepted / investable % | What happened |
|---|---|---:|---:|---:|---:|---:|---|
| `NB129` | Baseline final age-ramp | `130.81%` | `3.80` | `-4.95%` | `63.15%` | `36.79%` | Baseline underdeployment: too many small tickets, too little recycling |
| `NB130` | Post-floor re-normalisation / survivor-first sizing | `215.89%` | `3.60` | `-8.09%` | `18.87%` | `82.28%` | The only experiment that genuinely fixed most of the idle-cash problem |
| `NB131` | Age-ramp selection + equal-weight deployment | `88.26%` | `3.81` | `-2.00%` | `74.44%` | `25.39%` | Very defensive, but cash efficiency got worse rather than better |
| `NB132` | Dynamic deployable-set sizing | `130.81%` | `3.80` | `-4.95%` | `63.15%` | `36.79%` | Essentially identical to baseline; the pre-pruning rule did not move the result |
| `NB133` | Capped residual HLP sleeve | `130.81%` | `3.80` | `-4.95%` | `63.15%` | `44.41%` | Accepted-investable bookkeeping improved, but realised cash and realised performance stayed unchanged |

## What we learnt from each experiment

### NB130 - post-floor re-normalisation

- This was the clear winner on deployment.
- Accepted investable equity rose from about `36.8%` of investable capital in NB129 to about `82.3%`.
- Cash fell from about `63.2%` of equity to about `18.9%`.
- Mean accepted ticket size rose from about `4.0k USD` to about `10.8k USD`.
- The rejection mix flipped from `47` too-small flags and `4` pool-size caps in NB129 to `4` too-small flags and `8` pool-size caps here.

Interpretation:

- The baseline problem really was denominator dilution.
- Once the strategy selected the final survivors first and then re-normalised across them, most of the fake underdeployment disappeared.
- The next bottleneck was not “not enough vaults”, but actual capacity and concentration.

Trade-off:

- The strategy became much more aggressive.
- CAGR jumped to `215.9%`, but max drawdown worsened to `-8.09%`.
- This is not an obvious drop-in production replacement for NB129 if low drawdown is part of the objective.

### NB131 - age-ramp selection plus equal-weight deployment

- This delivered the lowest drawdown of the whole batch at `-2.00%`.
- Sharpe stayed excellent at `3.81`.
- But cash efficiency got worse, not better: only about `25.4%` of investable capital was deployed and cash rose to about `74.4%` of equity.
- The final cycle still showed `45` `individual_trade_size_too_small` flags and only `1` pool-size cap.

Interpretation:

- Equal weight is not the right answer when the final ticket size is already constrained by a trade-size floor.
- In this branch, equal weighting made each ticket even smaller and stranded more capital.
- So the old README lesson from `NB62` to `NB64` does not transfer mechanically to the NB129 age-ramp setup.

### NB132 - dynamic deployable-set sizing

- This came out effectively identical to NB129 on every relevant number.
- CAGR, Sharpe, max drawdown, cash share, accepted-investable share, accepted position count, and flag mix were all the same or near-identical.

Interpretation:

- The simple pre-pruning rule did not change the real bottleneck.
- That tells us the underdeployment is not solved by a light gate added before the existing sizing logic.
- The strategy needs a deeper change in how capital is redistributed after the final survivor set is chosen.

### NB133 - capped residual HLP sleeve

- The notebook reported higher accepted investable equity on paper, rising to about `44.4%` of investable capital from `36.8%` in NB129.
- But realised cash stayed at about `63.15%` of equity and the realised performance line was identical to NB129.
- HLP still finished at roughly `4.16k USD`, the same end-position size as the baseline.

Interpretation:

- The HLP sleeve, as implemented in this notebook, improved accounting inside the alpha-model diagnostics but did not change the realised portfolio.
- In other words, this was not a real deployment fix in its current form.
- That is actually useful to learn: a residual HLP sweep can look good in diagnostics without truly changing the portfolio unless it is wired all the way through the position and trade path.

Practical conclusion:

- We should not treat NB133 as evidence that an HLP sleeve works.
- We should treat it as evidence that an HLP sleeve needs a more rigorous implementation and verification path than a late-stage bookkeeping patch.

## Cross-experiment conclusions

### 1. The main bottleneck was structural, and NB130 proved it

- NB130 showed that the baseline underdeployment was not mainly caused by a lack of vaults.
- The strategy could, in fact, deploy most of the capital once the survivor set was fixed first and then re-normalised properly.
- That means Hyperliquid does have enough investable vault depth for a much fuller book than NB129 was actually holding.

### 2. The second bottleneck is real capacity, not denominator noise

- After fixing the denominator problem, the remaining bottleneck became pool-size caps and concentration.
- This is a much healthier problem to have: it means we moved from “the allocation logic is wasting cash” to “the portfolio is finally pushing against genuine capacity limits”.

### 3. Equal-weight is safer here, but too conservative to solve deployment

- NB131 confirms that equal-weight can preserve very strong risk-adjusted returns and very low drawdown.
- But in this particular branch it is too gentle to get capital into the market.
- So the best production answer is unlikely to be pure equal-weight deployment.

### 4. HLP is not a shortcut

- The historical README warning from `NB73` still stands up well.
- HLP should not be treated as a magic sink for leftover capital.
- If we use HLP at all, it should come after the main survivor-set allocation is already correct, and it must be validated on realised portfolio state rather than diagnostic counters alone.

## Revised recommendation

The experiments changed the recommendation meaningfully.

### Strongest research finding

- The best real fix was **survivor-first re-normalisation** from `NB130`.
- It is the only variant that substantially improved true deployment.

### Why it is not yet the production answer

- It raised drawdown from `-4.95%` to `-8.09%`.
- It shifted the strategy from “cash drag dominated” to “concentration and pool-cap dominated”.
- That is a legitimate research win, but not yet the clean production trade-off.

### Best next experiment now

- Keep the `NB130` survivor-first sizing path.
- Add a milder concentration control on top of it.
- The target is to retain much of the jump from `36.8%` to `82.3%` deployment while pulling drawdown back towards the baseline region.

That is now a much better next step than:

- pure equal-weight deployment
- light pre-pruning rules
- or a cosmetic HLP residual sweep

## Suggested next experiments

These are now re-ordered based on the executed notebook results rather than the initial hypotheses.

| Priority | Experiment | Why it should improve cash efficiency | Why it is now the right follow-up |
|---|---|---|---|
| `1` | Survivor-first re-normalisation plus a milder concentration guard | Start from the `NB130` path, then cap post-recycling concentration more gently | `NB130` proved the deployment fix works; now the goal is to recover drawdown discipline |
| `2` | Two-pass allocation with residual recycling across accepted names only | Keep the survivor-first basket, then redistribute any leftover cash only to accepted names still under their caps | This targets the new, genuine capacity bottleneck rather than the old denominator bottleneck |
| `3` | Survivor-first sizing with a soft TVL-aware tie-break | When many mature vaults look identical by age-ramp, prefer the ones that can actually absorb more size | This may reduce the new pool-cap bottleneck without introducing a noisy continuous TVL multiplier |
| `4` | Fully wired and verified residual HLP sleeve | Only after the main book is correct, test a true realised HLP sleeve with explicit end-position verification | `NB133` showed that diagnostic-only improvements are not enough; the trade path must be real |

## Concrete experiment designs

### Experiment 1: post-floor re-normalisation

- Keep the current `age_ramp`, `min_tvl=15k`, `min_age=0.0`, and daily rebalance rules.
- Apply the normal allocation pass.
- Drop all signals below the minimum trade size.
- Re-normalise only across the survivors.
- Repeat the cap pass once.

Result:

- This worked.
- It is no longer a hypothesis; it is the best-performing real deployment fix found so far.
- The remaining job is to tame the extra concentration and drawdown it introduced.

### Experiment 2: age-ramp gate plus equal-weight survivors

- Keep `age_ramp` for ranking and selection.
- Select the final deployable set after the trade-size filter.
- Allocate equal weight across that set.
- Compare against the current notebook on CAGR, Sharpe, max drawdown, average cash weight, and worst idle-cash day.

Result:

- This did not solve the cash problem.
- It improved defensiveness but made ticket sizes even smaller and left more money idle.
- It is now best viewed as a conservative benchmark, not the main path forward.

### Experiment 3: dynamic max-assets rule

- Replace the fixed `max_assets_in_portfolio=15` with a rule that solves for the largest tradeable set each day.
- One simple version is: keep adding ranked vaults until the next position would fall below the minimum trade size, then stop.
- Another version is: target a minimum ex-ante ticket size such as `3k`, `4k`, or `5k` and let the portfolio breadth float.

Result:

- This made no material difference in the executed notebook.
- The simple gate is too shallow a change for the actual bottleneck.

### Experiment 4: capped residual HLP sleeve

- Only after the main vault book is built, send any remaining residual cash to HLP.
- Hard-cap HLP at `5%`, `7.5%`, and `10%` of equity as a small grid.
- Do not override the main vault allocations to make room for HLP.

Result:

- As implemented here, this did not create a real portfolio change even though the diagnostics improved on paper.
- It needs a stricter end-to-end implementation if it is to be taken seriously as a follow-up.

## What not to prioritise

| Idea | Why it is lower priority |
|---|---|
| Full HLP cash sweep modes | `NB73` already found that they worsened drawdown relative to baseline |
| Dispersion-aware switching | `NB72b` showed the extra logic rarely activated and still underperformed |
| Heavy TVL multipliers | The README shows TVL-based multipliers were usually noisy and not robust |
| New overlay signals | `NB123` is a strong warning that most overlays failed walk-forward even when they looked good in-sample |

## Recommended order

1. Build a new notebook on top of `NB130`, not `NB129`.
2. Test survivor-first re-normalisation with a milder concentration guard.
3. Test survivor-first re-normalisation with residual recycling across accepted names only.
4. Only then revisit HLP, and only with explicit realised-position verification.

The experiment batch changed the answer clearly: the right next branch is no longer “try lots of cash sweeps”. It is “keep the NB130 deployment fix, then reduce the extra concentration it introduced”.
