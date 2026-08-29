import json

d = json.load(open('companies.json'))
existing_names = {c['name'].lower() for c in d}

# Verified via live search today. Bluestone deliberately excluded - the
# Greenhouse board found belongs to a US medical practice with the same
# name, not the Indian jewelry brand from Accel's portfolio.
new_companies = [
    {"name": "Atlas", "domain": "atlashxm.com", "sector": "saas",
     "ats": "ashby", "slug": "atlas", "method": "manual-verified"},
    {"name": "Bounce", "domain": "bouncedaily.in", "sector": "consumer",
     "ats": "ashby", "slug": "Bounce", "method": "manual-verified"},
    {"name": "Captain Fresh", "domain": "captainfresh.com", "sector": "saas",
     "ats": "smartrecruiters", "slug": "captainfresh", "method": "manual-verified"},
    {"name": "Vaya", "domain": "vaya.in", "sector": "fintech",
     "ats": "greenhouse", "slug": "vaya", "method": "manual-verified"},
]

added = []
for c in new_companies:
    if c['name'].lower() in existing_names:
        print(f"skip (already exists): {c['name']}")
        continue
    d.append(c)
    added.append(c['name'])

json.dump(d, open('companies.json', 'w'), indent=2)
with open('companies.json', 'a') as f:
    f.write('\n')

print(f"\nadded: {added}")
print(f"total companies now: {len(d)}")

# Verify each live board right away, same discipline as FamApp/Stable Money.
import ats
print("\n--- verifying live boards ---")
for c in new_companies:
    if c['name'] not in added:
        continue
    try:
        jobs = ats.fetch_jobs(c['ats'], c['slug'], c['name'])
        print(f"{c['name']}: {len(jobs)} roles found")
        for j in jobs[:3]:
            print(f"   - {j['title']}")
    except Exception as e:
        print(f"{c['name']}: ERROR verifying - {type(e).__name__}: {e}")
