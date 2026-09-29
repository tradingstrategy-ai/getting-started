"""The 2026-09-16 idiot-gate audit note, inserted into the headings of the notebooks whose
verdicts it corrects. One source for the text so the notebooks and RESEARCH-RULES.md agree.
Numbers are read from the manifests."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _m(n):
    return json.loads((HERE / f"manifest_{n}.json").read_text())


def _note(n: int) -> str:
    if n == 28:
        m = _m(28)
        s = m["screen_full"]
        two = [k for k, v in s.items() if v["evaluated"] and v["lo_forward_vol"] > 0 and v["lo_forward_downside"] > 0]
        return f"""## Idiot-gate audit, 2026-09-16 - verdict corrected in place

Gate 5 as pre-registered here was an idiot gate on two counts (see the audit section of
[RESEARCH-RULES.md](RESEARCH-RULES.md)): its three-target stability clause is unpassable on this
archive - the notebook's own oracle shows perfect volatility foresight fails it - and its 5 pp
return clause demands a significance the sample cannot supply (half-width 20-60x the margin).
The "0 of 13 pass gate 5" result stands as a fact about the gate, not about the signals, and the
twelve signals described below as "rejected without a backtest" are **NOT BACKTESTED, not
rejected**. Under the corrected gate 5 - forward volatility and forward downside only, lower
bounds above zero - **{len(two)} of 13 signals pass**: {", ".join(f"`{k}`" for k in two)}. Only
`inverse_vol` was carried to a backtest (NB29, as the reference). The DIAGNOSTIC verdict of this
notebook is unchanged.
"""
    if n in (29, 31):
        m = _m(29)
        g = m["gates"]["inverse_vol_q30"]
        return f"""## Idiot-gate audit, 2026-09-16 - verdict checked in place

Three of the gates in the table below were later found to be idiot gates (see the audit section
of [RESEARCH-RULES.md](RESEARCH-RULES.md)): gate 5's three-target form and its return clause,
gate 9's "beat every draw", and gate 3's concentration leg. **The REJECT of `inverse_vol_q30`
stands on standing gates**: it fails gate 6 (plateau) and gate 7 (sub-period sign) as well
(cell citations in the table), and a 30% exclusion is a `drop_30`-class spike. The twelve
signals "rejected without a backtest" at gate 5 are NOT BACKTESTED, not rejected; seven of them
clear the corrected stability-only gate 5 (NB28's audit note).
"""
    if n == 30:
        return """## Idiot-gate audit, 2026-09-16

The VACUOUS verdict stands: the folds were too short to select a signal. Gate 5's return clause
and three-target form, on which the fold screens relied, were later found to be idiot gates
(see the audit section of [RESEARCH-RULES.md](RESEARCH-RULES.md)); this notebook's conclusion
does not depend on them.
"""
    if n == 34:
        m = _m(34)
        sp = m["screen_post"]
        return f"""## Idiot-gate audit, 2026-09-16 - verdict corrected in place

The return clause of gate 5 is an idiot gate on this sample (see the audit section of
[RESEARCH-RULES.md](RESEARCH-RULES.md)): its standard error is 35x its margin and only a
foresight oracle can reach the bar it sets. It is now a DIAGNOSTIC. **Gate 5 is the stability
clause alone, and it PASSES for both signals** - forward volatility lower bounds
{sp["calm_score"]["lo_forward_vol"]:.3f} / {sp["inverse_vol"]["lo_forward_vol"]:.3f}, forward downside
{sp["calm_score"]["lo_forward_downside"]:.3f} / {sp["inverse_vol"]["lo_forward_downside"]:.3f} (cell 32). The
"gate 5 False" printed in cell 32 and cell 42 is the pre-registered rule's output and is
superseded. The return clause's reading - positive point estimate, unresolvable interval - is
unchanged and is reported as such.
"""
    if n in (35, 36):
        m = _m(35)
        T = m["track"]
        E = m["expensive_diagnostic"]
        G8 = m["gate_8"]
        I = m["inertness"]
        return f"""## Idiot-gate audit, 2026-09-16 - verdicts corrected in place

The protocol verdicts printed in this notebook - REJECT for both centres - rest on gates later
found to be idiot gates (see the audit section of [RESEARCH-RULES.md](RESEARCH-RULES.md)): gate
5's return clause (unresolvable on 66 decisions), gate 9's "beat every draw" (no power at a
+0.2 effect), gate 8 by one distinct vault and gate 4 by 0.008 of a luck ratio (strict
inequalities on noise-scale metrics). The printed tables are the pre-registered rule's output
and are left as they are. The corrected verdicts:

- **`measured_8`: NOT CONFIRMED (conditionally positive).** Passes every standing gate: 1, 2
  (mask retention {E["measured_8"]["lovo_retention"]:.3f}), 3 (volatility leg), 5 (stability clause), 6, 7;
  gate 8 within the new tolerance ({G8["measured_8"]["distinct_vaults"]:.0f} distinct vaults against 33). Its
  Sharpe gap to the anchor, {T["measured_8"]["cycle_sharpe"] - T["anchor"]["cycle_sharpe"]:+.3f}, is inside the
  operator's 0.25 indifference band and the tie-break against the anchor is unresolved (better
  on three diversification measures, level on one, worse on one). The null diagnostic - rank
  {E["measured_8"]["null_rank_of_centre"]} of 20 - cannot separate a +0.2 effect from a random exclusion, in
  either direction. Carrying it is the operator's decision on priors.
- **`calm_8`: NO EFFECT.** Sharpe {T["calm_8"]["cycle_sharpe"]:.3f} against the anchor's
  {T["anchor"]["cycle_sharpe"]:.3f}; basket changed on {I["calm_8"]["dates_with_a_different_basket"]} of 126 decisions;
  the guard removes the mechanism (H4 false). Not carried.

Nothing is SHORTLISTED under either reading, so the specification's status is unchanged.
"""
    raise KeyError(n)


def insert_audit(heading: str, n: int) -> str:
    """Insert the note after the paragraph that contains '**Based on:**'. Asserts the anchor
    exists and that the note is not already present."""
    note = _note(n)
    assert "Idiot-gate audit, 2026-09-16" not in heading, f"NB{n}: audit note already present"
    key = "**Based on:**"
    assert key in heading, f"NB{n}: no 'Based on' paragraph to anchor the audit note"
    start = heading.index(key)
    end = heading.index("\n\n", start)
    return heading[:end + 2] + note + "\n" + heading[end + 2:]
