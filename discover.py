"""
Slug prober.

Takes companies.json entries that have a domain but no resolved ATS, and
figures out which ATS they use and under what slug. Two methods, in order:

  1. Careers-page redirect trace. Fetch <domain>/careers and <domain>/jobs,
     follow redirects, and look for ATS URLs in the final URL or page HTML.
     This is the accurate method and catches vanity slugs.

  2. Endpoint probing. Guess slugs from the domain name and fire requests at
     every ATS posting endpoint. Whichever returns a valid board wins.

Writes resolved results back into companies.json. Run it weekly, or whenever
you add new companies.

    python3 discover.py            # resolve anything unresolved
    python3 discover.py --recheck  # re-resolve everything, including solved
"""

import json
import re
import sys
import time
import urllib.error
import urllib.request

import ats as ats_lib

CONFIG = "companies.json"

PATTERNS = [
    ("greenhouse", r"(?:boards|job-boards)\.greenhouse\.io/(?:embed/job_board\?for=)?([a-zA-Z0-9_-]+)"),
    ("lever", r"jobs\.(?:eu\.)?lever\.co/([a-zA-Z0-9_-]+)"),
    ("ashby", r"jobs\.ashbyhq\.com/([a-zA-Z0-9_.-]+)"),
    ("workable", r"(?:apply\.workable\.com/([a-zA-Z0-9_-]+)|([a-zA-Z0-9_-]+)\.workable\.com)"),
    ("smartrecruiters", r"jobs\.smartrecruiters\.com/([a-zA-Z0-9_-]+)"),
]

# ATS platforms we can detect but cannot poll via a public JSON API.
# Recorded so you know to check them manually rather than silently missing them.
UNSUPPORTED_PATTERNS = [
    ("darwinbox", r"([a-zA-Z0-9_-]+)\.darwinbox\.(?:in|com)"),
    ("keka", r"([a-zA-Z0-9_-]+)\.keka\.com"),
    ("zoho", r"([a-zA-Z0-9_-]+)\.zohorecruit\.(?:in|com)"),
    ("pyjamahr", r"([a-zA-Z0-9_-]+)\.pyjamahr\.com"),
    ("recruitee", r"([a-zA-Z0-9_-]+)\.recruitee\.com"),
]


def slug_candidates(domain):
    """Guess plausible ATS slugs from a domain like 'stader-labs.com'."""
    base = domain.split("//")[-1].split("/")[0]
    base = base.replace("www.", "")
    stem = base.split(".")[0]
    cands = [stem, stem.replace("-", ""), stem.replace("-", "_")]
    # multi-word domains: also try the full second-level name joined
    parts = base.split(".")
    if len(parts) > 2:
        cands.append("".join(parts[:-1]))

    # Case matters. Lever board slugs are case-sensitive: Sprinto's board is
    # at jobs.lever.co/Sprinto, and probing "sprinto" returns nothing. So for
    # every candidate, try lowercase AND capitalised. Previously this function
    # forced .lower() on everything, which silently made every capitalised
    # Lever board unreachable.
    seen, out = set(), []
    for c in cands:
        if not c:
            continue
        for variant in (c.lower(), c.capitalize()):
            if variant not in seen:
                seen.add(variant)
                out.append(variant)
    return out


def trace_careers_page(domain):
    """Method 1. Returns (ats, slug) or (unsupported_name, slug) or (None, None)."""
    base = domain.replace("www.", "")

    # Many companies host hiring on a career SUBDOMAIN, not a path:
    # jobs.chargebee.com, careers.zerodha.com. Checking only <domain>/careers
    # missed this entire category. Subdomains are tried first because when
    # they exist they are the canonical board.
    urls = [
        f"https://careers.{base}",
        f"https://jobs.{base}",
        f"https://{domain}/careers",
        f"https://{domain}/jobs",
        f"https://{domain}/careers/",
        f"https://{domain}/company/careers",
    ]

    for url in urls:
        try:
            html, final_url = ats_lib._get(url, expect_json=False)
        except Exception:
            continue
        haystack = final_url + "\n" + html[:400000]
        for name, pat in PATTERNS:
            m = re.search(pat, haystack)
            if m:
                slug = next((g for g in m.groups() if g), None)
                if slug:
                    return name, slug
        for name, pat in UNSUPPORTED_PATTERNS:
            m = re.search(pat, haystack)
            if m:
                return f"unsupported:{name}", m.group(1)
    return None, None


def probe_endpoints(domain):
    """Method 2. Returns (ats, slug) or (None, None).

    A board that returns 0 roles is NOT accepted as a match. An empty board
    is much more often an unrelated account that happens to share the guessed
    slug name than the real company with nothing open right now. Rejecting
    zero-role boards trades a small chance of missing a company that
    genuinely has zero open roles today for a much larger reduction in
    false-positive slug matches — worth it, since a wrong slug silently
    watches nothing forever, while a real company with zero roles today will
    resolve correctly the next time discover.py re-runs after they post one.
    """
    best = None
    zero_role_hits = []
    for slug in slug_candidates(domain):
        for platform in ats_lib.SUPPORTED:
            count = ats_lib.probe(platform, slug)
            if count is not None and count > 0:
                if best is None or count > best[2]:
                    best = (platform, slug, count)
            elif count == 0:
                zero_role_hits.append(f"{platform}/{slug}")
            time.sleep(0.15)
    if best:
        return best[0], best[1]
    if zero_role_hits:
        print(f"    (rejected zero-role match(es): {', '.join(zero_role_hits)})")
    return None, None


def resolve(company):
    domain = company if isinstance(company, str) else company.get("domain")
    if not domain:
        return None, None, "no-domain"
    ats, slug = trace_careers_page(domain)
    if ats:
        return ats, slug, "careers-page"
    ats, slug = probe_endpoints(domain)
    if ats:
        return ats, slug, "endpoint-probe"
    return None, None, "unresolved"


def main():
    recheck = "--recheck" in sys.argv
    with open(CONFIG) as f:
        companies = json.load(f)

    resolved = skipped = failed = 0
    for c in companies:
        if c.get("ats") and not recheck:
            skipped += 1
            continue
        ats, slug, method = resolve(c["domain"])
        if ats:
            c["ats"], c["slug"], c["method"] = ats, slug, method
            status = "OK " if not ats.startswith("unsupported") else "MAN"
            print(f"  {status} {c['name']:<24} {ats}/{slug}  ({method})")
            resolved += 1
        else:
            # Clear any stale ats/slug from a prior bad resolution. Do NOT
            # reuse c.get("ats") here — that was the bug: it silently kept
            # an old false-positive slug on disk even though this run
            # correctly determined the company is unresolved.
            c["ats"] = None
            c["slug"] = None
            c["method"] = "unresolved"
            print(f"  --  {c['name']:<24} no public board found")
            failed += 1

    with open(CONFIG, "w") as f:
        json.dump(companies, f, indent=2)
        f.write("\n")

    print(f"\nresolved {resolved}, already known {skipped}, unresolved {failed}")
    print("Entries marked 'unsupported:<platform>' have no public JSON API.")
    print("Check those career pages manually or add an HTML parser later.")


if __name__ == "__main__":
    main()
