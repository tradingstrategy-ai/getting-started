## Review outcome

The executed screen is arithmetically sound: causal T−1 access, forward windows, cycle-clock metrics, shared two-way bootstrap, complete-family max-T handling, finite-draw p-values, and the common-sample calendar/fresh comparison are all correctly implemented. The raw gate-5 result is accurately **0/13**.

The oracle calibration is also technically sound: directions are correct, noise avoids zero-SE degeneration, and `oracle_all` passes even under an expanded (therefore more conservative) family. It establishes that the **raw, implemented stability clause is computationally reachable**.

Findings:

| Severity | Cell | Finding | Fix |
|---|---:|---|---|
| Material | 0 | The provenance statement is still false, repeating the second-round finding. It says `vault-prices.parquet` is 254,818,366 bytes / `3e79966a`; cell 22 reports 255,136,297 / `8bce13191183c7d4`. `_prov()` / `PV` are computed in `write_heading_28.py` but never used in the rendered snapshot line. | Render that line from `PV["bytes"]` and `PV["sha256"]`, then regenerate the heading. |
| Material | 0 | Several numerical heading citations point to the wrong cells, contrary to the standing reporting rule. The paired comparison is in cell 39, not 37; tail-sign agreement is cell 37, not 35; persistence/confounds are cell 41, not 39; corrected-indicator descriptives are cell 39, not 37. The initial corrected-screen citation also includes unrelated cell 41. | Correct the references in `_build/write_heading_28.py` and regenerate. |
| Material | 0, 35 | The oracle result is overstated: “the thirteen real signals … fail it because none predicts concentration independently” is not established. The test shows no tested signal has a positive simultaneous lower bound for the raw concentration target; it does not test conditional independence, establish a causal reason, or validate the count-confounded target. An oracle built directly from outcomes can demonstrate mechanical reachability even if the target remains defective as a stability measure. | Replace with: “none of the thirteen signals established a positive association with this raw concentration target under the simultaneous screen.” Keep the existing caveat about reporting-count dependence. |

The prior technical findings were otherwise addressed correctly. In particular, the new oracle means the all-zero raw-screen result is no longer merely an unexplained mechanical impossibility; it supports the narrower conclusion that none of these signals passed this implementation.