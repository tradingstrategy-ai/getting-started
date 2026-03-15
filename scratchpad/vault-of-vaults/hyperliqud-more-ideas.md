# More Ideas For Vault-of-Vaults Robustness

NB78 through NB80 shifted the project from broad parameter hunting toward a more useful question: do the main design choices still hold up once we stop focusing on single winning rows and start asking whether the architecture is stable? The current evidence points to a provisional but fairly coherent view. Bayesian-style gating still looks like the strongest selection layer. Equal weight or only mildly signal-responsive sizing still looks safer than aggressive tilt. Weekly cadence, once the implementation bug was corrected, is weaker than daily in the current Hyperliquid-only setup. That leaves one main remaining risk: not that we missed one magical parameter, but that we may still be over-trusting in-sample winners and under-testing robustness.

What we now believe:

- Gate quality matters more than fancy sizing.
- Mild sizing is plausible, but equal weight remains a serious baseline and not just a fallback.
- Some historical weekly results were either artefacts or stale benchmarks rather than current reproducible evidence.
- Robustness matters more now than squeezing out another increment of headline CAGR.

## NB81 idea: Walk-forward validation of the full gate + weight architecture

### Why this matters

NB67, NB78, and NB80 all improved our understanding, but they still rely mainly on pooled historical backtests. That is useful for narrowing the search space, but it does not really answer the question we care about now: if we choose a gate-plus-weight architecture using the past, does it still hold up in the next unseen month? This is the cleanest way to test whether the current preference for mild tilt over equal weight is real, or whether it mostly reflects in-sample tuning luck. It also helps separate "robust enough to trust" from "best row in one sample."

The broader literature is very clear that a strong in-sample Sharpe can be misleading when many model variants are compared. [Bailey and Lopez de Prado's Deflated Sharpe Ratio](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551) is directly relevant here because the vault notebook chain has already tried many gates, transforms, and weighting rules. For a practical cross-validation framing, the [QuantBeckman article on combinatorial purged cross-validation](https://www.quantbeckman.com/p/with-code-combinatorial-purged-cross) and Quantreo's write-up on [walk-forward optimization in trading](https://www.blog.quantreo.com/the-walk-forward-optimization-in-trading/) are useful reference points. For a more modern system-level framing, the [AlgoXpert Alpha Research Framework](https://arxiv.org/abs/2603.09219) is a good example of treating strategy research as a disciplined validation pipeline rather than a leaderboard exercise.

### Experiment design

Use daily cadence only and keep the strategy family intentionally narrow. Split the Aug-2025 onward period into anchored or rolling train/test folds: for example, train on a fixed 120-day history, select the best row from a small fixed matrix, and test it on the next 30 days. Repeat forward through the sample. The search matrix should stay small and explicit:

- gate family candidates such as Bayesian credibility and Bayesian sterling
- sizing choices restricted to equal weight and mild blends
- `blend_alpha` restricted to `{1.0, 0.8, 0.6}`
- `weight_signal` restricted to `{rolling_sharpe, rolling_returns}`
- `volatility_window` restricted to `{90, 120}`

The important output is not pooled full-period Sharpe. It is fold-level behavior: which architecture wins how often, how close the runners-up are, and whether the same design keeps showing up near the top. Baselines should include Bayesian gate plus equal weight, Bayesian gate plus mild blend, and the current best daily mild-weight configuration from NB78.

### What would change our mind

If the same gate-plus-weight architecture keeps placing near the top across most holdout folds, then we can start treating it as a genuine production candidate rather than an in-sample favorite. If fold winners bounce around, or if equal weight is always close enough that the mild tilt adds no reliable edge after holdout testing, that would be strong evidence that the project should simplify further and stop treating mild tilt as an important degree of freedom.

## NB82 idea: Gate family ablation with sizing deliberately held simple

### Why this matters

The README now points in a fairly consistent direction: selection is where most of the edge lives. That makes gate design the highest-value remaining research problem. Bayesian credibility has come through the notebook gauntlet as the best incumbent, but it has also mostly been evaluated inside a familiar surrounding design. A gate ablation notebook would ask a sharper question: if we deliberately hold sizing simple and almost inert, does Bayesian credibility still win because it is truly the best selector, or because the rest of the architecture has adapted around it?

This is closely related to the empirical-Bayes logic behind learning across related assets or funds. [Efron and Morris](https://academic.oup.com/biomet/article-abstract/59/2/335/325580) provide the classical shrinkage foundation, while [Jones and Shanken](https://faculty.marshall.usc.edu/Christopher-Jones/pdf/jones_shanken_2005_jfe.pdf) show why learning across funds can dominate naive treatment of noisy performance histories. For a broader Bayesian framing in finance, [Jacquier, Polson, and Rossi](https://people.bu.edu/jacquier/papers/bayesfinance.2011.pdf) are a useful conceptual reference. The real question underneath NB82 is whether "learning across vaults" is the right mental model for uneven track records and young-vault uncertainty.

### Experiment design

Hold sizing fixed at equal weight or at most a very mild blend, and then compare only gate families. This notebook should avoid conflating a better selector with a compensating sizing trick. A reasonable gate set would be:

- positive Bayesian credibility
- Bayesian sterling
- PSR-only gate
- simple age-gated `rolling_sharpe > 0`
- percentile-rank metadata gate

Run the comparison on both the canonical Aug-2025 start and the extended Jan-2025 start from NB80. The point is not just to find the top row on each range, but to see whether the same gate remains good under both a shorter, more mature universe period and a longer period with sparser early history.

### What would change our mind

If Bayesian credibility stays top-tier across both date ranges without needing a different downstream weighting rule, then it becomes much more defensible as the default gate. If a different gate wins on the longer history, or if gate preference changes with sample window, that would suggest the current “Bayesian gate is the answer” conclusion is still too sample-dependent and should be weakened.

## NB83 idea: Equal weight vs mild blend vs rank tilt

### Why this matters

NB62 through NB65, and then NB78, all point toward the same conclusion: signals are useful for deciding which vaults deserve inclusion, but much less reliable for deciding exactly how much bigger one surviving vault should be than another. That does not mean the sizing question is fully closed, though. One clean remaining possibility is that ordinal or capped rank-based sizing could retain a little more information than equal weight without amplifying noise the way raw signal-proportional weights do. This notebook would be the last serious attempt to find a sizing rule that is still simple, bounded, and plausibly robust.

This is where the classic portfolio-construction literature is helpful. [DeMiguel, Garlappi, and Uppal](https://www.nber.org/system/files/working_papers/w14525/w14525.pdf) remains one of the clearest warnings that simple allocations often outperform more “optimized” ones once estimation error is acknowledged. The paper on [small rebalanced portfolios beating the market over long horizons](https://academic.oup.com/raps/article/13/2/307/6874022) is relevant because it highlights how smaller, simpler, regularly rebalanced constructions can be surprisingly resilient. For practitioner context, [Alpha Architect on how portfolio construction affects the reliability of outcomes](https://alphaarchitect.com/2021/04/how-portfolio-construction-impacts-the-reliability-of-outcomes/) and the [CXO Advisory summary of weighting schemes](https://www.cxoadvisory.com/strategic-allocation/best-weighting-scheme-for-a-stock-portfolio/) are useful complements.

### Experiment design

Fix the best gate from NB81 or NB82, then compare only a small family of simple sizing rules:

- equal weight
- mild blend with `blend_alpha` in `{0.8, 0.6}`
- capped rank tilt
- top-k equal weight with values such as `k ∈ {10, 15, 20}`

Do not reopen the full sizing zoo. No passthrough weights, no waterfall, no HLP sweep logic, no softmax temperature search. Keep the test focused on the one unresolved idea: whether a bounded ordinal sizing rule can beat equal weight or mild blend without reintroducing the same noise-amplification failure mode seen in NB62-NB64.

### What would change our mind

If equal weight and mild blend remain functionally tied, then the simpler implementation should win by default and the sizing question can mostly be declared settled. If capped rank tilt wins consistently with lower churn and similar drawdown, that would be the one remaining sizing method worth promoting into the core architecture.

## NB84 idea: Does the best weighting rule depend on universe breadth?

### Why this matters

NB77 is an important warning against over-generalizing from Hyperliquid-only evidence. In the narrow Hyperliquid-only daily universe, mild tilt still looks acceptable. In the broader cross-chain universe, equal weight appears stronger because the larger opportunity set already provides more natural diversification. That raises a structural question: maybe weighting is not a single global choice at all. Maybe the best rule depends on the shape of the universe, the amount of cross-sectional dispersion, and how concentrated the opportunity set is.

There is a broader diversification literature behind this idea. The [Journal of Asset Management paper on alpha concentration versus diversification](https://link.springer.com/article/10.1057/s41260-021-00226-0) is relevant because it speaks directly to the tension between focusing on strongest convictions and preserving robustness. The [Alpha Architect piece on portfolio construction and reliability](https://alphaarchitect.com/2021/04/how-portfolio-construction-impacts-the-reliability-of-outcomes/) is useful here too, as is the [CFA Institute discussion of portfolio concentration](https://blogs.cfainstitute.org/blog/2018/04/23/portfolio-concentration-how-much-is-optimal/). Locally, NB77 itself should be cited as the internal evidence that broader universes can flip the relative attractiveness of equal weight versus tilt.

### Experiment design

Run the same restricted gate/weight matrix on two universes:

- Hyperliquid-only
- a cross-chain NB77-style universe

Hold everything else as constant as practical: same gate candidates, same mild-weight set, same reporting metrics, and preferably the same cadence if feasible. In addition to the normal performance table, include concentration diagnostics such as top-5 weight share, realized PnL concentration, and capital utilization. The purpose is not only to compare CAGR and Sharpe, but also to see whether the weighting rule interacts with the natural diversification of the universe itself.

### What would change our mind

If the preferred weighting rule flips by universe, that would be a valuable result in its own right. It would mean the project should stop searching for a universal weighting default and instead document a universe-conditional rule. If one simple rule wins in both the narrow and broad universes, then confidence in that rule rises sharply.

## NB85 idea: Leave-one-winner-out robustness

### Why this matters

A strategy can look diversified in weights while still depending economically on a very small number of vaults. NB80 already hinted at this by noting that a small handful of vaults produced a large share of total PnL. That is not necessarily bad, but it does raise a real robustness question: are we looking at a diversified architecture, or at a strategy that happened to find a few outsized winners? This notebook would be a stress test for hidden dependency rather than another optimizer notebook.

There is a nice conceptual parallel here with sensitivity and jackknife analysis. The [Portfolio Probe note on jackknifing portfolio decision returns](https://www.portfolioprobe.com/2012/05/28/jackknifing-portfolio-decision-returns/) is a practical reference for asking how much a portfolio result depends on any one component. The paper on [theoretical and empirical estimates of mean-variance portfolio sensitivity](https://www.sciencedirect.com/science/article/abs/pii/S0377221713003160) is relevant because it formalizes how portfolio outputs can be unstable to small estimation changes. The paper on [diversification in portfolio optimization](https://www.sciencedirect.com/science/article/abs/pii/S0957417421006369) is useful as a broader robustness framing.

### Experiment design

Start from the leading architecture from the earlier robustness notebooks, then rerun under perturbations rather than re-optimizing everything:

- exclude the top 1 PnL vault
- exclude the top 3 PnL vaults
- leave one protocol out
- leave one launch-age cohort out

Measure not only changes in CAGR, Sharpe, and max drawdown, but also how turnover and capital utilization respond. A genuinely structural edge should degrade gradually when strong contributors are removed. A fragile edge will collapse quickly once a few winner vaults are removed from the sample.

### What would change our mind

If Sharpe or CAGR collapse after removing only one or two major contributors, then the architecture is still too dependent on lucky winners and should be described as fragile. If performance deteriorates gradually and remains respectable under these perturbations, then the case for a genuine, diversified process becomes much stronger.

## Suggested order

1. NB81 walk-forward validation
2. NB82 gate ablation
3. NB83 sizing shootout
4. NB84 universe-breadth interaction
5. NB85 leave-one-winner-out robustness

The sequencing matters. NB81 is first because it tells us whether we are still being fooled by in-sample winners. NB82 comes next because gating now looks like the most important unresolved design choice. NB83 may let us close the sizing question cleanly and stop spending research cycles on weight maps that are unlikely to matter. NB84 then tells us whether any conclusions are Hyperliquid-specific or general across broader universes. NB85 is the final stress test: even if a design looks good on all the previous metrics, we still want to know whether the apparent diversification is economically real.
