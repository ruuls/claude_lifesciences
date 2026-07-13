"""Pure-Python BM25 (Okapi). No dependencies — stage-1 lexical retrieval."""
from __future__ import annotations
import math, re
from collections import Counter

_TOK = re.compile(r"[a-z0-9]+")
def tokenize(t: str) -> list[str]:
    return _TOK.findall((t or "").lower())


class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.docs = docs
        self.N = len(docs)
        self.k1, self.b = k1, b
        self.dl = [len(d) for d in docs]
        self.avgdl = (sum(self.dl) / self.N) if self.N else 0.0
        self.tf = [Counter(d) for d in docs]
        df = Counter()
        for d in self.tf:
            df.update(d.keys())
        self.idf = {t: math.log(1 + (self.N - n + 0.5) / (n + 0.5)) for t, n in df.items()}

    def score(self, query: list[str], idx: int) -> float:
        s = 0.0; tf = self.tf[idx]; dl = self.dl[idx]
        for t in query:
            if t not in tf:
                continue
            idf = self.idf.get(t, 0.0)
            num = tf[t] * (self.k1 + 1)
            den = tf[t] + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1))
            s += idf * num / den
        return s

    def topk(self, query: list[str], k: int, exclude: int | None = None) -> list[tuple[int, float]]:
        q = query
        scored = [(i, self.score(q, i)) for i in range(self.N) if i != exclude]
        scored.sort(key=lambda x: -x[1])
        return scored[:k]


def rrf(rank_lists: list[list[int]], k: int = 60) -> dict[int, float]:
    """Reciprocal Rank Fusion of several ranked id lists -> fused score per id."""
    fused: dict[int, float] = {}
    for rl in rank_lists:
        for rank, idx in enumerate(rl):
            fused[idx] = fused.get(idx, 0.0) + 1.0 / (k + rank + 1)
    return fused
