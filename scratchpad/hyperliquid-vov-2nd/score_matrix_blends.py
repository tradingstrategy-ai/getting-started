"""Compose vault scores across clip profiles without losing their nonlinear maps."""

import hashlib
import json
from pathlib import Path

import numpy as np


def register_score_blend(panel, components):
    """Register a content-addressed mixture of normalised component scores.

    :param components:
        Dictionaries with :py:attr:`mass`, :py:attr:`weights` and :py:attr:`profile`.
        Every component uses the same missing flag and Calmar clip at evaluation.
    """
    recipe = []
    for component in components:
        mass = float(component["mass"])
        if mass == 0:
            continue
        w = np.asarray(component["weights"], dtype=float)
        assert mass > 0 and (w >= 0).all() and abs(w.sum() - 1) < 1e-12
        assert component["profile"] in ("requested", "legacy")
        recipe.append({"mass": mass, "weights": list(w), "profile": component["profile"]})
    assert abs(sum(c["mass"] for c in recipe) - 1) < 1e-12
    digest = hashlib.sha256(Path(__file__).read_bytes() + json.dumps(recipe, sort_keys=True).encode()).hexdigest()[:12]
    profile = f"mixed_{digest}"
    if not hasattr(panel, "score_blend_recipes"):
        panel.score_blend_recipes = {}
        original = panel.score_values

        def score_values(weights, calmar_cap=5.0, missing=False, profile="requested"):
            if profile not in panel.score_blend_recipes:
                assert profile in ("requested", "legacy"), f"Unregistered score profile: {profile}"
                return original(weights, calmar_cap, missing=missing, profile=profile)
            current = panel.score_blend_recipes[profile]
            merged = sum(c["mass"] * np.asarray(c["weights"]) for c in current)
            assert np.allclose(weights, merged, rtol=0, atol=1e-12)
            values = np.zeros(panel.raw.shape[:2])
            for c in current:
                values += c["mass"] * original(c["weights"], calmar_cap, missing=missing, profile=c["profile"])
            return values

        panel.score_values = score_values
    panel.score_blend_recipes[profile] = recipe
    weights = sum(c["mass"] * np.asarray(c["weights"]) for c in recipe)
    return weights, profile


def truncate_score_blend(panel, profile, active):
    """Discard cells across all profiles and renormalise retained coefficient mass."""
    retained = []
    for c in panel.score_blend_recipes[profile]:
        w = np.asarray(c["weights"]).copy()
        w[[i for i in range(len(w)) if i not in active]] = 0
        mass = float(w.sum())
        if mass > 0:
            retained.append({"weights": w / mass, "mass": c["mass"] * mass, "profile": c["profile"]})
    total = sum(c["mass"] for c in retained)
    assert total > 0
    for c in retained:
        c["mass"] /= total
    return register_score_blend(panel, retained)
