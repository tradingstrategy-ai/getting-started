# A different Hyperliquid vault strategy after PR #61

Prepared on 14 October 2026. This is a research direction and proposed experiment, with no new measured results. The goal is a substantially more profitable strategy with acceptable downside.

[PR #61](https://github.com/tradingstrategy-ai/getting-started/pull/61) has no posted discussion comments, inline comments or reviews at the time of this review. Its concluding findings provide the closure record. This direction uses the [research summary](summary.md) and [ranking/exposure/sizing audit](ranking-exposure-sizing-audit.md), and supersedes this branch's initial sell-band × RS01 proposal.

## The proposed strategy

Build a **factor- and regime-aware vault portfolio**, adding **underlying vault-book signals** where historical evidence supports them. Estimate where returns come from, whether those sources are likely to remain profitable, and how vaults can lose money together. Allocate directly across the eligible universe and cash.

The economic hypothesis is that persistent trading skill, market exposure, funding income and current leverage contain information that trailing clipped performance ratios obscure. Complementary return sources could support a stronger portfolio without a fixed six-vault core. This is unconfirmed: decomposition alone does not establish predictability.

C00 remains a separately executed benchmark. The new strategy has no protected C00 core, inherited rank-six/rank-eight gate or mandatory inverse-variance sizing. Portfolio breadth and cash follow the new opportunity and risk estimates.

### What changes

The table describes proposed rules, not measured performance.

| Decision | C00 | Proposed strategy |
| --- | --- | --- |
| Economic signal | Four clipped CAGR/Sortino inputs | Residual skill, conditional market exposure and, where observed, funding/leverage/book information |
| Entry selection | Ranked core with six-entry/eight-exit hysteresis | Compare feasible net opportunities across eligible vaults, incumbents and cash |
| Sizing | Regularised 90-day inverse variance and capacity waterfall | Joint scenario allocation using expected net growth, uncertainty and common downside |
| Position count | Six core positions | Determined by opportunities, diversification, costs and capacity |
| Cash | Target deployment limited by selected-vault capacity | Explicit alternative when available investments do not justify deployment |
| Diversification | Individual variance and concentration limits | Underlying exposure/style overlap and jointly modelled losses |
| Young vaults | Missing-score eligibility and regularised risk | Pooled priors with actual-observation confidence; unknown is not zero-profit or zero-risk |
| Trading | Source rebalance thresholds | Compare net hold/add/reduce/exit actions, including redemption conditions and cost basis |

Permission, leader-share, concentration, capacity and operational protections remain constraints. Distinguish them from research heuristics such as six slots, a 98% target and inverse-variance sizing. This proposal holds vault shares and cash; external derivative execution is outside its scope.

## Why a new optimiser alone is insufficient

Earlier work already moved beyond simple weighting. The failures identify what this experiment must change.

| Prior work | What was tried or learned | Consequence |
| --- | --- | --- |
| NB04–07 and NB10 | Performance formulas, multiple inputs, risk/K inside scores, ranking/sizing blends and allocation maps | Another formula grid is unlikely to supply a new economic signal |
| NB08–09 | Forecast diagnostics, weak incremental K evidence; NB08 also examined BTC/ETH-adjusted outcomes | A beta or residual-return chart alone repeats existing diagnostics |
| NB11–12 and NB14–19 | Risk estimation, covariance-related sizing, constraints, waterfall, breadth and extra-position policies | More positions and deployment have not reliably improved profit |
| NB21 | Expected-return/loss forecasts, conditional gain/loss magnitudes, basis-aware marginal allocation and adaptive breadth | Forecast-driven allocation already failed; a different solver does not repair misleading forecasts |
| NB22 | Managed-entry calibration and exposure-veto qualification | Better average bias did not establish useful local discrimination or a qualified filter |

For **1 January–4 October 2026**, C00 returns **58.59% CAGR, 2.474 Sharpe and −6.36% drawdown**. NB21's calibrated-score adaptive portfolio returns approximately **11.28% CAGR**, and its conditional-magnitude portfolio approximately **−39.74%**. NB21 predicts the supported C00 cohort's 30-day net outcome at −1.23% versus realised +1.81%. NB22's corrected forecast has rank IC −0.065 and sign accuracy near 49%. Reusing these ratio-derived forecasts with a more elaborate optimiser is not an evidenced solution.

The new distinctions are an explicit return-source model, market-conditional relationships and additional book information where available. Joint tail allocation is useful only if the information improves decisions. Each distinction needs its own control.

The small positive sell-band and RS01 differences remain recorded historical observations, but are not the central experiment for this goal. Full history overlaps 2026 and all these periods have been researched repeatedly.

## Return-source model

### Separate exposure from skill

Start with a parsimonious model of observed vault returns:

`r_i,[a,b] = alpha_i(z_a) × duration[a,b] + beta_i(z_a)' × F_[a,b] + epsilon_i,[a,b]`.

`F_[a,b]` is the factor return over the actual interval between NAV observations; `z_a` is market/style information observable at the decision; `alpha_i` is residual expected performance. Keep time scales and return units consistent. Check the approximation for large moves: additive factor residuals are not an exact leveraged trading identity.

Use BTC/ETH initially, with reference prices from `tradingstrategy.binance.price.fetch_binance_price()`. Additional factors need a distinct observed exposure and past-only predictive evidence. Do not assume rising markets favour every vault: prominent historical winners rose while BTC/ETH fell. Exposures and leverage can change with managers' books.

Fit with explicit pooled/hierarchical shrinkage so young vaults participate without a long-history exclusion. Estimate residual skill conservatively and test whether it persists. Compare zero-skill/exposure-only, pooled and unconditional residual forecasts before claiming a manager-skill edge.

### Market conditions and future outcomes

Begin with continuous observable conditions: market trend, realised volatility, cross-asset co-movement and funding conditions where point-in-time data exist. A discrete regime model is a later justified alternative. A hard-coded bull/bear switch introduces another unsupported rule.

Produce conditional distributions of feasible future net outcomes, rather than a clipped score called expected return. Model shared shocks and vault-specific uncertainty. Use chronological evaluation with purging for overlapping labels. Forecast horizons must reflect executable decisions and redemption restrictions, not whichever horizon wins on the 2026 account.

Declare how future factor paths and residuals are generated. Begin with paired historical market/residual blocks selected using past-only conditions and shrink conditional estimates towards a pooled distribution. Include a zero-market-drift control: a positive residual forecast must not silently depend on a claimed ability to forecast BTC direction. Preserve cross-vault dependence and interval support when constructing scenarios. Block length, conditioning strength and training window need chronological sensitivity checks.

Inspect calibration, tails and economic decisions together. Ranking vaults, predicting risk and deciding whether investment beats cash are different capabilities. Missing/young-vault forecasts should express uncertainty rather than silently turn a pooled prior into measured skill.

## Underlying book information

This route changes the information set most substantially. Establish feasibility before adding a historical strategy arm.

### Candidate signals and mechanisms

These are hypotheses, not established predictors. All fields must be available before the decision.

| Information | Economic mechanism | Limitation |
| --- | --- | --- |
| Signed asset exposure and gross leverage | Market shocks affect books differently; leverage amplifies outcomes | Turnover makes a static book an imperfect future exposure estimate |
| Funding income/cost relative to capital and positions | Carry can support earnings or erode them | Future funding is unknown; realised future payments are not features |
| Book concentration and margin headroom | Shared liquidation/concentration risk can be hidden by smooth NAV | Interpretation depends on margin mode and the complete account |
| Trading PnL, funding, fees and turnover | Distinguish repeatable trading income from beta and costly activity | Truncated histories and missing unrealised PnL can imply false skill |
| Exposure/leverage changes | Detect style drift and risk escalation earlier than NAV ratios | Requires reliable snapshots or reconstruction anchors |

The local `web3-ethereum-defi` package includes `eth_defi/hyperliquid/trade_history_db.py` and `equity_curve_reconstruction.py`, storing fills, funding and ledger events and reconstructing share-price/PnL curves. Tooling does not establish complete historical books or availability at a past decision.

The [official Info endpoint documentation](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint) limits `userFillsByTime` to the latest 10,000 fills. Pagination cannot recover older fills beyond that boundary. The local reconstruction also clips curves to available fill history. Realised PnL reconstruction alone is not a mark-to-market equity series or a complete historical book.

### Availability gate

Inventory existing snapshots, fills, funding and ledger records before downloading or fitting anything. Report vault-by-date coverage, observation/publication times, truncation boundaries, initial-position anchors, marked-price availability and discrepancies against observed NAV.

Do not initialise every position to zero at the first retained fill, reconstruct a whole book from one coin's `startPosition`, or use today's positions in historical decisions. Reconcile per-coin anchors, transfers, spot holdings and unrealised PnL separately. Unknown publication timing is a disclosed limitation on historical executability.

If history is inadequate, run the NAV/factor arm with its limitations and start a prospective book-data record. Keep the book proposal separate; do not call a NAV proxy the implemented book strategy. A shorter covered cohort supports a labelled feasibility study, not a matched full-history replacement claim.

## Joint portfolio construction

Let `w_i` be the equity allocation to vault `i`, with `w_cash = 1 − sum(w_i)`. Feasible action `w` has scenario net wealth multiplier `G_s(w; holdings, basis, permissions)`, after redemption charges, funding of purchases and withdrawal restrictions.

An initial objective is:

`maximise sum_s p_s × log(G_s(w))`

`subject to tail_loss(w) ≤ declared risk budget, operational limits, w_i ≥ 0 and sum(w_i) ≤ 1`.

For example, define loss `L_s(w) = 1 − G_s(w)` and use scenario CVaR:

`tail_loss(w) = min_eta [eta + sum_s p_s × max(L_s(w) − eta, 0) / (1 − q)]`.

The tail confidence `q` and loss budget are declared preferences, not numbers selected to make 2026 pass. Report realised tail losses and sensitivity alongside the constraint's modelled value.

Only positive-wealth scenarios admit the log objective; liquidation/insolvency requires explicit treatment. Cash yield reflects what the account actually earns. Joint scenarios include common market/book shocks rather than independently shuffled vault returns. Disclose stress scenarios separately from calibrated probability forecasts.

Risk budget, confidence treatment, lookback/shrinkage and any practical position ceiling are design choices. Select a small set from past-only evidence or explicit investor risk preference, show sensitivity and disclose influence. Do not tune them on the final evaluation period or present them as universal constants. Classify concentration/TVL caps as hard execution limits or assumed policy choices.

Optimise executable hold/add/reduce/exit actions, including incumbent basis. A two-stage proxy is acceptable only with reconciliation to engine-funded trades and resulting exposure. More cash deployment, more positions or a higher in-sample objective is not a success criterion.

## Proposed next experiment

Working title: **NB24 — return sources and joint vault allocation**. Establish information and predictive feasibility before a small controlled strategy comparison. This replaces the incremental C00 factorial.

### Initial matrix

Isolate new information and conditioning; keep the joint allocator consistent across new-strategy arms.

| ID | Signal model | Construction | Question |
| --- | --- | --- | --- |
| A | Exact C00 | Existing six-position core/risk waterfall | Matched economic benchmark |
| B | Shrunk residual skill and factor exposures, without market-conditional skill | Joint allocation across eligible vaults and cash | Does return-source decomposition support a profitable new portfolio? |
| C | B plus market-conditional skill/exposure and downside scenarios | Same construction and execution as B | Does conditioning improve decisions beyond B? |
| D, gated | C plus historical funding/book/leverage signals | Same construction as B/C | Does new underlying information add value beyond NAV/factor inference? |

Use zero-skill/exposure-only forecasts as a prediction control without initially adding another engine account. Existing NB21 forecasts can be diagnostic references where cohorts and target labels match; mismatched targets do not isolate model effects.

D runs only where coverage/chronology qualify. If only a shorter cohort qualifies, execute a separate common-cohort A/B/C/D comparison and label dates/universe. Do not compare D's shorter CAGR directly with A's full archive result.

### Calendar, controls and accounting

Use fresh USD 150,000 per archive account, all prior indicator warm-up and NB20/NB23's corrected accounting:

- Short account: `[2026-01-01, 2026-10-05)` naive UTC, through 4 October; include 2025 warm-up.
- Full account: `[2023-03-01, 2026-10-08)`, through 7 October; final archive day partial.
- Fit chronologically using only resolved labels available before each decision; full-history fitting cannot learn from later 2026 outcomes.
- Retain partial-sale correction, fresh-entry tax reset and final-net-proceeds funding. Initially use the shared 10% positive-profit charge and 0.1% capital allowance for comparability; disclose unverified fee assumptions and qualify with real fee evidence when available.
- Reproduce C00 before interpreting challengers. Preserve matching source/input/execution identities; publication formatting can invalidate old byte-hash caches.

All archive histories are exploratory and repeatedly researched. Rolling splits improve discipline but do not create untouched confirmation. Freeze a surviving policy for genuinely later observations.

### Sparse data and young vaults

Use causal forward filling after inception for calendar accounting where justified. Fit return-source models on actual NAV changes over aligned observation intervals; carried prices are not additional independent measurements. Track quote age, interval duration, actual updates and joint exposure support.

Unknown scores/book fields retain pooled priors and uncertainty rather than automatic exclusion or safe-risk assumptions. Stale NAV, disappearance and absent future outcomes are not zero future returns. Report resolved, open, vanished and unsupported outcomes separately, including sensitivity to unresolved cases.

### Results and interpretation

Lead with 2026 key metrics, equity, drawdown, absolute asset weights, quarterly profit and cash. Report full history separately. Every element has a heading, short explanation and period; each image is separate.

Add return-source attribution, net-outcome calibration, common-factor exposures, tail-risk calibration, style/manager concentration, position count, turnover/costs and requested versus funded allocation. Show where the portfolio earns money and chooses cash. Pair diagnostics on common cohorts and use calendar/overlap block uncertainty rather than independent vault-row assumptions.

Compare C−B and, where qualified, D−C to separate information from optimisation. Run forecast ablations before expanding accounts. Check dependence on a single vault, quarter or isolated NAV update; deleting an influential ledger event is not an executable alternative strategy.

Continue if new information supports useful absolute opportunity decisions and improves net account economics at a disclosed downside trade-off. Record unqualified forecasts before adding complexity. Better risk prediction alone can justify a defensive lead, but does not establish a more profitable replacement. Large historical gains still require later confirmation.

## What remains unproven

No challenger is implemented or shown to beat C00. The book-history gate may prevent a full retrospective study. Residual skill can be unstable, exposures can change quickly and the NAV archive can be too sparse. This direction tests different economic information and construction, with those failures identifiable; it does not promise a breakthrough from another small C00 adjustment.
