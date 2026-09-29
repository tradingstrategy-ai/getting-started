## Findings

- **Material — cell 0, finding 1.** The ranker’s `0.68` LOVO retention is described as “the anchor’s dependence plus 6.6 percentage points more of it”. The 6.6 pp is the difference in positive-P&L share (48.5% vs 41.9%), not a decomposition of Sharpe retention; indeed 0.68 is below the anchor’s 0.825.  
  Fix: report these as separate diagnostics and remove the additive/inherited-dependence claim.

- **Material — cell 0, finding 4.** “N = 4’s return is the anchor’s largest position at twice the weight” and “whose result and whose drawdown are two names” overstate the evidence. Cell 34 shows the largest vault supplies about 64% of positive P&L, not all return; cell 36 lists further drawdown contributors.  
  Fix: say the book is highly concentrated in anchor-held names, with the largest position and the two largest drawdown attributions accounting for substantial shares.

- **Material — cell 0, finding 6.** The statement that the floor “sells out on June 18 as the score dips through 1.0” is not supported by the cited output. Cell 48 shows the position closed then, but does not print the `QUALITY_LOG` value or establish that the floor rather than another eligibility condition caused the exit.  
  Fix: either display the contemporaneous logged quality/floor decision, or say only that the position was absent from 18 June to 17 August.

- **Material — cell 0, finding 7.** “The rescue failed on the floor, not on the sleeve” is an unsupported causal attribution. The sleeve changes deployment dynamically, and realised deployment is materially below intended deployment at high floors. The notebook verifies that it does not deploy more than intended; it does not isolate the sleeve’s performance contribution from the floor’s.  
  Fix: conclude that the tested floor-and-sleeve construction failed, while limiting the sleeve conclusion to correct, non-overdeploying implementation.

- **Material — cell 0, final interpretation.** The notebook repeatedly states that new runs are exploratory sensitivity calculations rather than verdicts, but later calls the floor rescue “REJECTED”. This contradicts its own stated reporting rule. “Never worse than the anchor” is also unqualifiedly false: both `measured_8` and `thr150` have slightly worse maximum drawdown than the anchor, among other differing diagnostics.  
  Fix: use “would fail the standing-gate calculations” for the floor family, and replace “never worse” with a specific metric-qualified statement.

- **Minor — cell 0, robustness section; cell 48.** “The floor’s logged qualifying counts match an offline reconstruction on every decision” omits scope. Cell 48 checks the ten six-slot `anchor_*` and `thr150_*` runs, not the N=4 or unlimited floor variants.  
  Fix: say “on all 126 decisions for each of the ten six-slot runs checked”.

- **Minor — cell 0, finding 3 and windows summary; cell 52.** `thr150` and `thr175` are called “not the same mechanism” on window B. They are always distinct threshold rules; cell 52 merely shows that they no longer produce identical realised outcomes on that window.  
  Fix: say “no longer produce identical realised results” (or baskets, if separately shown).

## Checks that pass

- The quality score is causal at the T−1 interface, uses row windows consistently, and treats forward-filled marks as zero returns.
- The floor is correctly placed after the crash filter and before ranking; the empty-selection path is supported by the executed close-out behaviour.
- Sleeve arithmetic preserves the intended full-equity concentration ceiling, and the deployment table is honestly numerical: realised deployment is below, not claimed equal to, intended deployment.
- Cycle Sharpe and volatility use the two-day strategy clock with sample standard deviation.
- The fourth-round unlimited-book wording is now correct: unlimited capacity, capped weights, no sleeve, and qualifying holdings distinguished from realised holdings.
- The aligned band attribution is appropriately labelled as an aligned contribution rather than a counterfactual.

## Overall verdict

**Not ready to sign off on the interpretation.** I found no blocking backtest, quality-score, floor-placement, or sleeve-arithmetic error. However, the remaining causal/decomposition claims and the exploratory-versus-REJECT verdict language need correction before NB40 is an accurate forensic record.