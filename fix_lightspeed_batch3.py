import json
import ats

d = json.load(open('companies.json'))
by_name = {c['name']: c for c in d}

# Direct-platform hits, verified via real page load (not guessed).
direct = [
    ('Cybrilla',  'workable', 'cybrilla'),
    ('Emversity', 'workable', 'emversity'),
    ('ShareChat', 'workable', 'sharechat'),
]
for name, platform, slug in direct:
    if name in by_name:
        c = by_name[name]
        c['ats'] = platform
        c['slug'] = slug
        c['method'] = 'manual-verified'
        print(f'Applied {name}: {platform}/{slug}')
    else:
        print(f'! {name} not found')

# Yellow.ai: Zoho Recruit embed detected on their own /career/ page, but no
# direct board subdomain given (job list is a JS widget on yellow.ai itself,
# not a separate zohorecruit.com URL). Recording as a second-lane candidate
# pointing at the page where the embed lives.
if 'Yellow.ai' in by_name:
    c = by_name['Yellow.ai']
    c['board_platform'] = 'zoho_recruit'
    c['board_url'] = 'https://yellow.ai/career/'
    print('Applied Yellow.ai: zoho_recruit (embedded widget) -> https://yellow.ai/career/')

json.dump(d, open('companies.json', 'w'), indent=2)
with open('companies.json', 'a') as f:
    f.write('\n')
print('\nSaved companies.json.')

print('\n--- live verification of the 3 direct Workable hits ---')
for name, platform, slug in direct:
    try:
        jobs = ats.fetch_jobs(platform, slug, name)
        print(f'{name:<12} {platform}/{slug:<12} {len(jobs)} roles')
        for j in jobs[:3]:
            print(f'   - {j["title"]}')
    except Exception as e:
        print(f'{name}: ERROR {type(e).__name__}: {e}')
