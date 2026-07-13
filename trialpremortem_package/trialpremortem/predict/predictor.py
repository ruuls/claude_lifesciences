"""Live predictor — the ML risk engine the agent calls as a tool.

score_protocol(features) -> {risk, percentile_flags, drivers}
This is config C1 packaged for inference. The agentic red-team (C2) calls this,
so the shipped product is agentic in interface and ML-grade in accuracy.
"""
from __future__ import annotations
import pickle, numpy as np


class RiskEngine:
    def __init__(self, model_path):
        with open(model_path, "rb") as f:
            st = pickle.load(f)
        self.gbm = st["gbm"]
        self.feat_names = st["feat_names"]
        self.peer_lk = st["peer_lk"]
        self.cond_lk = st["cond_lk"]
        self.g_excl = st["g_excl_med"]; self.g_incl = st["g_incl_med"]; self.g_enroll = st["g_enroll_med"]

    def _peer(self, cond, phase):
        cond = (cond or "").lower()[:15]; phase = (phase or "NA").split(";")[0]
        k = str((cond, phase))
        if k in self.peer_lk and self.peer_lk[k].get("n", 0) >= 8:
            r = self.peer_lk[k]; return r["excl_med"], r["incl_med"], r["enroll_med"]
        if cond in self.cond_lk:
            r = self.cond_lk[cond]; return r["excl_med"], r["incl_med"], r["enroll_med"]
        return self.g_excl, self.g_incl, self.g_enroll

    def featurize(self, p: dict) -> tuple[np.ndarray, dict]:
        """p: {n_excl,n_incl,age_span,enroll_target,n_arms,cond,phase,competition?}"""
        em, im, enm = self._peer(p.get("cond",""), p.get("phase",""))
        enroll = float(p.get("enroll_target", 0) or 0)
        row = [
            p.get("n_excl", 0), p.get("n_incl", 0), p.get("age_span", 100),
            np.log1p(enroll), p.get("n_arms", 1),
            p.get("n_excl", 0) - em, p.get("n_incl", 0) - im,
            np.log1p(enroll) - np.log1p(enm), p.get("competition", 0),
        ]
        peer_info = {"excl_median": em, "incl_median": im, "enroll_median": enm,
                     "excl_vs_peer": p.get("n_excl",0)-em, "enroll_vs_peer_ratio": enroll/max(enm,1)}
        return np.nan_to_num(np.array([row], float), nan=0.0), peer_info

    def score(self, p: dict) -> dict:
        X, peer = self.featurize(p)
        risk = float(self.gbm.predict(X)[0])
        from .whatif import plain_driver
        drivers = plain_driver(peer, p)
        return {"risk_score": round(risk, 3), "peer_comparison": peer, "top_drivers": drivers}
