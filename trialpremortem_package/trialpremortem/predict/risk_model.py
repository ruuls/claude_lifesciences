"""L4 PREDICT — calibrated accrual-failure risk from neighbor outcomes.

score = (Σ wᵢ·yᵢ + α·p_base) / (Σ wᵢ + α),  wᵢ = exp(-dᵢ/τ)   [empirical-Bayes shrinkage]
Then isotonic calibration maps raw scores -> calibrated probabilities on a held fold.
"""
from __future__ import annotations
import numpy as np


def weighted_shrunk_score(neigh_y, neigh_dist, p_base, tau=0.5, alpha=3.0):
    """neigh_y: 0/1 outcomes; neigh_dist: distances (smaller=closer). Returns risk in [0,1]."""
    if len(neigh_y) == 0:
        return float(p_base)
    y = np.asarray(neigh_y, float); d = np.asarray(neigh_dist, float)
    w = np.exp(-d / max(tau, 1e-6))
    return float((np.sum(w * y) + alpha * p_base) / (np.sum(w) + alpha))


class IsotonicCalibrator:
    """Minimal PAV isotonic regression (monotone raw->calibrated)."""
    def __init__(self):
        self.x = None; self.y = None
    def fit(self, raw, y):
        order = np.argsort(raw)
        x = np.asarray(raw, float)[order]; g = np.asarray(y, float)[order]
        # Pool Adjacent Violators
        w = np.ones_like(g); vals = g.copy()
        i = 0; blocks = [[v, 1.0, xi] for v, xi in zip(vals, x)]
        # simple PAV
        stack = []
        for v, xi in zip(vals, x):
            stack.append([v, 1.0, xi])
            while len(stack) > 1 and stack[-2][0] > stack[-1][0]:
                v2, w2, x2 = stack.pop(); v1, w1, x1 = stack.pop()
                nv = (v1*w1 + v2*w2)/(w1+w2)
                stack.append([nv, w1+w2, x1])
        xs=[]; ys=[]
        for v, wt, xi in stack:
            xs.append(xi); ys.append(v)
        self.x = np.array(xs); self.y = np.array(ys)
        return self
    def predict(self, raw):
        return np.interp(np.asarray(raw, float), self.x, self.y)
