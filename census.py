"""
ATS census.

Purpose: for every company that failed to resolve, find out WHICH hiring
platform they actually use. Not to watch them — to count them, so the
decision about which platform to support next is made on evidence rather
than a guess.

This does not need JavaScript rendering. An ATS almost always leaves its
fingerprint in the raw HTML: a script source, a stylesheet link, a redirect
target, or the URL structure of the careers page itself.

    python3 census.py            # census the unresolved companies
    python3 census.py --all      # census every company, resolved or not

Output is a per-company line plus a ranked tally at the end. The tally is
the point: "9 companies on Keka" means building Keka support unlocks 9 at
once, plus every future Indian startup you add.
"""

import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter

CONFIG = "companies.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " \
     "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
TIMEOUT = 15

# Ordered most-specific first. Each entry: (platform, regex, has_public_api)
# has_public_api records whether a documented unauthenticated JSON board
# endpoint exists — that is what decides whether support is cheap or hard.
# (platform, regex, has_public_api, board_url_template)
# The regex CAPTURES the tenant where possible, and the template turns it into
# the real ATS board URL. This matters: the Apify actor needs the actual board
# URL (awfis.keka.com/careers), not the company's marketing careers page
# (awfis.com) — the latter silently returns zero rows.
SIGNATURES = [
    ("greenhouse",      r"(?:boards|job-boards)\.greenhouse\.io/([a-zA-Z0-9_-]+)", True,
     "https://boards.greenhouse.io/{t}"),
    ("lever",           r"jobs\.(?:eu\.)?lever\.co/([a-zA-Z0-9_-]+)", True,
     "https://jobs.lever.co/{t}"),
    ("ashby",           r"jobs\.ashbyhq\.com/([a-zA-Z0-9_.-]+)", True,
     "https://jobs.ashbyhq.com/{t}"),
    ("workable",        r"apply\.workable\.com/([a-zA-Z0-9_-]+)", True,
     "https://apply.workable.com/{t}"),
    ("smartrecruiters", r"(?:jobs|careers)\.smartrecruiters\.com/([a-zA-Z0-9_-]+)", True,
     "https://careers.smartrecruiters.com/{t}"),

    ("keka",            r"([a-zA-Z0-9-]+)\.keka\.com", False,
     "https://{t}.keka.com/careers"),
    ("darwinbox",       r"([a-zA-Z0-9-]+)\.darwinbox\.(?:in|com)", False,
     "https://{t}.darwinbox.in"),
    ("freshteam",       r"([a-zA-Z0-9-]+)\.freshteam\.com", False,
     "https://{t}.freshteam.com"),
    ("breezy",          r"([a-zA-Z0-9-]+)\.breezy\.hr", False,
     "https://{t}.breezy.hr"),
    ("recruitee",       r"([a-zA-Z0-9-]+)\.recruitee\.com", False,
     "https://{t}.recruitee.com"),
    ("bamboohr",        r"([a-zA-Z0-9-]+)\.bamboohr\.com", False,
     "https://{t}.bamboohr.com"),
    ("teamtailor",      r"([a-zA-Z0-9-]+)\.teamtailor\.com", False,
     "https://{t}.teamtailor.com"),
    ("personio",        r"([a-zA-Z0-9-]+)\.jobs\.personio\.(?:com|de)", False,
     "https://{t}.jobs.personio.com"),
    ("peoplestrong",    r"([a-zA-Z0-9-]+)\.peoplestrong\.com", False,
     "https://{t}.peoplestrong.com"),
    ("ripplehire",      r"([a-zA-Z0-9-]+)\.ripplehire\.com", False,
     "https://{t}.ripplehire.com"),
    ("zoho_recruit",    r"([a-zA-Z0-9-]+)\.zohorecruit\.(?:in|com)", False,
     "https://{t}.zohorecruit.in/jobs/Careers"),
    ("eightfold",       r"([a-zA-Z0-9-]+)\.eightfold\.ai", False,
     "https://{t}.eightfold.ai"),
    ("workday",         r"([a-zA-Z0-9-]+\.wd\d+\.myworkdayjobs\.com/[a-zA-Z0-9_-]+)", False,
     "https://{t}"),
    ("icims",           r"(careers-[a-zA-Z0-9-]+\.icims\.com)", False,
     "https://{t}"),
    ("pyjamahr",        r"(app\.pyjamahr\.com/careers\?company=[a-zA-Z0-9_&=%-]+)", False,
     "https://{t}"),
    ("successfactors",  r"(jobs\.[a-zA-Z0-9-]+\.com)/content/", False,
     "https://{t}"),
    ("taleo",           r"([a-zA-Z0-9-]+\.taleo\.net/careersection/[0-9a-z]+)", False,
     "https://{t}/jobsearch.ftl"),
]


def fetch(url):
    """Return (text, final_url) or raise. No bare except — caller sees the error."""
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        raw = resp.read(600_000).decode("utf-8", errors="replace")
        return raw, resp.geturl()


def candidate_urls(domain):
    base = domain.replace("www.", "")
    return [
        f"https://careers.{base}",
        f"https://jobs.{base}",
        f"https://{base}/careers",
        f"https://{base}/jobs",
        f"https://{base}/company/careers",
        f"https://{base}/about/careers",
    ]


def identify(domain):
    """Return (platform, has_api, evidence_url, tried_log)."""
    tried = []
    for url in candidate_urls(domain):
        try:
            html, final_url = fetch(url)
        except urllib.error.HTTPError as e:
            tried.append(f"{url} -> HTTP {e.code}")
            continue
        except (urllib.error.URLError, TimeoutError, ConnectionError,
                UnicodeDecodeError, OSError) as e:
            tried.append(f"{url} -> {type(e).__name__}")
            continue

        haystack = final_url + "\n" + html
        for platform, pattern, has_api, template in SIGNATURES:
            m = re.search(pattern, haystack, re.I)
            if m:
                tenant = m.group(1) if m.groups() else None
                if not tenant:
                    tried.append(f"{url} -> matched {platform} but no tenant captured")
                    continue
                board = template.format(t=tenant)
                return platform, has_api, board, tried
        tried.append(f"{url} -> 200, no signature matched")
    return None, None, None, tried


def main():
    do_all = "--all" in sys.argv
    verbose = "-v" in sys.argv or "--verbose" in sys.argv
    companies = json.load(open(CONFIG))

    targets = [c for c in companies
               if do_all or not c.get("ats") or str(c.get("ats")).startswith("unsupported")]

    print(f"Censusing {len(targets)} of {len(companies)} companies.")
    print("Looking for which ATS each one actually uses.\n")
    print(f"{'COMPANY':<18} {'PLATFORM':<18} {'API?':<6} EVIDENCE")
    print("-" * 96)

    tally = Counter()
    api_status = {}
    unknown = []

    for c in targets:
        name, domain = c.get("name", "?"), c.get("domain")
        if not domain:
            print(f"{name:<18} {'(no domain)':<18}")
            continue

        platform, has_api, evidence, tried = identify(domain)

        if platform:
            tally[platform] += 1
            api_status[platform] = has_api
            flag = "yes" if has_api else "NO"
            print(f"{name:<18} {platform:<18} {flag:<6} {(evidence or '')[:52]}")
            # Persist so watch_ats.py can poll these via Apify. The board URL
            # is the important part: the Apify actor MUST be given the real
            # board URL, never a company name, or it silently guesses
            # SmartRecruiters and returns zero rows.
            c["board_platform"] = platform
            c["board_url"] = evidence
        else:
            unknown.append(name)
            print(f"{name:<18} {'unknown':<18} {'-':<6} no signature on any careers URL")
            if verbose:
                for t in tried:
                    print(f"{'':<18}   . {t}")
        time.sleep(0.3)

    print("-" * 96)
    print(f"\nidentified : {sum(tally.values())}")
    print(f"unknown    : {len(unknown)}")
    if unknown:
        print(f"             {', '.join(unknown)}")

    print("\n=== PLATFORM TALLY (the decision table) ===\n")
    print(f"{'PLATFORM':<18} {'COMPANIES':<11} {'PUBLIC JSON API?':<18} VERDICT")
    print("-" * 78)
    for platform, count in tally.most_common():
        has_api = api_status[platform]
        if has_api:
            verdict = "already supported - investigate why probe failed"
        elif count >= 4:
            verdict = f"WORTH BUILDING - unlocks {count}"
        else:
            verdict = "low payoff for effort"
        print(f"{platform:<18} {count:<11} {'yes' if has_api else 'no':<18} {verdict}")

    print("\nRead the tally, not the per-company lines. A platform with 4+")
    print("companies is worth building support for, because it also covers")
    print("future companies you add. Anything with 1-2 is not.")
    print("\nRe-run with -v to see every URL tried for the unknown ones.")

    # Persist board_platform / board_url so watch_ats.py can poll them.
    with open(CONFIG, "w", encoding="utf-8") as f:
        json.dump(companies, f, indent=2)
        f.write("\n")
    with open(CONFIG) as f:
        check = json.load(f)
    saved = sum(1 for c in check if c.get("board_url"))
    print(f"\nsaved board URLs for {saved} companies into {CONFIG}")
    print("Next: python3 watch_ats.py --dry-run")


if __name__ == "__main__":
    main()
