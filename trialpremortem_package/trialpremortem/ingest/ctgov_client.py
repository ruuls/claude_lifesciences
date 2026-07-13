"""L1 INGEST — ClinicalTrials.gov client.

Two endpoints (both verified live):
  V2  https://clinicaltrials.gov/api/v2/studies         -> search by status/condition
  INT https://clinicaltrials.gov/api/int/studies/{nct}/history         -> version list + changes
      https://clinicaltrials.gov/api/int/studies/{nct}/history/{idx}   -> full snapshot at version idx
      NOTE: history is 0-indexed. /history/0 == studyVersion 0 == the original draft (v0).
"""
from __future__ import annotations
import urllib.request, urllib.parse, json, time

V2  = "https://clinicaltrials.gov/api/v2"
INT = "https://clinicaltrials.gov/api/int"

_SEARCH_FIELDS = "NCTId,OverallStatus,WhyStopped,Phase,StudyType,StartDate,EnrollmentCount,Condition"


def _get(url: str, tries: int = 4, pause: float = 1.5):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json",
                                                       "User-Agent": "trialpremortem-research"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            last = e
            if i < tries - 1:
                time.sleep(pause * (i + 1))
    raise last


def search(status: str, cond: str, page_size: int = 100, max_pages: int = 3) -> list[dict]:
    """Search studies by overall status + condition. Returns flat dicts, paged."""
    out, token = [], None
    for _ in range(max_pages):
        params = {
            "filter.overallStatus": status,
            "query.cond": cond,
            "pageSize": min(page_size, 100),
            "fields": _SEARCH_FIELDS,
        }
        if token:
            params["pageToken"] = token
        d = _get(f"{V2}/studies?" + urllib.parse.urlencode(params))
        for s in d.get("studies", []):
            p = s["protocolSection"]
            idm, sm = p["identificationModule"], p["statusModule"]
            dm = p.get("designModule", {})
            cm = p.get("conditionsModule", {})
            sd = sm.get("startDateStruct", {}).get("date", "")
            out.append({
                "nct": idm["nctId"],
                "status": sm.get("overallStatus", ""),
                "why": sm.get("whyStopped", "") or "",
                "phase": ";".join(dm.get("phases", []) or []),
                "type": dm.get("studyType", ""),
                "condition": (cm.get("conditions", [""]) or [""])[0],
                "start_year": int(sd[:4]) if sd[:4].isdigit() else 0,
                "enrollment": (dm.get("enrollmentInfo", {}) or {}).get("count", 0) or 0,
            })
        token = d.get("nextPageToken")
        if not token:
            break
    return out


def get_history(nct: str) -> dict:
    """Full version history: {'changes':[{version,date,status,moduleLabels}], ...}."""
    return _get(f"{INT}/studies/{nct}/history")


def get_version(nct: str, idx: int = 0) -> dict:
    """Snapshot at history index idx. Asserts studyVersion matches idx (correctness guard)."""
    rec = _get(f"{INT}/studies/{nct}/history/{idx}")
    sv = rec.get("studyVersion")
    if sv is not None and sv != idx:
        raise ValueError(f"{nct}: /history/{idx} returned studyVersion={sv} (expected {idx})")
    return rec


def get_v0(nct: str) -> dict:
    """The original draft protocolSection (studyVersion==0), outcome-blind by construction."""
    rec = get_version(nct, 0)
    return rec.get("study", {}).get("protocolSection", {})


def trajectory(nct: str) -> list[dict]:
    """Amendment path: [{version,date,status,moduleLabels}] across all versions."""
    h = get_history(nct)
    return h.get("changes", [])
