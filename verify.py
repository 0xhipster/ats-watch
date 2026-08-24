"""
Verification pass.

For every resolved company, fetch its board and report how many roles came
back plus a couple of sample titles. Purpose: expose false-positive slug
matches, where a probe "succeeded" against an empty or unrelated board.

Read the output with suspicion. Two failure signatures to look for:

  EMPTY   0 roles. discover.py's probe now rejects zero-role boards, so a
          fresh run should never produce one of these. If you see EMPTY
          here, this company was resolved by an OLDER run before the fix —
          re-run "python discover.py --recheck" on it and check again.

  WRONG   Roles come back, but the titles obviously belong to a different
          company than the one named on the left. Check these by eye —
          no script can judge this for you.

    python3 verify.py
"""

import json
import sys

import ats as ats_lib

CONFIG = "companies.json"


def main():
    companies = json.load(open(CONFIG))

    empty, wrong_candidates, ok, errored = [], [], [], []

    print(f"{'COMPANY':<18} {'ATS/SLUG':<34} {'N':>5}  SAMPLE TITLES")
    print("-" * 100)

    for c in companies:
        ats = c.get("ats")
        slug = c.get("slug")
        name = c.get("name", "?")

        if not ats or not slug:
            print(f"{name:<18} {'(no ats/slug)':<34} {'-':>5}  SKIPPED: unresolved")
            continue
        if ats.startswith("unsupported"):
            print(f"{name:<18} {ats+'/'+slug:<34} {'-':>5}  SKIPPED: no public API")
            continue

        try:
            jobs = ats_lib.fetch_jobs(ats, slug, name)
        except Exception as e:
            print(f"{name:<18} {ats+'/'+slug:<34} {'!':>5}  ERROR: {type(e).__name__}: {e}")
            errored.append(name)
            continue

        titles = " | ".join(j["title"][:38] for j in jobs[:2]) or "(none)"
        flag = "EMPTY" if len(jobs) == 0 else ""
        print(f"{name:<18} {ats+'/'+slug:<34} {len(jobs):>5}  {flag} {titles}")

        if len(jobs) == 0:
            empty.append(f"{name} ({ats}/{slug})")
        else:
            ok.append(name)

    print("-" * 100)
    total = len(companies)
    print(f"total entries      : {total}")
    print(f"returned roles     : {len(ok)}")
    print(f"returned ZERO roles: {len(empty)}")
    print(f"errored            : {len(errored)}")

    if empty:
        print("\nZERO-ROLE BOARDS (likely false-positive slug matches):")
        for e in empty:
            print(f"  - {e}")
        print("\nA real company board almost never has zero open roles.")
        print("Treat every entry above as unresolved until proven otherwise.")

    print("\nNOW READ THE SAMPLE TITLES ABOVE BY EYE.")
    print("If a company's titles look like they belong to a different")
    print("business, that slug is wrong even though it returned data.")


if __name__ == "__main__":
    main()
