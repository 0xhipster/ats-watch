"""
The poller.

Fetches every resolved board, filters to roles worth seeing, diffs against
state/seen.json, and pushes anything new to Telegram. Writes the same batch
to digest.md so you can paste it into Claude for triage.

    python3 watch.py             # normal run
    python3 watch.py --dry-run   # print matches, do not notify, do not save state
    python3 watch.py --seed      # mark everything currently open as seen, no alerts
"""

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import ats as ats_lib

CONFIG = "companies.json"
FILTERS = "filters.json"
STATE = "state/seen.json"
DIGEST = "digest.md"


def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def matches(job, filters):
    title = job["title"].lower()
    loc = (job["location"] or "").lower()

    if any(re.search(p, title) for p in filters["title_exclude"]):
        return False
    if not any(re.search(p, title) for p in filters["title_include"]):
        return False

    if job.get("remote") is True:
        return True
    if any(re.search(p, loc) for p in filters["location_include"]):
        return True
    # A blank location on an otherwise matching role is worth a look, not a drop.
    return loc.strip() == ""


def notify_telegram(jobs):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("! TELEGRAM_TOKEN / TELEGRAM_CHAT_ID not set, skipping notification")
        return
    for j in jobs:
        loc = j["location"] or ("Remote" if j.get("remote") else "location not stated")
        text = f"<b>{j['company']}</b>\n{j['title']}\n{loc}\n\n{j['url']}"
        payload = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "false",
        }).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage", data=payload
        )
        try:
            urllib.request.urlopen(req, timeout=15).read()
        except Exception as e:
            print(f"! telegram send failed: {e}")


def write_digest(jobs):
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"# New matches, {stamp}\n"]
    for j in jobs:
        loc = j["location"] or ("Remote" if j.get("remote") else "not stated")
        lines.append(f"- **{j['company']}** | {j['title']} | {loc}\n  {j['url']}")
    with open(DIGEST, "w") as f:
        f.write("\n".join(lines) + "\n")


def main():
    dry = "--dry-run" in sys.argv
    seed = "--seed" in sys.argv

    companies = load_json(CONFIG, [])
    filters = load_json(FILTERS, None)
    if filters is None:
        sys.exit("filters.json missing")
    seen = set(load_json(STATE, {}).get("uids", []))

    all_jobs, errors = [], []
    for c in companies:
        ats = c.get("ats")
        if not ats or ats.startswith("unsupported") or not c.get("slug"):
            continue
        try:
            all_jobs.extend(ats_lib.fetch_jobs(ats, c["slug"], c["name"]))
        except Exception as e:
            errors.append(f"{c['name']} ({ats}/{c['slug']}): {type(e).__name__} {e}")

    hits = [j for j in all_jobs if matches(j, filters)]
    fresh = [j for j in hits if j["uid"] not in seen]

    print(f"boards polled: {len(companies)}  roles seen: {len(all_jobs)}  "
          f"matching: {len(hits)}  new: {len(fresh)}")
    for e in errors:
        print(f"! {e}")

    for j in fresh:
        print(f"  NEW  {j['company']} | {j['title']} | {j['location']}")
        print(f"       {j['url']}")

    if dry:
        return

    if fresh and not seed:
        notify_telegram(fresh)
        write_digest(fresh)

    # Track every currently open role, not just matches, so a retitled or
    # refiltered role does not fire a stale alert later.
    seen.update(j["uid"] for j in all_jobs)
    os.makedirs("state", exist_ok=True)
    with open(STATE, "w") as f:
        json.dump({"updated": datetime.now(timezone.utc).isoformat(),
                   "uids": sorted(seen)}, f, indent=0)
        f.write("\n")


if __name__ == "__main__":
    main()
