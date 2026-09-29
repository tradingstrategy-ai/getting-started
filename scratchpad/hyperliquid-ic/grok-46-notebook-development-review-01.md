# Grok 4.6 notebook development review

Completed in the original review session after a turn-limit interruption. The first investigation is incomplete; the resumed final response ended successfully with `end_turn`, backend `grok-4.6-build`. Read with [the disposition](grok-46-notebook-development-disposition-01.md): some recommendations below were rejected.

**Verdict:** implement the chain, but freeze the gate, membership-replay and window-multiplication rules before any new arm. The 2×2 and ledgers are the right first-wave design. The published **24 + 6 + 3 + 14** budget overstates unique simulations.

Read and used: the notebook plan, parent plan, author disposition (not raw synthesis advice), NB23/24 summaries, NB18/20 screens, NB21/22 allocation decomposition, lower-vol NB28/32/39 extracts, waterfall NB69 extract, `hyper-ai.py` (`return_gate`, `inverse_vol`, `waterfall=False`), and `AlphaModel._normalise_weights_size_risk_positions`. No notebooks were executed.

---

## 1. Prioritised plan issues

**P1. Gate change vs original control (NB25–26).** Production excludes `return_gate` that is `None`, NaN, or `≤ −16%` (`hyper-ai.py`). That is an admission barrier for histories shorter than 14 carried days, not a sizing quirk. The parent plan keeps the original gate in the 2×2 and *adds* a labelled young-compatible gate. The notebook plan applies “whichever common gate NB25 established” to all four arms, then says B00 is reusable and a distinct control “adds at most 3”. Those cannot all be true. If the factorial switches gate, B00 is not the NB25 original-policy control, ranking contrasts are not original-admission contrasts, and “9 incremental” undercounts. If it does not switch, B10/B11 cannot answer young/sparse access. **Fix:** always keep NB25 original-policy (legacy gate). If that gate blocks young names, run the 2×2 *only* on the named common gate (same −16% threshold, available-history return when the 14-day mark is missing). Do not silently repair B11 only. Do not copy NB24’s *positive* 14-day diagnostic gate.

**P2. Window multiplier (shared contract, NB26–29).** Full, hyper-ai and later overlap; the plan already says they are not three confirmations. NB25 should reproduce the two saved NB24 controls and compute the later cold start (three simulations). For new arms, treat hyper-ai as a **slice of the native full run**, and add only the 1 Apr–8 Sep cold start. That is transport of NB24’s reporting, not a new hypothesis. Later is retrospective, not a holdout.

**P3. Frozen-membership replay (NB27).** B11’s live requested set embeds min-hold, closed-deposit skips and B11’s own fills. Replaying that list for equal / k=1 siblings is not an independent causal ranking snapshot. Keep the predeclared B11 parent even if it loses (good: not winner-picking). Reuse live B11 k=2 only if requested membership matches exactly; otherwise label a desired-membership diagnostic. If Jaccard of B11 vs B00 requested sets is ~1, NB27 is a fee-correct **transport of NB69**, not a new short-history basket test — run at most one equal-weight sibling, or skip.

**P4. 2×2 does not isolate lookback (NB26).** Ranking contrasts B10−B00 and B11−B01, sizing B01−B00 and B11−B10, are the right table. The sizing factor still bundles 90-day forward-filled `std` + `fillna(0)` versus 30-day interval `v` + 5% floor + median-finite fallback. Label it a **sizing-path** change. Portfolio B10−B00 can look like a no-op if original sizing zeros the new names; that is an allocation limitation (as the plan says), so the funded ranking test is B11−B01. Tie-break growth arms the same way as original (`(−score, pair_id)`). Do not add a positive-growth gate.

**P5. Inverse-risk fallback is specified, not a `drop_30` rerun.** Production missing `inverse_vol` → `0.0` is why StratWise can be eligible and unfunded. New path: missing `v` (one interval: `g` finite, `v` missing, not algebraic zero); median finite raw `1/max(v,0.05)^k` in the **selected six**; all missing → equal raw weights; then existing caps. That is the disposition’s choice, not Grok’s equal-share. Do not change it after seeing weights. Original-ranking arms keep original missing-score and missing-vol semantics.

**P6. E1 is probably not a no-op; do not import A0-cap numbers (NB28).** `waterfall=False` still loops leftover `equity_left` onto remaining selected names in `_normalise_weights_size_risk_positions`, then renormalises accepted dollars. Name that function as the step to disable. If a ledger shows leftover already cash, skip the six runs. Do not cite historical A0-cap ~12.5% / 1.17, summary-04, or pre-fee anchors (NB20/21 hyper-ai 34.2% / 1.74 versus fee-correct NB23 41.2% / 2.01). Production docstring ~62% CAGR is a different archive.

**P7. Cash match must not use another path’s equity (NB28).** Scale the **parent’s desired weights at t** by the invested fraction implied by applying E1/E2 to those same pre-trade weights. Do not target live E-path cash or hindsight dollars. Report fill error; do not call it cash-matched if it is not.

**E2 extra:** `exp(−D/0.10)` can near-zero a name while it still occupies a six-slot. That is not NB19/20’s forced replacement (0/12 full-period Sharpe improvements; 24 screened-vs-control pairs worse). Report slot occupancy vs effective holdings and cash. ATM’s observed D=0 still gets multiplier 1 — a limitation, not a reason to fit a name rule. Scale 0.10 stays frozen.

**P8. Sensitivity count (NB29).** Stated 12 lookback + 2 B11 leader-out = 14 is arithmetically right: B01/B11 × {14,60} × 3 windows = 12; B11 identity-out on two primary windows = 2. B01’s composite ranking does not change; only the sizing clock does. Skip 14/60 only when 30-day membership **and** funding are identical (no-op), not because they lose. Do not add a second mechanism’s leader-out after inspecting Sharpe. Full-period contributor removal is retrospective, as labelled. Overlapping daily labels are not extra samples.

Do not revive synthesis claims the disposition rejected: growth ranking is not NB32’s calmness-after-floor; lower risk need not predict higher return; monotonic `U(g)` is not a second ranker; Scared Money stays off in primary; no 20% CAGR-in-every-slice or beat-incumbent gate.

---

## 2. Duplication matrix

| New | Nearest earlier | New question | Class |
|---|---|---|---|
| NB25 | NB23/24 fee-correct original inverse-variance anchors; lower-vol NB28/34 vol persistence | Can interval features and the **corrected** control operate? Does the 14-day gate block young names before sizing? | Control **transport** + coverage. Not another IC grid. |
| NB26 B00 | Same anchors | Reproduced original policy under the factorial’s frozen extras | Reproduction |
| NB26 B10 | NB24 ranking isolation was monthly vs original at **equal** weight; NB32 ranked calmness after a return floor (26/30 non-incumbent configs negative) | Does available-history **growth** change requested membership vs composite, original sizer held fixed? | **New ranking question.** Weak as a funded test if old sizer zeros newcomers. |
| NB26 B01 | NB69 vol vs equal/composite on the **incumbent** basket (pre-fee, 20% pool cap, ffill vol) | Does short **interval** inverse-variance plus missing-`v` fallback fund the original selected set? | New sizing path on the old book. Invalid to quote NB69 CAGRs. |
| NB26 B11 | Synthesis option 1 bundled rank+sizer; disposition demanded the 2×2 | Joint short-history access | New joint path; interpret via contrasts, not as one “winner”. |
| NB27 | NB69 equal / k=1 / k=2, frozen incumbent membership | Same sizers on **B11’s** requested set | New **if** membership differs; else NB69 transport on this engine. |
| NB28 E1 | A0-cap; NB13 redistribute control; this allocator’s leftover loop | Does turning **this** recycle off leave cash on the original-policy book? | Conditional. Code check first. |
| NB28 E2 | NB19/20 hard DD/weekly overlays | Continuous DD shrink, no eligibility change, cash retained | Distinct mechanism. Soft exclusion can still consume a slot. |
| NB29 14/60 | NB32 lookback grid (only 45-day floor positive in that design) | Ranking contrast at 14/60 **sizing** clocks | Predeclared sensitivity, not a search — skip if 30-day is a membership no-op. |
| NB29 leader-out | NB24 C36_leader_out (−38.1% → −47.3% CAGR); NB32 LOVO | Concentration on B11, not a blacklist | Diagnostic **transport**. |

NB23/24 already showed saturated monthly scores and later young top-groups at −15.6% / 60d versus mature +1.8%; that is historical description, not a licence for a long-history admission rule or a claim that short growth will pay.

---

## 3. Minimal corrections and order

1. **NB25 only:** hash-frozen NB24 inputs, fee-correct original replay, feature panel, gate coverage, ledgers. Stop if the control misses recorded equity/date tolerance.\
2. **Gate freeze in writing:** original-policy = NB25. Factorial = common young-compatible gate **only if** the audit shows blocking. Extra runs: 3 common-gate B00, not a second 2×2.\
3. **NB26:** 4 arms on full native + later cold start; hyper-ai sliced. Attribute ranking from B11−B01; report B10 zeros as sizing, not “growth failed”.\
4. **NB27:** only if B11 requested membership materially differs; 2 new sizers × 2 simulations (full + later) if B11 k=2 replays.\
5. **NB28:** E1 ledger against `_normalise_weights_size_risk_positions`; skip if no-op. E2 + causal parent-weight scaling, original-policy parent, not the best NB26 row.\
6. **NB29:** artefacts only; 14/60 iff 30-day membership/funding moved; one predeclared B11 leader-out pair.

Revised unique simulations if the common gate is needed and E1 is real: NB25 3 + factorial 9 + common-gate B00 3 + sizing ≤4 + E2+scale 4 + optional E1+scale 4 + lookbacks only if live. That is well below 47 without dropping a mechanism.

Six names / 33% caps stay **diagnostic**, not product requirements. 1–n remains allowed later.

---

## 4. Explicit missing coverage

Not bugs: graded fallback inside the original composite (deferred D); 1–n breadth / cap-off (NB22 withdrew the N-as-quality reading; stale-mark Sharpe is not this test); E2 on a high-growth book (ATM-class jumps still have D=0); fee-correct equal-weight on **original** membership (NB69 direction only); cadence; TVL/social factors (in scope to omit). Interval `v` may proxy freshness but is not a freshness policy.

Price-only rules will not catch the next ATM. Overlapping windows and reused history cannot prove future profitability. Lower risk with enough profit in the ~20% CAGR region can still serve the user.
