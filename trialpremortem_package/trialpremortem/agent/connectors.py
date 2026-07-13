"""Live biomedical connector tools (L1) — thin wrappers over MCP servers.

All method names + params below were verified live against the connected servers
(each returned real data in a probe call before this file was written):
  chembl.compound_search(name=) -> compounds[].molecule_chembl_id
  chembl.get_mechanism(molecule_chembl_id=) -> mechanisms[]
  pubmed.search_articles(query=,max_results=) -> pmids ; get_article_metadata(pmids=) -> titles
  clinical-trials.search_trials(condition=,page_size=) -> items[{nct_id,title,status,phase}]
  clinical-genomics.open_targets_drug(chembl_id=) -> mechanism+target+maximumClinicalStage
  drug-regulatory.search_drug_applications(active_ingredient=) -> records[{application_number,sponsor_name,products}]

Runs in the `repl` kernel (host.mcp only available there). Each wrapper returns a
compact JSON-serializable dict and never raises — {"unavailable": reason} on failure
so the agent loop degrades gracefully (brief's degradation rule).
"""
from __future__ import annotations


import time

_CACHE = {}  # deterministic lookups (drug_mechanism, target_disease) shared across investigators


def _mcp(host, server, method, **kw):
    """Call host.mcp but RAISE on error-string returns so _safe's retry engages.
    host.mcp returns a plain string (e.g. 'exceeded 30s server timeout') on failure
    rather than raising, which would otherwise slip past a try/except as a bad dict."""
    r = host.mcp(server, method, **kw)
    if not isinstance(r, dict):
        raise RuntimeError(f"{server}.{method} non-dict return: {str(r)[:120]}")
    return r


def _safe(fn, retries=3):
    last = None
    for i in range(retries + 1):
        try:
            return fn()
        except Exception as e:
            last = str(e)[:160]
            time.sleep(2.0 * (i + 1))  # ChEMBL is slow / rate-limits; back off and retry
    return {"unavailable": last}


def drug_mechanism(host, drug_name):
    """ChEMBL: drug name -> chembl_id -> mechanism of action + target (cached)."""
    ck = ("drug_mechanism", drug_name.lower())
    if ck in _CACHE:
        return _CACHE[ck]
    def go():
        c = _mcp(host, "chembl", "compound_search", name=drug_name, limit=3)
        comps = c.get("compounds", [])
        if not comps:
            return {"drug": drug_name, "found": False}
        cid = comps[0]["molecule_chembl_id"]
        m = _mcp(host, "chembl", "get_mechanism", molecule_chembl_id=cid, limit=5)
        moa = [{"mechanism": x.get("mechanism_of_action"), "action": x.get("action_type"),
                "target_chembl_id": x.get("target_chembl_id")}
               for x in m.get("mechanisms", [])]
        return {"drug": drug_name, "chembl_id": cid,
                "pref_name": comps[0].get("pref_name"), "mechanisms": moa}
    out = _safe(go)
    if "chembl_id" in out:
        _CACHE[ck] = out
    return out


def target_disease(host, chembl_id):
    """Open Targets (clinical-genomics): drug -> mechanism, target gene, max clinical stage.
    Second independent source confirming the drug's mechanism/target."""
    ck = ("target_disease", chembl_id)
    if ck in _CACHE:
        return _CACHE[ck]
    def go():
        r = _mcp(host, "clinical-genomics", "open_targets_drug", chembl_id=chembl_id)
        moa = r.get("mechanismsOfAction", {}).get("rows", [])
        return {"chembl_id": chembl_id, "name": r.get("name"),
                "max_clinical_stage": r.get("maximumClinicalStage"),
                "mechanisms": [{"mechanism": x.get("mechanismOfAction"),
                                "action": x.get("actionType"),
                                "targets": [t.get("approvedSymbol") for t in x.get("targets", [])]}
                               for x in moa]}
    out = _safe(go)
    if out.get("mechanisms"):
        _CACHE[ck] = out
    return out


def literature(host, query, k=5):
    """PubMed: search -> pmids -> titles. Grounds endpoint-timing / MoA-onset claims."""
    def go():
        s = _mcp(host, "pubmed", "search_articles", query=query, max_results=k)
        pmids = s.get("pmids", [])[:k]
        if not pmids:
            return {"query": query, "n": 0, "articles": []}
        meta = _mcp(host, "pubmed", "get_article_metadata", pmids=pmids)
        arts = meta.get("articles", meta.get("results", []))
        out = []
        for i, a in enumerate(arts):
            # pmid lives in identifiers.pmid (metadata doesn't echo a top-level pmid)
            ids = a.get("identifiers", {}) or {}
            pmid = ids.get("pmid") or ids.get("pubmed") or (pmids[i] if i < len(pmids) else None)
            pd = a.get("publication_date")
            year = pd.get("year") if isinstance(pd, dict) else (str(pd)[:4] if pd else None)
            out.append({"pmid": pmid,
                        "title": (a.get("title") or "")[:150],
                        "abstract": (a.get("abstract") or "")[:400],
                        "year": year})
        return {"query": query, "n": len(out), "total_hits": s.get("total_count"),
                "articles": out}
    return _safe(go)


def similar_trials(host, condition, phase="", k=6):
    """ClinicalTrials.gov: real analogous trials + status (whyStopped when terminated)."""
    def go():
        kw = {"condition": condition, "page_size": k}
        if phase:
            kw["phase"] = phase
        r = _mcp(host, "clinical-trials", "search_trials", **kw)
        items = r.get("items", r.get("studies", []))
        return {"condition": condition, "n": len(items),
                "trials": [{"nct": s.get("nct_id") or s.get("nctId"),
                            "title": (s.get("title") or "")[:100],
                            "status": s.get("status"),
                            "phase": s.get("phase"),
                            "why_stopped": s.get("why_stopped") or s.get("whyStopped")}
                           for s in items[:k]]}
    return _safe(go)


def regulatory_precedent(host, active_ingredient, k=5):
    """Drugs@FDA: approved drug applications for an active ingredient (sponsor + products)."""
    def go():
        r = _mcp(host, "drug-regulatory", "search_drug_applications",
                     active_ingredient=active_ingredient, limit=k)
        recs = r.get("records", [])
        out = []
        for a in recs[:k]:
            prods = a.get("products", [])
            out.append({"application": a.get("application_number"),
                        "sponsor": a.get("sponsor_name"),
                        "brand": prods[0].get("brand_name") if prods else None,
                        "status": prods[0].get("marketing_status") if prods else None})
        return {"active_ingredient": active_ingredient, "total": r.get("total"),
                "n": len(out), "applications": out}
    return _safe(go)
