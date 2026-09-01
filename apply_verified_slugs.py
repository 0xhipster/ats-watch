import json
import ats

d = json.load(open('companies.json'))
by_name = {c['name'].lower(): c for c in d}

# Every one of these was personally verified in-browser earlier today during
# the Accel Hermes-sheet pass. discover.py's automated guessing failed on
# them (case-sensitivity or slug-pattern misses, same class of issue as
# FamApp/Stable Money), so they never got written despite being confirmed
# real. Writing the verified slugs directly rather than re-guessing.
verified = [
    ("Airmeet",     "workable",        "airmeet"),
    ("Credgenics",  "smartrecruiters", "credgenics"),
    ("EduPristine", "workable",        "edupristine"),
    ("Fashinza",    "workable",        "fashinza"),
    ("Fundly",      "workable",        "fundly"),
    ("Hashnode",    "workable",        "hashnode"),
    ("Jify",        "workable",        "jify"),
    ("KGeN",        "workable",        "kgen"),
    ("LetsVenture", "workable",        "letsventure"),
    ("Swish",       "workable",        "swish"),
    ("Uppercase",   "workable",        "uppercase"),
    ("UrbanCompany","smartrecruiters", "urbancompany"),
]

applied = []
for name, platform, slug in verified:
    c = by_name.get(name.lower())
    if not c:
        print(f"! {name} not found in companies.json, skipping")
        continue
    c['ats'] = platform
    c['slug'] = slug
    c['method'] = 'manual-verified'
    applied.append(name)

json.dump(d, open('companies.json', 'w'), indent=2)
with open('companies.json', 'a') as f:
    f.write('\n')

print(f"applied: {applied}\n")

# Verify every single one live, right now, before trusting the write.
print("--- live verification ---")
total_roles = 0
for name, platform, slug in verified:
    try:
        jobs = ats.fetch_jobs(platform, slug, name)
        total_roles += len(jobs)
        flag = "EMPTY - suspicious" if len(jobs) == 0 else "ok"
        print(f"{name:<14} {platform}/{slug:<16} {len(jobs):>3} roles   {flag}")
    except Exception as e:
        print(f"{name:<14} {platform}/{slug:<16} ERROR: {type(e).__name__}: {e}")

print(f"\ntotal roles across these 12: {total_roles}")
