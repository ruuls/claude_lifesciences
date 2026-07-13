"""Gradient-boosted decision trees (depth-limited) in numpy — captures feature
interactions the linear model misses, no sklearn dependency."""
from __future__ import annotations
import numpy as np


class Tree:
    def __init__(self, depth=2, min_leaf=10):
        self.depth = depth; self.min_leaf = min_leaf; self.node = None

    def _best_split(self, X, g, h):
        best = None; bestgain = 0.0; G, H = g.sum(), h.sum(); lam = 1.0
        for j in range(X.shape[1]):
            xs = X[:, j]; order = np.argsort(xs)
            xss = xs[order]; gs = g[order]; hs = h[order]
            Gl = np.cumsum(gs)[:-1]; Hl = np.cumsum(hs)[:-1]
            Gr = G - Gl; Hr = H - Hl
            gain = (Gl**2/(Hl+lam)) + (Gr**2/(Hr+lam)) - (G**2/(H+lam))
            valid = (xss[:-1] != xss[1:]); idxs = np.arange(len(xss)-1)
            valid &= (idxs+1 >= self.min_leaf) & (len(xss)-idxs-1 >= self.min_leaf)
            if valid.any():
                gi = np.argmax(np.where(valid, gain, -np.inf))
                if gain[gi] > bestgain:
                    bestgain = gain[gi]; best = (j, (xss[gi]+xss[gi+1])/2)
        return best

    def fit(self, X, g, h, depth=None):
        if depth is None: depth = self.depth
        lam = 1.0
        def build(idx, d):
            gg, hh = g[idx], h[idx]; leaf = -gg.sum()/(hh.sum()+lam)
            if d == 0 or len(idx) < 2*self.min_leaf: return {"leaf": leaf}
            sp = self._best_split(X[idx], gg, hh)
            if sp is None: return {"leaf": leaf}
            j, thr = sp; m = X[idx, j] <= thr
            if m.sum() < self.min_leaf or (~m).sum() < self.min_leaf: return {"leaf": leaf}
            return {"j": j, "thr": thr, "L": build(idx[m], d-1), "R": build(idx[~m], d-1)}
        self.node = build(np.arange(len(X)), depth); return self

    def _p1(self, x, n):
        while "leaf" not in n: n = n["L"] if x[n["j"]] <= n["thr"] else n["R"]
        return n["leaf"]

    def predict(self, X): return np.array([self._p1(x, self.node) for x in X])


class GBM:
    def __init__(self, n=60, lr=0.1, depth=2, min_leaf=12):
        self.n = n; self.lr = lr; self.depth = depth; self.min_leaf = min_leaf
        self.trees = []; self.base = 0.0

    def fit(self, X, y):
        p = np.clip(y.mean(), 1e-3, 1-1e-3); self.base = np.log(p/(1-p))
        F = np.full(len(y), self.base)
        for _ in range(self.n):
            pr = 1/(1+np.exp(-F)); g = pr - y; h = pr*(1-pr)
            t = Tree(self.depth, self.min_leaf).fit(X, g, h)
            F += self.lr*t.predict(X); self.trees.append(t)
        return self

    def predict(self, X):
        F = np.full(len(X), self.base)
        for t in self.trees: F += self.lr*t.predict(X)
        return 1/(1+np.exp(-F))
