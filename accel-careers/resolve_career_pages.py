"""
resolve_career_pages.py

Goal: for each of the 112 Accel India/SEA companies, find the URL that
ats-watch should actually POLL -- not just a marketing "careers" page.

For each company this script:
  1. Finds the company's real domain, via Accel's separate job-board site
     (jobs.accel.com), which is plain HTML (no JavaScript needed) and states
     the company's domain directly on each company's page.
  2. Finds a working /careers-style page on that domain.
  3. Scans that page (and any redirect target) for signatures of the 5
     ATS platforms ats-watch already supports (Greenhouse, Lever, Ashby,
     Workable, SmartRecruiters) -- if found, outputs the exact board URL
     ready to drop into ats-watch's company list.
  4. If instead it finds signatures of a non-standard platform (Keka,
     Darwinbox, PeopleStrong, SuccessFactors, Workday, PyjamaHR, etc.),
     it flags that too, since those go through the Apify actor path
     instead of the direct 5-platform poller.

Usage:
    pip install requests --break-system-packages   (if not already installed)
    python resolve_career_pages.py

Input:  accel_india_sea_companies.csv   (must be in the same folder)
Output: career_pages_resolved.csv

Key output columns:
  - detected_ats   : greenhouse / lever / ashby / workable / smartrecruiters
                      (ats-watch-ready) OR keka / darwinbox / etc. (needs
                      the Apify actor path) OR blank (needs manual look)
  - board_url      : the exact URL to feed into ats-watch / the Apify actor
  - career_page    : the marketing careers page we found it on (for context)
  - confidence     : high (ATS detected) / medium (career page found, no ATS
                      detected) / low (couldn't even find the company)
"""

import csv
import re
import time
import sys

try:
    import requests
except ImportError:
    print("The 'requests' library isn't installed. Run this first:")
    print("    pip install requests --break-system-packages")
    sys.exit(1)

INPUT_CSV = "accel_india_sea_companies.csv"
OUTPUT_CSV = "career_pages_resolved.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

CAREER_PATHS = ["/careers", "/careers/", "/jobs", "/jobs/", "/join-us", "/join-us/", "/about/careers"]

TIMEOUT = 12
PAUSE_BETWEEN_REQUESTS = 0.5  # be polite to the sites we're hitting

# The 5 platforms ats-watch directly polls. Pattern captures the board's
# exact URL so it can be dropped straight into ats-watch's company list.
ATS_PATTERNS = {
    "greenhouse": r"https?://(?:boards|job-boards)\.greenhouse\.io/[a-zA-Z0-9_-]+",
    "lever": r"https?://jobs\.lever\.co/[a-zA-Z0-9_-]+",
    "ashby": r"https?://jobs\.ashbyhq\.com/[a-zA-Z0-9_-]+",
    "workable": r"https?://apply\.workable\.com/[a-zA-Z0-9_-]+",
    "smartrecruiters": r"https?://jobs\.smartrecruiters\.com/[a-zA-Z0-9_-]+",
}

# Non-standard platforms -- these need the Apify actor (memo23/career-site-ats-jobs-api)
# path instead of ats-watch's direct poller. Pattern just needs to locate the domain;
# the exact board URL is whatever page we found it on.
NON_STANDARD_PATTERNS = {
    "keka": r"[a-zA-Z0-9_-]+\.keka\.com[^\s\"'<>]*",
    "darwinbox": r"[a-zA-Z0-9_-]+\.darwinbox\.(?:com|in)[^\s\"'<>]*",
    "peoplestrong": r"[a-zA-Z0-9_./-]*peoplestrong\.com[^\s\"'<>]*",
    "successfactors": r"[a-zA-Z0-9_./-]*successfactors\.com[^\s\"'<>]*",
    "workday": r"[a-zA-Z0-9_.-]+\.myworkdayjobs\.com[^\s\"'<>]*",
    "pyjamahr": r"[a-zA-Z0-9_./-]*pyjamahr\.com[^\s\"'<>]*",
    "rippling": r"ats\.rippling\.com[^\s\"'<>]*",
    "zoho_recruit": r"[a-zA-Z0-9_.-]+\.zohorecruit\.com[^\s\"'<>]*",
}


def slugify(name):
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def get(url):
    try:
        return requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
    except requests.RequestException:
        return None


def find_getro_page(name, accel_slug):
    """Try a handful of likely slugs on jobs.accel.com until one resolves."""
    base = slugify(name)
    candidates = []
    for s in [accel_slug, base, f"{base}-2", f"{accel_slug}-2"]:
        if s and s not in candidates:
            candidates.append(s)

    for slug in candidates:
        url = f"https://jobs.accel.com/companies/{slug}"
        r = get(url)
        time.sleep(PAUSE_BETWEEN_REQUESTS)
        if r is not None and r.status_code == 200 and "Accel Job Board" in r.text:
            return url, r.text
    return None, None


def extract_domain(name, html):
    """The company's domain appears right after its name, e.g. 'ACKOacko.com'."""
    for candidate_name in {name, re.sub(r"[^A-Za-z0-9]", "", name)}:
        pattern = re.escape(candidate_name) + r"([a-z0-9.-]+\.[a-z]{2,10})"
        m = re.search(pattern, html, re.IGNORECASE)
        if m:
            domain = m.group(1).strip(".").lower()
            if "." in domain and len(domain) < 60:
                return domain
    return None


def detect_ats(text):
    """Scan page text for a known ATS signature. Returns (platform, board_url) or (None, None)."""
    for platform, pattern in ATS_PATTERNS.items():
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return platform, m.group(0)
    for platform, pattern in NON_STANDARD_PATTERNS.items():
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            hit = m.group(0)
            if not hit.startswith("http"):
                hit = "https://" + hit
            return platform, hit
    return None, None


def find_career_page(domain):
    """Try common career paths on the domain. Returns (final_url, html) of the
    first one that resolves, following redirects (which may land directly on
    an ATS board)."""
    for scheme_prefix in ["https://", "https://www."]:
        root = f"{scheme_prefix}{domain}"
        for path in CAREER_PATHS:
            url = root + path
            r = get(url)
            time.sleep(PAUSE_BETWEEN_REQUESTS)
            if r is not None and r.status_code == 200:
                return r.url, r.text
    return None, None


def accel_slug_from_url(accel_profile_url):
    if not accel_profile_url:
        return ""
    return accel_profile_url.rstrip("/").rsplit("/", 1)[-1]


def main():
    try:
        with open(INPUT_CSV, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except FileNotFoundError:
        print(f"Couldn't find {INPUT_CSV}. Make sure it's in the same folder as this script.")
        sys.exit(1)

    results = []
    total = len(rows)
    for i, row in enumerate(rows, 1):
        name = row["name"].strip()
        accel_url = row.get("accel_profile_url", "").strip()
        note = row.get("notes", "").strip()
        accel_slug = accel_slug_from_url(accel_url)

        print(f"[{i}/{total}] {name} ...", end=" ", flush=True)

        # Step 1: find the real domain via jobs.accel.com
        getro_url, getro_html = find_getro_page(name, accel_slug)
        domain = extract_domain(name, getro_html) if getro_html else None

        # ATS signatures can sometimes appear right on the Getro page itself
        # (some companies list a direct "Apply" link there)
        detected_ats, board_url = detect_ats(getro_html) if getro_html else (None, None)

        career_page = ""
        if domain and not detected_ats:
            # Step 2: find a careers page on the company's own domain
            career_page, career_html = find_career_page(domain)
            if career_html:
                detected_ats, board_url = detect_ats(career_html)
                # the redirect target itself might already be the board
                if not detected_ats and career_page:
                    ats_from_url, url_hit = detect_ats(career_page)
                    if ats_from_url:
                        detected_ats, board_url = ats_from_url, url_hit

        if detected_ats:
            confidence = "high"
        elif career_page or domain:
            confidence = "medium"
        else:
            confidence = "low"

        print(f"{confidence}" + (f" ({detected_ats})" if detected_ats else ""))

        results.append({
            "name": name,
            "official_domain": domain or "",
            "detected_ats": detected_ats or "",
            "board_url": board_url or "",
            "career_page": career_page or "",
            "accel_job_board_url": getro_url or "",
            "accel_profile_url": accel_url,
            "confidence": confidence,
            "notes": note,
        })

    fieldnames = ["name", "official_domain", "detected_ats", "board_url", "career_page",
                  "accel_job_board_url", "accel_profile_url", "confidence", "notes"]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    ats_ready = sum(1 for r in results if r["detected_ats"] in
                     ("greenhouse", "lever", "ashby", "workable", "smartrecruiters"))
    non_standard = sum(1 for r in results if r["detected_ats"] and r["detected_ats"] not in
                        ("greenhouse", "lever", "ashby", "workable", "smartrecruiters"))
    medium = sum(1 for r in results if r["confidence"] == "medium")
    low = sum(1 for r in results if r["confidence"] == "low")
    print(f"\nDone. Wrote {OUTPUT_CSV}")
    print(f"  ats-watch-ready (Greenhouse/Lever/Ashby/Workable/SmartRecruiters): {ats_ready}")
    print(f"  non-standard ATS detected (Keka/Darwinbox/etc. -- Apify path): {non_standard}")
    print(f"  found a careers page but no ATS detected (medium confidence): {medium}")
    print(f"  couldn't find the company at all (needs manual look): {low}")


if __name__ == "__main__":
    main()
