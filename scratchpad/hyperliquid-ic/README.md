# Hyperliquid information-coefficient research

The active implementation follows [rewrite-plan-01.md](rewrite-plan-01.md).
It issues daily predictions from causally forward-filled vault NAVs,
supports young and weekly-observed vaults, and keeps sparse interval evidence
separate from observed daily risk. Raw observation freshness remains available
as a provenance and carried-mark diagnostic.

[summary-02.md](summary-02.md) records the first completed rewrite run:

- headline interval: 13 September 2025 to 12 September 2026;
- 365 daily decision dates and 87,081 eligible headline-year rows;
- 21 targets covering seven horizons and three primary outcomes;
- expanding monthly out-of-fold models and the incumbent/fixed/adaptive replay.

The shared implementation is [ic_research.py](ic_research.py). The notebooks
run in order and save the rewrite artefacts under the _artifacts-rewrite
directory, leaving the original artefacts experiment untouched:

1. [01-data-and-baseline.ipynb](01-data-and-baseline.ipynb)
2. [02-feature-panel.ipynb](02-feature-panel.ipynb)
3. [03-ic-screen.ipynb](03-ic-screen.ipynb)
4. [04-allocation-validation.ipynb](04-allocation-validation.ipynb)

The results do not support a change to the production strategy. The next step
is block uncertainty and permutation testing for a predeclared,
horizon-specific candidate, followed by exact strategy-engine settlement
accounting.

The stable-profit follow-up is implemented in [stable-profit-plan-01.md](stable-profit-plan-01.md):

1. [05-stable-profit-selection.ipynb](05-stable-profit-selection.ipynb) diagnoses the selectable pool, fits the fixed severe-loss classifier and replays A0 through A3.
2. [06-repeatability-and-direction.ipynb](06-repeatability-and-direction.ipynb) computes bounded path, sampling and BTC-direction diagnostics.
3. [07-stable-profit-validation.ipynb](07-stable-profit-validation.ipynb) evaluates weekly marks, young access, accepted-dollar sizing and falsification checks.

Its outputs are under `_artifacts-stable-profit`; [summary-03.md](summary-03.md)
contains the primary results and shortlist decision. The A0 no-op replay is
bit-for-bit equal to the earlier incumbent replay on the saved research ledger.

Earlier [plan.md](plan.md), [summary-01.md](summary-01.md) and Claude reviews
are retained as history. The [Fable rewrite review](claude-review-fable-rewrite-01.md)
is also retained; the rewrite contract takes precedence where older documents
conflict.
