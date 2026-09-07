import json
import ats

d = json.load(open('companies.json'))
by_name = {c['name']: c for c in d}

# Nurix AI regressed: discover.py re-matched it to greenhouse/nurix, which is
# Nurix Therapeutics (US biopharma), not the real Nurix AI. Re-applying the
# verified Keka fix from earlier today.
if 'Nurix AI' in by_name:
    c = by_name['Nurix AI']
    c['ats'] = None
    c['slug'] = None
    c['method'] = None
    c['board_platform'] = 'keka'
    c['board_url'] = 'https://nurix.keka.com/careers/'
    print('Re-fixed Nurix AI collision (was clobbered back to wrong Greenhouse match)')

# CSV-verified slugs that discover.py's guessing algorithm never tried,
# because its candidate-generation doesn't match these real slugs.
verified_direct = [
    ('Mitti Labs', 'workable', 'mitti-labs'),
    ('Coral AI',   'ashby',    'coralai'),
]
for name, platform, slug in verified_direct:
    if name in by_name:
        c = by_name[name]
        c['ats'] = platform
        c['slug'] = slug
        c['method'] = 'manual-verified'
        print(f'Applied {name}: {platform}/{slug}')

# Thena: real Greenhouse board (job-boards.greenhouse.io/thena), confirmed
# by the CSV, but currently has zero open roles - which is exactly the
# ambiguous case the zero-role-rejection rule can't distinguish from a fake.
# Trusting the CSV's specific verification here rather than the automated
# zero-role guess.
if 'Thena' in by_name:
    c = by_name['Thena']
    c['ats'] = 'greenhouse'
    c['slug'] = 'thena'
    c['method'] = 'manual-verified-zero-roles'
    print('Applied Thena: greenhouse/thena (currently 0 roles, real board)')

json.dump(d, open('companies.json', 'w'), indent=2)
with open('companies.json', 'a') as f:
    f.write('\n')
print('\nSaved companies.json.')

print('\n--- live verification ---')
for name, platform, slug in verified_direct + [('Nurix AI', 'keka', None)]:
    if platform == 'keka':
        print(f'{name}: keka board, cannot verify via ats.py (second lane only) - trust the earlier confirmed check')
        continue
    try:
        jobs = ats.fetch_jobs(platform, slug, name)
        print(f'{name:<12} {platform}/{slug:<14} {len(jobs)} roles')
        for j in jobs[:3]:
            print(f'   - {j["title"]}')
    except Exception as e:
        print(f'{name}: ERROR {type(e).__name__}: {e}')

try:
    jobs = ats.fetch_jobs('greenhouse', 'thena', 'Thena')
    print(f'Thena: greenhouse/thena {len(jobs)} roles (0 expected, confirming board is reachable not 404)')
except Exception as e:
    print(f'Thena: ERROR {type(e).__name__}: {e}')
