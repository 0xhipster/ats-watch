"""
Second lane: poll the ATS platforms watch.py cannot read.

watch.py talks directly to Greenhouse, Lever, Ashby, Workable and
SmartRecruiters. This script covers everything else — Keka, Darwinbox,
PeopleStrong, RippleHire, SuccessFactors and 45+ more — by calling the
Apify actor memo23/career-site-ats-jobs-api.

    python3 watch_ats.py --dry-run   # print matches, no alerts, no state write
    python3 watch_ats.py --seed      # mark everything currently open as seen
    python3 watch_ats.py             # normal run

REQUIRES
--------
An Apify API token in the APIFY_TOKEN environment variable. Get one free at
apify.com -> Settings -> Integrations -> API token.

    Windows (this session only):  set APIFY_TOKEN=apify_api_xxxxx
    GitHub Actions:               add APIFY_TOKEN as a repository secret

INPUT
-----
Companies in companies.json that have a "board_url" field, written there by
census.py. If none have one, run census.py first.

CRITICAL: the actor is given the board URL, never the company name. Passing a
bare name makes it guess SmartRecruiters, find nothing, and report success —
a silent false negative. This was verified: "CleverTap" as a name returned
ats=smartrecruiters/jobsFound=0, while the real board URL returns real jobs.

COST
----
Roughly $0.03 per run plus $0.004 per job row returned. A run over ~15
companies costs a few cents. Free-plan runs are capped at 100 rows.
Use --dry-run freely; it still calls the API, so it still costs.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

import watch as fast_lane  # reuse matches() and notify_telegram()

CONFIG = "companies.json"
FILTERS = "filters.json"
STATE = "state/seen_ats.json"      # separate from watch.py's state, on purpose
DIGEST = "digest_ats.md"

ACTOR = "memo23~career-site-ats-jobs-api"
ENDPOINT = (f"https://api.apify.com/v2/acts/{ACTOR}"
            "/run-sync-get-dataset-items")
MAX_ROWS = 100        # free plan caps runs at 100 rows anyway
PER_COMPANY_CAP = 6  # so one big board cannot starve the rest of the list
TIMEOUT = 300         # the actor can take a couple of minutes


def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def call_apify(board_urls, token):
    """Call the actor. Returns a list of raw job rows. Raises on failure."""
    payload = json.dumps({
        "startUrls": board_urls,
        "maxItemsTotal": MAX_ROWS,
        # Per-company cap. Without this, one large board (a Workday tenant at
        # a big company) consumes the entire 100-row free-plan budget and
        # every other company silently returns nothing — which looks
        # identical to a broken board URL.
        "maxItems": PER_COMPANY_CAP,
        "includeDescription": False,
    }).encode()

    url = f"{ENDPOINT}?token={token}&format=json"
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def normalise(row):
    """Convert an actor row into watch.py's job schema."""
    org = row.get("org") or row.get("company") or "?"
    jid = row.get("globalId") or row.get("jobId") or row.get("jobUrl")
    loc = row.get("location") or ""
    if not loc:
        addr = row.get("address") or {}
        if isinstance(addr, dict):
            loc = ", ".join(x for x in [addr.get("city"), addr.get("country")] if x)
    return {
        "uid": f"apify:{row.get('ats', 'unknown')}:{org}:{jid}",
        "company": row.get("company") or org,
        "title": row.get("title", ""),
        "location": loc,
        "remote": row.get("isRemote"),
        "url": row.get("applyUrl") or row.get("jobUrl") or "",
        "posted": row.get("publishedAt", ""),
    }


def main():
    dry = "--dry-run" in sys.argv
    seed = "--seed" in sys.argv

    token = os.environ.get("APIFY_TOKEN")
    if not token:
        sys.exit("APIFY_TOKEN is not set. See the header of this file for how "
                 "to set it. Refusing to run rather than fail quietly.")

    companies = load_json(CONFIG, [])
    filters = load_json(FILTERS, None)
    if filters is None:
        sys.exit("filters.json missing")

    targets = [c for c in companies if c.get("board_url")]
    skipped = len(companies) - len(targets)

    if not targets:
        sys.exit("No companies have a board_url. Run census.py first — it "
                 "detects each company's ATS and records the board URL.")

    print(f"companies with a board URL : {len(targets)}")
    print(f"skipped (no board URL)     : {skipped}")
    for c in targets:
        print(f"  -> {c['name']:<18} {c.get('board_platform', '?'):<14} {c['board_url']}")

    board_urls = [c["board_url"] for c in targets]

    try:
        rows = call_apify(board_urls, token)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:400]
        sys.exit(f"Apify returned HTTP {e.code}. Body: {body}")
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        sys.exit(f"Could not reach Apify: {type(e).__name__}: {e}")
    except json.JSONDecodeError as e:
        sys.exit(f"Apify returned something that is not JSON: {e}")

    if not isinstance(rows, list):
        sys.exit(f"Expected a list of jobs from Apify, got {type(rows).__name__}. "
                 f"Not treating this as 'no jobs'.")

    jobs = [normalise(r) for r in rows]

    # Which requested companies produced nothing? Name them explicitly rather
    # than letting a silent zero look like success.
    seen_orgs = {(j["company"] or "").lower() for j in jobs}
    silent = [c["name"] for c in targets
              if c["name"].lower() not in seen_orgs
              and (c.get("board_url", "").lower().split(".")[0].split("//")[-1]
                   not in seen_orgs)]

    seen = set(load_json(STATE, {}).get("uids", []))
    hits = [j for j in jobs if fast_lane.matches(j, filters)]
    fresh = [j for j in hits if j["uid"] not in seen]

    print(f"\nrows returned : {len(jobs)}")
    print(f"matching      : {len(hits)}")
    print(f"new           : {len(fresh)}")
    if silent:
        print(f"\n! returned NOTHING ({len(silent)}): {', '.join(silent)}")
        print("  Check those board URLs by hand. A board that is genuinely")
        print("  empty and a board URL that is wrong look identical here.")

    for j in fresh:
        print(f"  NEW  {j['company']} | {j['title']} | {j['location']}")
        print(f"       {j['url']}")

    if dry:
        print("\n(dry run: no alerts sent, no state written)")
        return

    if fresh and not seed:
        fast_lane.notify_telegram(fresh)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        with open(DIGEST, "w", encoding="utf-8") as f:
            f.write(f"# New matches (second lane), {stamp}\n\n")
            for j in fresh:
                loc = j["location"] or "not stated"
                f.write(f"- **{j['company']}** | {j['title']} | {loc}\n  {j['url']}\n")

    seen.update(j["uid"] for j in jobs)
    os.makedirs("state", exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump({"updated": datetime.now(timezone.utc).isoformat(),
                   "uids": sorted(seen)}, f, indent=0)
        f.write("\n")
    print(f"\nstate written: {len(seen)} job ids tracked in {STATE}")


if __name__ == "__main__":
    main()
