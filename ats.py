"""
ATS client layer.

Every function here talks only to public, unauthenticated posting endpoints.
Nothing in this file requires an API key or a login.

Normalized job schema returned by fetch_jobs():
    {
        "uid":      stable unique id, "<ats>:<slug>:<job_id>"
        "company":  display name
        "title":    job title
        "location": free-text location string ("" if unknown)
        "remote":   bool or None
        "url":      direct ATS apply/posting URL
        "posted":   ISO timestamp string or ""
    }
"""

import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (compatible; personal-job-watcher/1.0)"
TIMEOUT = 20

SUPPORTED = ["greenhouse", "lever", "ashby", "workable", "smartrecruiters"]


def _get(url, expect_json=True):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json, text/html"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        final_url = resp.geturl()
    if expect_json:
        return json.loads(raw), final_url
    return raw, final_url


def _hashed(*parts):
    return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:12]


# ---------------------------------------------------------------- endpoints

def board_url(ats, slug):
    if ats == "greenhouse":
        return f"https://api.greenhouse.io/v1/boards/{slug}/jobs?content=false"
    if ats == "lever":
        return f"https://api.lever.co/v0/postings/{slug}?mode=json"
    if ats == "ashby":
        return f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
    if ats == "workable":
        return f"https://www.workable.com/api/accounts/{slug}?details=true"
    if ats == "smartrecruiters":
        return f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100"
    raise ValueError(f"unknown ats: {ats}")


# -------------------------------------------------------------- normalizers

def _norm_greenhouse(data, slug, company):
    out = []
    for j in data.get("jobs", []):
        out.append({
            "uid": f"greenhouse:{slug}:{j.get('id')}",
            "company": company,
            "title": j.get("title", ""),
            "location": (j.get("location") or {}).get("name", ""),
            "remote": None,
            "url": j.get("absolute_url", ""),
            "posted": j.get("first_published") or j.get("updated_at") or "",
        })
    return out


def _norm_lever(data, slug, company):
    out = []
    for j in data if isinstance(data, list) else []:
        cats = j.get("categories") or {}
        out.append({
            "uid": f"lever:{slug}:{j.get('id')}",
            "company": company,
            "title": j.get("text", ""),
            "location": cats.get("location") or "",
            "remote": (j.get("workplaceType") == "remote") if j.get("workplaceType") else None,
            "url": j.get("hostedUrl") or j.get("applyUrl") or "",
            "posted": str(j.get("createdAt", "")),
        })
    return out


def _norm_ashby(data, slug, company):
    out = []
    for j in data.get("jobs", []):
        url = j.get("jobUrl") or j.get("applyUrl") or ""
        jid = j.get("id") or _hashed(url, j.get("title"))
        out.append({
            "uid": f"ashby:{slug}:{jid}",
            "company": company,
            "title": j.get("title", ""),
            "location": j.get("location") or "",
            "remote": j.get("isRemote"),
            "url": url,
            "posted": j.get("publishedAt", ""),
        })
    return out


def _norm_workable(data, slug, company):
    out = []
    for j in data.get("jobs", []):
        loc = j.get("location")
        if isinstance(loc, dict):
            loc = ", ".join(x for x in [loc.get("city"), loc.get("country")] if x)
        out.append({
            "uid": f"workable:{slug}:{j.get('shortcode')}",
            "company": company,
            "title": j.get("title", ""),
            "location": loc or "",
            "remote": j.get("telecommuting"),
            "url": j.get("url") or f"https://apply.workable.com/j/{j.get('shortcode')}",
            "posted": j.get("published_on") or j.get("created_at") or "",
        })
    return out


def _norm_smartrecruiters(data, slug, company):
    out = []
    for j in data.get("content", []):
        loc = j.get("location") or {}
        parts = [loc.get("city"), loc.get("region"), loc.get("country")]
        out.append({
            "uid": f"smartrecruiters:{slug}:{j.get('id')}",
            "company": company,
            "title": j.get("name", ""),
            "location": ", ".join(p for p in parts if p),
            "remote": loc.get("remote"),
            "url": f"https://jobs.smartrecruiters.com/{slug}/{j.get('id')}",
            "posted": j.get("releasedDate", ""),
        })
    return out


_NORMALIZERS = {
    "greenhouse": _norm_greenhouse,
    "lever": _norm_lever,
    "ashby": _norm_ashby,
    "workable": _norm_workable,
    "smartrecruiters": _norm_smartrecruiters,
}


def fetch_jobs(ats, slug, company):
    """Fetch and normalize all open roles for one company. Raises on network error."""
    data, _ = _get(board_url(ats, slug))
    return _NORMALIZERS[ats](data, slug, company)


def probe(ats, slug):
    """Return job count if this ats/slug pair is a live public board, else None.

    A count of 0 is returned as 0, not None: the account name exists but has
    no open roles. Callers must decide whether to accept a zero-role board —
    do not treat 0 as equivalent to a resolved, watchable company. An empty
    board is far more often a same-name unrelated account than the real
    company with no jobs open right now.
    """
    try:
        data, _ = _get(board_url(ats, slug))
    except (urllib.error.HTTPError, urllib.error.URLError,
            urllib.error.ContentTooShortError, json.JSONDecodeError,
            TimeoutError, ConnectionError, UnicodeDecodeError) as e:
        return None
    if ats == "lever":
        return len(data) if isinstance(data, list) else None
    if ats == "greenhouse":
        return len(data.get("jobs", [])) if isinstance(data, dict) and "jobs" in data else None
    if ats == "ashby":
        return len(data.get("jobs", [])) if isinstance(data, dict) and "jobs" in data else None
    if ats == "workable":
        return len(data.get("jobs", [])) if isinstance(data, dict) and "jobs" in data else None
    if ats == "smartrecruiters":
        return data.get("totalFound") if isinstance(data, dict) and "content" in data else None
    return None
