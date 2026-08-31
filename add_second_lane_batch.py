import json

d = json.load(open('companies.json'))
by_name = {c['name'].lower(): c for c in d}

# These were identified from the Hermes-sourced Accel CSV but never actually
# added to companies.json before now - a miss on my part last round.
# URLs are the exact ones from that list, verified as known ATS patterns.
new_second_lane = [
    {"name": "Bizongo", "domain": "bizongo.com", "sector": "saas",
     "board_platform": "darwinbox", "board_url": "https://bizongo.darwinbox.in"},
    {"name": "CityMall", "domain": "citymall.in", "sector": "consumer",
     "board_platform": "darwinbox", "board_url": "https://citymall.darwinbox.in"},
    {"name": "HomeLane", "domain": "homelane.com", "sector": "consumer",
     "board_platform": "darwinbox",
     "board_url": "https://homelane.darwinbox.in/ms/candidatev2/a6817a5ec3524e/careers/allJobs"},
    {"name": "Jiraaf", "domain": "jiraaf.com", "sector": "fintech",
     "board_platform": "keka", "board_url": "https://jiraaf.keka.com/careers"},
    {"name": "Material Depot", "domain": "materialdepot.in", "sector": "saas",
     "board_platform": "keka", "board_url": "https://materialdepot.keka.com/careers"},
    {"name": "Truemeds", "domain": "truemeds.in", "sector": "consumer",
     "board_platform": "keka", "board_url": "https://truemeds.keka.com/careers"},
    {"name": "Unmannd", "domain": "unmannd.in", "sector": "saas",
     "board_platform": "zoho_recruit", "board_url": "https://unmannd.zohorecruit.com/careers"},
    {"name": "Zolve", "domain": "zolve.com", "sector": "fintech",
     "board_platform": "freshteam", "board_url": "https://zolve.freshteam.com/jobs"},
]

added, updated_existing = [], []
for c in new_second_lane:
    if c['name'].lower() in by_name:
        # Already exists (e.g. added from an earlier batch without a board_url) -
        # patch in the board URL rather than skip or duplicate.
        existing = by_name[c['name'].lower()]
        existing['board_platform'] = c['board_platform']
        existing['board_url'] = c['board_url']
        updated_existing.append(c['name'])
    else:
        d.append(c)
        added.append(c['name'])

# Tracxn already exists from an earlier batch and showed "unknown" in census -
# its real board is Zoho Recruit per the Hermes list, apply it directly.
for c in d:
    if c['name'] == 'Tracxn':
        c['board_platform'] = 'zoho_recruit'
        c['board_url'] = 'https://tracxn.zohorecruit.com/careers'
        updated_existing.append('Tracxn')

json.dump(d, open('companies.json', 'w'), indent=2)
with open('companies.json', 'a') as f:
    f.write('\n')

print(f"newly added: {added}")
print(f"existing, board URL patched: {updated_existing}")
print(f"total companies now: {len(d)}")

# integrity check
doms = [c['domain'] for c in d]
assert len(doms) == len(set(doms)), "DUPLICATE DOMAIN"
print("integrity OK")
