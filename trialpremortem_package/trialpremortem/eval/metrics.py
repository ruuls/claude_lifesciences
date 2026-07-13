"""L5a — ROC/AUC, PR/AP, calibration, all in numpy."""
from __future__ import annotations
import numpy as np


def roc_curve(y, s):
    y = np.asarray(y); s = np.asarray(s, float)
    order = np.argsort(-s); y = y[order]; s = s[order]
    P = y.sum(); Nn = len(y) - P
    tps = np.cumsum(y); fps = np.cumsum(1 - y)
    tpr = tps / (P or 1); fpr = fps / (Nn or 1)
    tpr = np.concatenate([[0], tpr]); fpr = np.concatenate([[0], fpr])
    return fpr, tpr


def auc(x, y):
    return float(np.trapezoid(y, x))


def roc_auc(y, s):
    fpr, tpr = roc_curve(y, s); return auc(fpr, tpr)


def pr_curve(y, s):
    y = np.asarray(y); s = np.asarray(s, float)
    order = np.argsort(-s); y = y[order]
    tps = np.cumsum(y); fps = np.cumsum(1 - y)
    prec = tps / np.maximum(tps + fps, 1); rec = tps / (y.sum() or 1)
    return rec, prec


def average_precision(y, s):
    rec, prec = pr_curve(y, s)
    rec = np.concatenate([[0], rec]); prec = np.concatenate([[1], prec])
    return float(np.sum(np.diff(rec) * prec[1:]))


def calibration_bins(y, s, nbins=10):
    y = np.asarray(y); s = np.asarray(s, float)
    edges = np.linspace(0, 1, nbins + 1)
    xs=[]; ys=[]; ns=[]
    for i in range(nbins):
        m = (s >= edges[i]) & (s < edges[i+1] if i < nbins-1 else s <= edges[i+1])
        if m.sum() == 0: continue
        xs.append(s[m].mean()); ys.append(y[m].mean()); ns.append(int(m.sum()))
    return np.array(xs), np.array(ys), np.array(ns)


def flag_rate(s, y, thresh):
    """Return (flag rate on positives, flag rate on negatives) at threshold."""
    s = np.asarray(s, float); y = np.asarray(y)
    pos = s[y == 1] >= thresh; neg = s[y == 0] >= thresh
    return float(pos.mean() if len(pos) else 0), float(neg.mean() if len(neg) else 0)


def auc_rank(y, s):
    """Wilcoxon-Mann-Whitney AUC — correct handling of tied scores (unlike trapezoid on a
    tie-ordered ROC). AUC = P(score_pos > score_neg) + 0.5*P(tie)."""
    y = np.asarray(y); s = np.asarray(s, float)
    pos = s[y == 1]; neg = s[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return 0.5
    # rank-based: average ranks handle ties
    order = np.argsort(s, kind="mergesort")
    ranks = np.empty(len(s), float)
    sr = s[order]
    i = 0
    while i < len(sr):
        j = i
        while j + 1 < len(sr) and sr[j + 1] == sr[i]:
            j += 1
        avg = (i + j) / 2.0 + 1.0  # 1-based average rank
        ranks[order[i:j + 1]] = avg
        i = j + 1
    R_pos = ranks[y == 1].sum()
    n1 = len(pos); n0 = len(neg)
    U = R_pos - n1 * (n1 + 1) / 2.0
    return float(U / (n1 * n0))
