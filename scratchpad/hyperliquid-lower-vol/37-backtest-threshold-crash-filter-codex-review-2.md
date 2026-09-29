Review of [NB37](</Users/moo/code/getting-started/scratchpad/hyperliquid-lower-vol/37-backtest-threshold-crash-filter.ipynb>):

- **Material — cells 14, 23, 29, 37; heading cell 0 finding 4.** The “unlimited” inverse-variance book is still mischaracterised. `max_assets_in_portfolio=999` makes all survivors signals, but `AlphaModel._normalise_weights_size_risk_positions()` then processes them sequentially by raw inverse-variance weight and stops when residual equity is below its `$5` epsilon. All unprocessed signals receive zero targets. Thus the roughly 25 realised names are principally an endogenous effective top-weight allocation, not evidence that the 0.5% close epsilon or trade thresholds “truncate the tail”; TVL caps adjust accepted sizes but do not themselves explain the count. The raw result is valid, but the strategy description is not.  
  Fix: report non-zero targets, zero-target signals, and the allocator stopping condition per decision; describe it as a sequential, inverse-variance-weighted effective-cap strategy.

- **Material — cells 14, 23, 27, 29; heading cell 0.** The hysteresis code is mechanically correct (`> exit` for held names; `> enter` for unheld names; non-finite values retained), but its operation is not auditable from the log. `CRASH_LOG` records neither each candidate’s held status nor the limit applied. More importantly, the headline six-name threshold runs report zero held exclusions, so the log supplies no evidence that the exit branch mattered there.  
  Fix: log held candidates, per-candidate applied threshold, and counts retained specifically because they sit between enter and exit; report these beside realised holdings. Describe the main-family result as a threshold result with hysteresis unverified, not as evidence for hysteresis.

- **Material — heading cell 0, summary paragraph after the scorecard; cell 33.** “Every N in 1–4 fails at least two standing gates” remains false. `thr100_n3` and `thr100_n4` have only gate 6 failed; gate 2 was not run. The earlier paragraph’s more careful statement (“REJECTED on at least one standing gate”) is correct, but the later summary reintroduces the original error.  
  Fix: replace with “every N in 1–4 has at least one observed standing-gate failure; several also have gate 2 unevaluated”.

- **Material — heading cell 0 finding 1 and scorecard; cell 33.** `thr150` is correctly marked “REJECT by gate 6”, but “economically NOT CONFIRMED” and “a ridge … not a spike” undermine that verdict. Under the stated rule, a centre more than 0.25 Sharpe above either neighbour fails the flatness test precisely because it has the prohibited spike-like shape. “NOT CONFIRMED” is reserved for candidates passing every standing gate.  
  Fix: retain the observed one-sided-cliff description, but state that it fails the pre-registered flatness rule and is therefore REJECT; remove the alternate verdict.

- **Material — heading cell 0 finding 4.** The “own plan” framing is not fully honest to the current objective. The book has lower realised volatility, but lower Sharpe than the anchor, a negative late CAGR, no plateau evaluation, and very high return kurtosis. Calling it “the stable-curve shape this track was asked for” changes the objective after seeing the result. The surrounding caveats help, but do not cure that claim.  
  Fix: call it a post-hoc low-volatility observation, not evidence for the current Sharpe objective or a recommendation for a follow-on plan.

- **Minor — cell 32 versus cell 33.** The Part 4 text says the mask runs for two filter configurations plus “three best remaining” runs. The executed list has six runs: those two, the unlimited run, and three additional high-Sharpe rows.  
  Fix: state the exact six-run selection rule.

- **Minor — heading cell 0 finding 1; cell 27.** “Gives up 17.3% of CAGR” is dimensionally ambiguous: 37.9% to 20.6% is **17.3 percentage points**, or about a 46% relative reduction.  
  Fix: say “17.3 percentage points of CAGR”.

What checks out: the prior fixes to unrun-gate handling, the explicit standing-gate tuple, the direct basket-difference/inertness check, the threshold analogue wording, the 37%/33% reductions, and the non-causal equal-weight interpretation are correctly applied. Cycle Sharpe and volatility remain on the two-day clock. The threshold boundary and permissive handling of missing volatility are also correct.

Overall verdict: **material interpretation and reporting corrections required; no blocking mechanical backtest error found.**